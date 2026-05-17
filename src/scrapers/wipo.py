"""
WIPO (世界知识产权组织) 新闻采集器
----------------------------------
新闻页: https://www.wipo.int/pressroom/en/
备用: https://www.wipo.int/zh/web/pct-system/news
      https://www.wipo.int/zh/web/patents/news
"""
import re
import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class WIPOScraper(BaseScraper):
    """WIPO 新闻采集器"""

    def __init__(self):
        super().__init__(
            name="WIPO",
            list_url="https://www.wipo.int/pressroom/en/",
        )

    def parse_list(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        articles = []

        # WIPO 网站使用 Liferay DXP，多个可能的现代选择器
        selectors = [
            "div.list-item",                      # 旧版列表项
            "li.news-item",                       # 旧版新闻项
            "div.news-list li",                   # 旧版新闻列表
            "ul.press-list li",                   # 旧版新闻列表
            "article",                            # HTML5 通用
            "div.card",                           # Liferay 卡片
            "div.article-card",                   # 文章卡片
            "div.component-card",                 # Liferay 组件卡片
            "li.component-list__item",            # Liferay 列表项
            "div.component-list div.item",        # 通用列表
            "a[href*='/pressroom/en/articles/']", # 直接找新闻链接
        ]

        items = []
        selector_used = ""
        for selector in selectors:
            items = soup.select(selector)
            if items:
                selector_used = selector
                break

        if not items:
            # 兜底: 获取所有包含 pressroom 的链接
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/pressroom/" not in href and "/news" not in href:
                    continue
                title = a_tag.get("title", "") or a_tag.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                items.append(a_tag)
            if items:
                logger.info(f"[WIPO] 兜底模式: 找到 {len(items)} 个链接")

        if items and selector_used:
            logger.info(f"[WIPO] 使用选择器 '{selector_used}' 找到 {len(items)} 条")

        for item in items:
            try:
                # 如果兜底直接拿到 a 标签
                if item.name == "a":
                    a_tag = item
                else:
                    a_tag = item.find("a")
                if not a_tag:
                    continue

                title = a_tag.get("title", "") or a_tag.get_text(strip=True)
                href = a_tag.get("href", "")

                if not title or not href or len(title) < 5:
                    continue

                full_url = urljoin(self.list_url, href)

                # 跳过非文章链接
                if any(kw in full_url for kw in ["/search", "/login", "#", "javascript"]):
                    continue

                # 日期
                date_text = ""
                date_tag = item.find("time") or item.find("span", class_=re.compile(r"date|time|date-display"))
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
                logger.warning(f"[WIPO] 解析条目失败: {e}")
                continue

        return articles

    def parse_detail(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        content_selectors = [
            "div.article-content",
            "div.content",
            "div.field-items",
            "div.field--name-body",
            "article",
            "div.component-content",
            "div.text-content",
            "div.portlet-body",
            "div.entry-content",
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


def scrape_wipo(max_articles: int = 5) -> list[Article]:
    scraper = WIPOScraper()
    return scraper.scrape_full_articles(max_articles=max_articles)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    articles = scrape_wipo(3)
    for a in articles:
        print(f"\n{'='*60}")
        print(f"标题: {a.title}")
        print(f"URL: {a.url}")
        print(f"日期: {a.publish_date}")
        print(f"正文预览: {a.content[:200]}..." if a.content else "  (无正文)")
    if not articles:
        print("⚠️ WIPO 未采集到文章，可能需要更新选择器")
