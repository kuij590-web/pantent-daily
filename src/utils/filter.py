# -*- coding: utf-8 -*-
"""
文章筛选器
----------
通过关键词规则，只保留符合要求的文章。
规则在 config.py 中配置，支持「必须包含」和「必须排除」两种模式。
"""
import re
import logging

logger = logging.getLogger(__name__)


# 默认筛选规则
# INCLUDE：标题包含这些关键词之一的文章才保留（为空则不限制）
# EXCLUDE：标题包含这些关键词之一的文章直接跳过
DEFAULT_INCLUDE_KEYWORDS = [
    # 政策文件类
    "通知", "办法", "意见", "方案", "指南", "规定", "决定",
    "公告", "批复", "函", "印发",
    # 新规类
    "修订", "修改", "施行", "实施", "发布", "调整",
    "新规", "新政策",
    # 知识产权专门
    "专利", "商标", "版权", "知识产权",
    "侵权", "维权", "保护",
    # 案例/诉讼类
    "诉讼", "案例", "判决", "纠纷",
    # 会议/活动类
    "论坛", "峰会", "研讨会", "培训", "讲座", "大会",
    # 热点类
    "WIPO", "PCT", "热点", "趋势",
]

DEFAULT_EXCLUDE_KEYWORDS = [
    # 招聘类
    "招聘", "招收", "博士后",
    # 名单/公示类（已确定结果的名单，非政策）
    "名单", "公示", "获奖",
]


def filter_articles(articles, include_keywords=None, exclude_keywords=None):
    """
    对文章列表进行筛选

    Args:
        articles: Article 对象列表
        include_keywords: 标题必须包含的关键词列表（None 则使用默认）
        exclude_keywords: 标题不能包含的关键词列表（None 则使用默认）

    Returns:
        筛选后的 Article 列表
    """
    if include_keywords is None:
        include_keywords = DEFAULT_INCLUDE_KEYWORDS
    if exclude_keywords is None:
        exclude_keywords = DEFAULT_EXCLUDE_KEYWORDS

    filtered = []
    skipped = []

    for article in articles:
        title = article.title

        # 排除规则：标题包含排除关键词的直接跳过
        if _matches_any(title, exclude_keywords):
            skipped.append((title, "包含排除关键词"))
            continue

        # 包含规则：如果设定了包含关键词，标题必须至少匹配一个
        if include_keywords:
            if _matches_any(title, include_keywords):
                filtered.append(article)
            else:
                skipped.append((title, "不匹配任何包含关键词"))
        else:
            # 没有设置包含关键词，全部保留
            filtered.append(article)

    if skipped:
        logger.info(f"筛选完成: 保留 {len(filtered)} 篇, 跳过 {len(skipped)} 篇")
        for title, reason in skipped:
            logger.info(f"  跳过: [{reason}] {title[:40]}...")

    return filtered


def _matches_any(text: str, keywords: list) -> bool:
    """检查文本是否包含列表中任意关键词"""
    for kw in keywords:
        if kw in text:
            return True
    return False
