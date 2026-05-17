"""
AI 摘要模块
-----------
基于 DeepSeek API，实现文章的专业摘要生成。

使用前需要在环境变量中设置 DEEPSEEK_API_KEY。
"""
import json
import logging
import re
import time
from typing import Optional

import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)


# ============================================================
# 专家 Prompt 模板
# ============================================================
SUMMARY_PROMPT_TEMPLATE = """你是一位资深知识产权顾问。请从以下几个维度分析这篇文章：

## 文章原文
{article_content}

## 分析要求
1. 【核心要点】：用 1-2 句话概括文章核心信息（50字以内）
2. 【实务影响】：该政策/案例/动态对 IP 从业者有什么实际影响
3. 【延伸思考】：如果你觉得这篇文章有价值，用一句话点出值得关注的原因
4. 【关键词】：提取 3-5 个标签，如 #专利审查 #商标法 #海外维权

## 输出格式（请严格按照以下格式输出）
【标题】{{标题}}
核心：{{一句话核心}}
影响：{{实务影响分析}}
点评：{{延伸思考}}
标签：{{关键词}}

注意：不要使用任何 emoji 表情符号。
输出字数控制在 200 字以内。"""


# ============================================================
# AI 摘要类
# ============================================================

class AISummarizer:
    """AI 摘要生成器"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY 未设置，AI 摘要功能将不可用")

    def summarize(self, title: str, content: str, max_retries: int = 2) -> str:
        """
        对一篇文章生成结构化摘要

        Args:
            title: 文章标题
            content: 文章正文
            max_retries: 失败重试次数

        Returns:
            结构化摘要文本，如 API 不可用则返回空字符串
        """
        if not self.api_key:
            return ""

        # 截断过长内容（DeepSeek 上下文限制）
        trimmed_content = content[:6000] if len(content) > 6000 else content

        prompt = SUMMARY_PROMPT_TEMPLATE.format(
            article_content=f"标题：{title}\n\n正文：{trimmed_content}"
        )

        for attempt in range(max_retries + 1):
            try:
                result = self._call_api(prompt)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"AI 摘要生成失败(第{attempt+1}次): {e}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # 指数退避
        return ""

    def _call_api(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位资深知识产权顾问，擅长从政策、实务、企业策略角度分析 IP 相关文章。请用专业但简洁的语言输出分析。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,  # 低温度确保输出稳定
            "max_tokens": 500,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def summarize_batch(self, articles: list, batch_size: int = 5) -> list:
        """
        批量摘要

        Args:
            articles: Article 对象列表
            batch_size: 每批处理数量

        Returns:
            更新了 summary 字段的 Article 列表
        """
        processed = 0
        for article in articles:
            if not article.content or len(article.content.strip()) < 20:
                logger.info(f"[{article.title}] 正文过短，跳过 AI 摘要")
                article.summary = f"🔹 **{article.title}**\n👉 [阅读原文]({article.url})"
                continue

            summary = self.summarize(article.title, article.content)
            if summary:
                article.summary = summary
                processed += 1
                logger.info(f"[{article.title}] AI 摘要完成")
            else:
                # 降级：纯标题+链接
                article.summary = f"🔹 **{article.title}**\n👉 [阅读原文]({article.url})"
                logger.warning(f"[{article.title}] AI 摘要失败，使用降级方案")

            time.sleep(0.5)  # 避免 API 限流

        logger.info(f"批量摘要完成: 成功 {processed}/{len(articles)}")
        return articles


# ============================================================
# 便捷函数
# ============================================================

def summarize_article(title: str, content: str) -> str:
    """便捷单篇摘要"""
    summarizer = AISummarizer()
    return summarizer.summarize(title, content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 测试
    test_content = """
    国家知识产权局近日发布《专利审查指南》修订公告，新规将于2026年6月1日起施行。
    本次修订主要涉及人工智能相关专利申请的审查标准，明确了AI辅助发明的发明人资格问题。
    新规要求，专利申请中必须明确披露人工智能工具的参与程度。
    """
    result = summarize_article("专利审查指南修订公告", test_content)
    print("摘要结果:")
    print(result)
