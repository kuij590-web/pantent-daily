"""
知产媒体网站采集器（知产力、IPRdaily 等）
-----------------------------------------
"""
import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class ZhichanliScraper(BaseScraper):
    """知产力采集器"""

    def __init__(self):
        super().__init__(
            name="知产力",
            list_url="https://www.zhichanli.com/",
        )

    def parse_list(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # 知产力的文章列表常见结构
        selectors = [
            "div.post-item",
            "div.article-item",
            "div.item",
            "li.post",
            "article",
            "div.post",
            "div.news-list li",
            "div.list li",
            "div.card",
        ]

        items = []
        selector_used = ""
        for selector in selectors:
            items = soup.select(selector)
            if items:
                selector_used = selector
                break

        if not items or len(items) < 2:
            # 兜底：找所有链接，按 URL 模式过滤
            seen_hrefs = set()
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                title = a_tag.get("title", "") or a_tag.get_text(strip=True)

                if not title or len(title) < 6:
                    continue
                if not href or href in ("/", "#", "", "javascript:void(0)"):
                    continue
                if any(kw in href for kw in ["/tag/", "/about", "/login", "/search",
                                              ".css", ".js", "javascript"]):
                    continue

                # 知产力文章 URL 模式：/p/{数字id}
                is_article_url = bool(re.search(r'/p/\d+', href))
                if not is_article_url:
                    continue

                href_key = href.rstrip("/")
                if href_key in seen_hrefs:
                    continue
                seen_hrefs.add(href_key)

                items.append(a_tag)

            if items:
                logger.info(f"[知产力] 兜底模式: 找到 {len(items)} 个文章链接")

        if items and selector_used:
            logger.info(f"[知产力] 使用选择器 '{selector_used}' 找到 {len(items)} 条")

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
                logger.warning(f"[知产力] 解析条目失败: {e}")
                continue

        return articles

    def parse_detail(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        content_selectors = [
            "div.article-content",
            "div.post-content",
            "div.content",
            "article",
            "div.rich_media_content",
            "div.entry-content",
            "div.main-content",
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


def scrape_media_sites(max_articles: int = 5) -> list[Article]:
    """采集所有已启用的知产媒体源"""
    articles = []
    try:
        scraper = ZhichanliScraper()
        articles.extend(scraper.scrape_full_articles(max_articles=max_articles))
    except Exception as e:
        logger.error(f"[知产力] 采集失败: {e}")
    return articles


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    articles = scrape_media_sites(5)
    for a in articles:
        print(f"\n{'='*60}")
        print(f"标题: {a.title}")
        print(f"URL: {a.url}")
        print(f"日期: {a.publish_date}")
        print(f"正文预览: {a.content[:200]}..." if a.content else "  (无正文)")
    if not articles:
        print("⚠️ 知产力未采集到文章，可能需要更新选择器")
