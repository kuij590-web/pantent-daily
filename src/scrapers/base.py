"""
采集器基类
----------
所有站点采集器继承此类，统一接口和错误处理。
"""
import time
import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY, HTTP_PROXY

logger = logging.getLogger(__name__)


class Article:
    """单篇文章的数据结构"""
    def __init__(self, title: str, url: str, source: str, summary: str = "",
                 publish_date: str = "", content: str = ""):
        self.title = title.strip()
        self.url = url.strip()
        self.source = source            # 来源名称，如"国家知识产权局"
        self.summary = summary          # AI 摘要（后续填充）
        self.publish_date = publish_date
        self.content = content          # 文章正文（传给 AI 用）
        self.category = ""              # 分类：政策/诉讼/海外/商标

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "publish_date": self.publish_date,
            "content": self.content[:200],  # 只存前200字用于去重
            "category": self.category,
        }


class BaseScraper:
    """采集器基类，所有站点采集器继承此类"""

    def __init__(self, name: str, list_url: str):
        self.name = name
        self.list_url = list_url
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
        if HTTP_PROXY:
            session.proxies = {"http": HTTP_PROXY, "https": HTTP_PROXY}
        return session

    def fetch_page(self, url: str, encoding: Optional[str] = None) -> str:
        """获取页面 HTML，统一异常处理"""
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            if encoding:
                resp.encoding = encoding
            else:
                # 自动检测编码
                resp.encoding = resp.apparent_encoding
            time.sleep(REQUEST_DELAY)  # 反爬礼貌
            return resp.text
        except requests.RequestException as e:
            logger.error(f"[{self.name}] 请求失败: {url} → {e}")
            return ""

    def parse_list(self, html: str) -> list[dict]:
        """解析列表页，返回 [{title, url, date}, ...]
        子类必须重写此方法"""
        raise NotImplementedError

    def parse_detail(self, html: str) -> str:
        """解析文章详情页，返回正文文本
        子类必须重写此方法"""
        raise NotImplementedError

    def scrape_list(self) -> list[dict]:
        """采集列表页的完整流程"""
        logger.info(f"[{self.name}] 开始采集列表页: {self.list_url}")
        html = self.fetch_page(self.list_url)
        if not html:
            return []
        articles = self.parse_list(html)
        logger.info(f"[{self.name}] 列表页解析完成，共 {len(articles)} 条")
        return articles

    def scrape_detail(self, url: str) -> str:
        """采集文章详情"""
        logger.info(f"[{self.name}] 采集详情: {url}")
        html = self.fetch_page(url)
        if not html:
            return ""
        return self.parse_detail(html)

    def scrape_full_articles(self, max_articles: int = 10) -> list[Article]:
        """采集完整文章：先取列表，再逐篇获取正文"""
        items = self.scrape_list()
        articles = []
        for item in items[:max_articles]:
            content = self.scrape_detail(item["url"])
            article = Article(
                title=item["title"],
                url=item["url"],
                source=self.name,
                publish_date=item.get("date", ""),
                content=content,
            )
            # 如果抓不到正文，至少保留标题和链接
            articles.append(article)
        return articles
