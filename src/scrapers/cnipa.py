# -*- coding: utf-8 -*-
"""
国家知识产权局 (CNIPA) 通知公告采集器
-------------------------------------
采集方式：直接请求列表页 HTML，从页面源码的 <script type="text/xml"> 标签中
提取文章数据。这是页面本身包含的信息，属于正常浏览行为。
"""
import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class CNIPAScraper(BaseScraper):
    """国知局通知公告采集器"""

    def __init__(self):
        super().__init__(
            name="国家知识产权局",
            list_url="https://www.cnipa.gov.cn/col/col75/index.html",
        )

    def parse_list(self, html: str) -> list[dict]:
        """
        国知局页面在 <script type="text/xml"> 标签中嵌入了 XML 格式的文章数据。
        每个 <record> 包含文章标题、URL 和日期。
        """
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 找到包含文章数据的 script 标签
        script_tag = soup.find("script", type="text/xml")
        if not script_tag:
            logger.warning("[CNIPA] 未找到数据 script 标签")
            return []

        xml_text = script_tag.string
        if not xml_text:
            return []

        # 提取所有 <record> 标签内的 CDATA 内容
        # 每个 record 包含类似:
        # <li><a href="URL" ...>TITLE</a><span>DATE</span></li>
        record_pattern = re.compile(
            r"<record><!\[CDATA\[(.*?)\]\]></record>", re.DOTALL
        )
        matches = record_pattern.findall(xml_text)

        for cdata_content in matches:
            try:
                # 解析 CDATA 中的 HTML 片段
                record_soup = BeautifulSoup(cdata_content, "lxml")
                a_tag = record_soup.find("a")
                span_tag = record_soup.find("span")

                if not a_tag:
                    continue

                title = a_tag.get("title", "") or a_tag.get_text(strip=True)
                href = a_tag.get("href", "")

                if not title or not href:
                    continue

                full_url = urljoin("https://www.cnipa.gov.cn", href)
                date_text = span_tag.get_text(strip=True) if span_tag else ""

                articles.append({
                    "title": title,
                    "url": full_url,
                    "date": date_text,
                })
            except Exception as e:
                logger.warning(f"[CNIPA] 解析条目失败: {e}")
                continue

        return articles

    def parse_detail(self, html: str) -> str:
        """解析文章详情页"""
        soup = BeautifulSoup(html, "lxml")

        content_selectors = [
            "div.article-content",
            "div#zoom",
            "div.content",
            "div.TRS_Editor",
            "div.Custom_UnionStyle",
            "div.pages_content",
            "div.news-content",
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                for tag in content_div.find_all(["script", "style"]):
                    tag.decompose()
                text = content_div.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    return text

        body = soup.find("body")
        if body:
            for tag in body.find_all(["script", "style"]):
                tag.decompose()
            text = body.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if len(l) > 10]
            return "\n".join(lines[:100])

        return ""


def scrape_cnipa(max_articles: int = 10) -> list[Article]:
    scraper = CNIPAScraper()
    return scraper.scrape_full_articles(max_articles=max_articles)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = scrape_cnipa(3)
    for a in articles:
        print(f"\n{'='*60}")
        print(f"标题: {a.title}")
        print(f"URL: {a.url}")
        print(f"日期: {a.publish_date}")
        print(f"正文预览: {a.content[:150]}...")
