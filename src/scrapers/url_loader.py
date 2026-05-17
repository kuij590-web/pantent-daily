# -*- coding: utf-8 -*-
"""
URL 文章采集器
--------------
从手动提供的 URL 列表抓取文章内容和标题。
支持微信公众号文章、普通网页文章等。
"""
import re
import logging
import os
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, Article

logger = logging.getLogger(__name__)


class URLArticleLoader(BaseScraper):
    """
    从单个 URL 加载文章，不依赖列表页。
    直接请求文章 URL 并提取正文和标题。
    """

    def __init__(self):
        super().__init__("URL导入", "")

    def parse_list(self, html: str):  # 不需要
        return []

    def parse_detail(self, html: str) -> str:
        """从任意网页提取正文"""
        soup = BeautifulSoup(html, "lxml")

    def _parse_wechat_article(self, html: str) -> str:
        '''专门解析微信公众号文章'''
        import re
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        # 方法1: 找 js_content (公众号文章正文)
        js_content = soup.select_one("div#js_content")
        if js_content:
            # 微信文章内容可能在 <span> 或直接文本中
            for tag in js_content.find_all(["script", "style"]):
                tag.decompose()
            text = js_content.get_text(separator="\n", strip=True)
            if len(text) > 50:
                return text

        # 方法2: 找 rich_media_content
        rich = soup.select_one("div.rich_media_content")
        if rich:
            for tag in rich.find_all(["script", "style"]):
                tag.decompose()
            text = rich.get_text(separator="\n", strip=True)
            if len(text) > 50:
                return text

        # 方法3: 从页面 JSON 数据中提取
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "var ct = " in script.string:
                match = re.search(r'var ct = \"(.+?)\"', script.string)
                if match:
                    import html
                    return html.unescape(match.group(1))
            if script.string and "content" in (script.string or ""):
                match = re.search(r'"content"\s*:\s*"(.+?)"', script.string or "")
                if match:
                    return match.group(1)[:2000]

        return ""

    def parse_detail(self, html: str) -> str:
        # 如果是微信公众号文章，用专用解析器
        if "mp.weixin.qq.com" in self.list_url or "weixin" in html[:500].lower():
            result = self._parse_wechat_article(html)
            if result:
                return result

        # 优先选择器列表
        content_selectors = [
            # 微信公众号文章
            "div#js_content",
            "div.rich_media_content",
            # 通用文章
            "article",
            "div.article-content",
            "div.post-content",
            "div.content",
            "div.main-content",
            ".article",
            ".post",
            # 兜底
            "div[class*='content']",
            "div[class*='article']",
            "div[class*='post']",
        ]

        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                for tag in content_div.find_all(["script", "style"]):
                    tag.decompose()
                text = content_div.get_text(separator="\n", strip=True)
                if len(text) > 100:  # 有效内容至少100字
                    return text

        # 终极兜底
        body = soup.find("body")
        if body:
            for tag in body.find_all(["script", "style"]):
                tag.decompose()
            lines = [l.strip() for l in body.get_text("\n", strip=True).split("\n")
                    if len(l.strip()) > 15]
            return "\n".join(lines[:200])

        return ""

    def load_from_url(self, url: str, title_hint: str = "") -> Article:
        """从 URL 加载文章"""
        logger.info(f"从URL加载文章: {url}")

        # 微信公众号文章需要特殊请求头
        if "mp.weixin.qq.com" in url:
            logger.info("检测到微信公众号文章，设置专用请求头")
            original_headers = dict(self.session.headers)
            self.session.headers.update({
                "Referer": "https://mp.weixin.qq.com/",
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.6099.230 Mobile Safari/537.36"
                ),
            })

        html = self.fetch_page(url)

        # 恢复原始请求头
        if "mp.weixin.qq.com" in url:
            self.session.headers = original_headers

        # 提取标题
        title = title_hint
        if not title and html:
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
                # 去掉网站名称后缀如 " - 知产力"
                for sep in [" - ", " _", " | ", " – "]:
                    if sep in title:
                        title = title.split(sep)[0].strip()
                        break

        # 提取正文
        # 先设置当前URL，让 parse_detail 能正确识别文章类型
        self.list_url = url
        content = self.parse_detail(html) if html else ""

        if not title:
            title = url

        return Article(
            title=title,
            url=url,
            source="人工推荐",
            content=content,
        )


def load_manual_links(links_file: str) -> list[Article]:
    """
    从 manual_links.md 文件加载人工收集的文章链接

    Args:
        links_file: 链接文件路径

    Returns:
        Article 列表
    """
    if not os.path.exists(links_file):
        logger.info(f"链接文件不存在: {links_file}")
        return []

    articles = []
    loader = URLArticleLoader()

    with open(links_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 读取链接后清空文件（下次重新收集）
    links_to_process = []

    logger.info(f"读取链接文件 {links_file}，共 {len(lines)} 行")

    for i, line in enumerate(lines, 1):
        line = line.strip()
        logger.debug(f"  行{i}: {line}")
        if not line or line.startswith("#") or line.startswith("---"):
            continue

        # 提取 URL 和备注
        # 支持格式: https://... # 备注
        url_match = re.search(r"https?://\S+", line)
        if not url_match:
            logger.debug(f"  行{i} 未找到URL")
            continue

        url = url_match.group(0)
        # 去掉 URL 后面的标点
        url = re.sub(r'[，。、；：\)\)）\]】》"\']$', '', url)

        # 提取 # 后面的备注作为标题提示
        note = ""
        if "#" in line:
            note = line.split("#", 1)[1].strip()

        links_to_process.append((url, note))
        logger.info(f"  发现链接 [{len(links_to_process)}]: {url}")

    if not links_to_process:
        logger.info("链接文件为空（未找到任何URL）")
        return []

    logger.info(f"从人工链接文件加载到 {len(links_to_process)} 个链接")

    for url, note in links_to_process:
        try:
            article = loader.load_from_url(url, title_hint=note)
            if article.content and len(article.content) > 50:
                articles.append(article)
                logger.info(f"  ✓ {article.title[:40]}...")
            else:
                logger.warning(f"  ✗ 未能获取正文: {url[:50]}")
        except Exception as e:
            logger.warning(f"  ✗ 加载失败: {url[:50]} → {e}")

    # 清空链接文件（已消费）
    with open(links_file, "w", encoding="utf-8") as f:
        f.write("# Daily manual links - paste URLs below\n")
        f.write("#\n")

    return articles
