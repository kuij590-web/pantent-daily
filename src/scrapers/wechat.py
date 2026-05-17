"""
微信公众号文章采集器（通过搜狗微信搜索）
-----------------------------------------
搜狗微信搜索是免费获取公众号文章列表的主要途径。

注意：
- 搜狗有反爬机制，频繁请求会被封 IP
- 建议每次运行只查询 1-2 个公众号
- 如需要稳定的公众号数据源，建议使用付费的第三方 RSS 服务
"""
import re
import json
import logging
import urllib.parse
from typing import Optional
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class SogouWechatScraper(BaseScraper):
    """
    通过搜狗微信搜索采集公众号文章
    搜狗搜索 URL 格式：
    https://weixin.sogou.com/weixin?type=2&query=公众号名称
    """

    def __init__(self, account_name: str):
        search_url = (
            f"https://weixin.sogou.com/weixin"
            f"?type=2&query={quote(account_name)}"
        )
        super().__init__(
            name=f"微信公众号-{account_name}",
            list_url=search_url,
        )
        self.account_name = account_name

    def parse_list(self, html: str) -> list[dict]:
        """
        搜狗微信搜索结果页解析
        每条结果在 <li> 标签内，包含标题、链接、摘要、公众号名称
        """
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 搜狗微信结果列表
        items = soup.select("ul.news-list2 li")

        for item in items:
            try:
                # 标题和链接
                title_box = item.select_one("h3 a")
                if not title_box:
                    continue

                title = title_box.get_text(strip=True)
                # 搜狗的结果链接是跳转链接，需要提取真正的文章 URL
                href = title_box.get("href", "")
                if not href:
                    continue

                # 搜狗链接是相对路径，需要补全
                article_url = urljoin("https://weixin.sogou.com", href)

                # 日期（搜狗显示为 "3天前" 等相对时间）
                date_span = item.select_one("span.s2")
                date_text = date_span.get_text(strip=True) if date_span else ""

                # 摘要
                summary_div = item.select_one("p.txt-info")
                summary = ""
                if summary_div:
                    summary = summary_div.get_text(strip=True)

                articles.append({
                    "title": title,
                    "url": article_url,
                    "date": date_text,
                    "summary": summary,
                })
            except Exception as e:
                logger.warning(f"[搜狗-{self.account_name}] 解析条目失败: {e}")
                continue

        return articles

    def parse_detail(self, html: str) -> str:
        """
        微信公众号文章详情页解析
        公众号文章通常是富文本格式
        """
        soup = BeautifulSoup(html, "lxml")

        # 微信公众号文章正文
        content_selectors = [
            "div#js_content",
            "div.rich_media_content",
            "div.article-content",
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                for tag in content_div.find_all(["script", "style"]):
                    tag.decompose()
                text = content_div.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    return text

        return ""


def search_wechat_account(account_name: str, max_articles: int = 5) -> list[Article]:
    """搜索指定公众号的最新文章"""
    scraper = SogouWechatScraper(account_name)
    return scraper.scrape_full_articles(max_articles=max_articles)


# 预设要监控的 IP 公众号
RECOMMENDED_ACCOUNTS = [
    "国家知识产权局",
    "知产力",
    "IPRdaily",
    "知识产权报",
    "知产宝",
    "中国知识产权报",
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = search_wechat_account("国家知识产权局", 3)
    for a in articles:
        print(f"\n{'='*60}")
        print(f"标题: {a.title}")
        print(f"URL: {a.url}")
        print(f"正文预览: {a.content[:150]}...")
