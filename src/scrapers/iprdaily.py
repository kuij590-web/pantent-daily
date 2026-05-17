"""
IPRdaily 知产媒体采集器
-----------------------
采集来源：https://www.iprdaily.cn/
"""
import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class IPRdailyScraper(BaseScraper):
    """IPRdaily 新闻采集器"""

    def __init__(self):
        super().__init__(
            name="IPRdaily",
            list_url="https://www.iprdaily.cn/",
        )

    def parse_list(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 尝试多种选择器（适配不同页面版本）
        selectors = [
            "div.news_list li",
            "div.list-item",
            "div.article-list li",
            "ul.news-list li",
            "div.new-list li",
            "div.index_news_list li",
            "div.right_news_list li",
            "li.news-item",
            "div.news_box li",
            "div.news_list dl",
            "div.news_con li",
            "article",
            "div.item",
            "li.clearfix",
            "div.article-item",
            "div.post-item",
            "div.news-item",
            "div.index-list li",
            "div.home-news li",
        ]

        items = []
        selector_used = ""
        for selector in selectors:
            items = soup.select(selector)
            if items:
                selector_used = selector
                break

        if not items or len(items) < 3:
            # 兜底：找所有链接，严格过滤
            seen_hrefs = set()
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                title = a_tag.get("title", "") or a_tag.get_text(strip=True)

                # 基础过滤
                if not title or len(title) < 8:
                    continue
                if not href or href in ("/", "#", "", "javascript:void(0)"):
                    continue
                if any(kw in href for kw in ["/list/", "/tag/", "/about", "/login",
                                              "/search", "javascript", ".css", ".js"]):
                    continue

                # 过滤栏目合集页（旧专题索引，不是新闻）
                if "栏目合集" in title:
                    continue

                # 只保留看起来像文章的 URL 模式
                is_article_url = bool(re.search(r'(news|article)_\d+', href))
                if not is_article_url:
                    continue

                # 去重
                href_key = href.rstrip("/")
                if href_key in seen_hrefs:
                    continue
                seen_hrefs.add(href_key)

                items.append(a_tag)
            if items:
                logger.info(f"[IPRdaily] 兜底模式: 找到 {len(items)} 个文章链接")

        if items and selector_used:
            logger.info(f"[IPRdaily] 使用选择器 '{selector_used}' 找到 {len(items)} 条")

        for item in items:
            try:
                a_tag = item if item.name == "a" else item.find("a")
                if not a_tag:
                    continue

                title = a_tag.get("title", "") or a_tag.get_text(strip=True)
                href = a_tag.get("href", "")

                if not title or not href or len(title) < 6:
                    continue

                full_url = urljoin(self.list_url, href)

                # 提取日期
                date_text = ""
                date_tag = item.find("time") or item.find("span", class_=re.compile(r"date|time"))
                if date_tag:
                    date_text = date_tag.get_text(strip=True)
                else:
                    date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", item.get_text())
                    if date_match:
                        date_text = date_match.group(1)

                articles.append({
                    "title": title,
                    "url": full_url,
                    "date": date_text,
                })
            except Exception as e:
                logger.warning(f"[IPRdaily] 解析条目失败: {e}")
                continue

        return articles

    def parse_detail(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        content_selectors = [
            "div.article-content",
            "div.content",
            "div.article_con",
            "div.news-content",
            "div.show_content",
            "div.detail-content",
            "div.content_detail",
            "article",
            "div.main-content",
            "div.rich_media_content",
            "div[class*='content']",
            "div[class*='article']",
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                for tag in content_div.find_all(["script", "style"]):
                    tag.decompose()
                text = content_div.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

        # 兜底
        body = soup.find("body")
        if body:
            for tag in body.find_all(["script", "style"]):
                tag.decompose()
            lines = [l.strip() for l in body.get_text("\n", strip=True).split("\n")
                    if len(l.strip()) > 15]
            return "\n".join(lines[:200])

        return ""


def scrape_iprdaily(max_articles: int = 8) -> list[Article]:
    """采集 IPRdaily 文章"""
    scraper = IPRdailyScraper()
    return scraper.scrape_full_articles(max_articles=max_articles)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    articles = scrape_iprdaily(3)
    for a in articles:
        print(f"\n{'='*60}")
        print(f"标题: {a.title}")
        print(f"URL: {a.url}")
        print(f"正文预览: {a.content[:150]}..." if a.content else "  (无正文)")
