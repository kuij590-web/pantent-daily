#!/usr/bin/env python3
"""
IP 信息中枢 - 主流程脚本
========================
完整的采集→摘要→发布流水线。

工作流程：
  1. 从配置的源采集文章
  2. AI 生成结构化摘要
  3. 整理为早报 HTML
  4. 发布到微信公众号草稿箱

运行方式：
  本地测试:  python scripts/collect.py
  生产环境:  由 GitHub Actions 定时触发
"""
import logging
import os
import sys
from datetime import datetime

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SOURCES, DATA_DIR, LAST_RUN_FILE, BACKUP_RETENTION_DAYS
from src.utils.filter import filter_articles
from src.scrapers.cnipa import scrape_cnipa
from src.scrapers.media_sites import scrape_media_sites
from src.scrapers.wechat import search_wechat_account
from src.scrapers.url_loader import load_manual_links
from src.scrapers.iprdaily import scrape_iprdaily
from src.scrapers.wipo import scrape_wipo
from src.ai.summarizer import AISummarizer
from src.utils.image_gen import generate_header_image
from src.publisher.wechat_draft import (
    WeChatDraftPublisher,
    generate_daily_digest_html,
    build_daily_title,
)
from src.utils.helpers import load_last_run, save_last_run

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("collect")


def categorize_article(article):
    """
    根据标题和来源判断文章分类
    返回: "官媒信息政策" / "行业信息" / "案例分享" / "热点关注" / "会议培训"
    """
    title = article.title
    source = article.source

    # 1) 会议培训（优先匹配，因为这部分以前被过滤掉了）
    keywords_event = [
        "讲座", "培训", "研修", "论坛", "峰会", "研讨会", "交流会",
        "公益", "活动", "宣传周", "万里行",
        "征稿", "征集", "选题", "报名", "参会",
        "大会", "年会", "沙龙",
    ]
    for kw in keywords_event:
        if kw in title:
            return "会议培训"

    # 2) 案例分享
    keywords_case = [
        "诉讼", "侵权", "无效", "判决", "裁定", "法院",
        "纠纷", "赔偿", "裁决", "案例", "判例",
        "庭审", "上诉", "再审", "争议",
    ]
    for kw in keywords_case:
        if kw in title:
            return "案例分享"

    # 3) 官媒信息政策
    keywords_policy = [
        "政策", "办法", "通知", "意见", "指南", "规定", "修订",
        "公告", "实施", "标准", "印发", "暂行", "决定",
        "批复", "函", "方案", "修改", "施行", "发布", "调整",
        "新规", "新政策", "保护", "知识产权",
    ]
    for kw in keywords_policy:
        if kw in title:
            return "官媒信息政策"

    # 4) 热点关注
    keywords_hot = [
        "WIPO", "PCT", "马德里", "海外", "国际",
        "USPTO", "EPO", "欧洲", "美国", "日本",
        "热点", "趋势", "前沿", "AI", "人工智能",
        "标准必要专利", "SEP", "开源",
    ]
    for kw in keywords_hot:
        if kw in title or kw in source:
            return "热点关注"

    # 5) 兜底 → 行业信息
    return "行业信息"


def dedup_articles(articles):
    """
    文章去重: 按 URL 去重 + 标题相似度去重
    """
    seen_urls = set()
    seen_titles = []
    result = []

    for article in articles:
        # URL 去重
        url_key = article.url.strip().rstrip("/")
        if url_key in seen_urls:
            logger.info(f"  去重(URL): {article.title[:40]}")
            continue
        seen_urls.add(url_key)

        # 标题相似度去重（简单版：标题包含关系）
        title = article.title.strip()
        is_dup = False
        for existing_title in seen_titles:
            # 如果一个标题包含另一个，视为重复
            short, long = (title, existing_title) if len(title) < len(existing_title) else (existing_title, title)
            if short and long and short in long:
                is_dup = True
                logger.info(f"  去重(标题): {title[:40]} ~ {existing_title[:40]}")
                break
            # 标题前15字相同视为重复
            if len(title) > 15 and len(existing_title) > 15:
                if title[:15] == existing_title[:15]:
                    is_dup = True
                    logger.info(f"  去重(标题前缀): {title[:40]}")
                    break

        if not is_dup:
            seen_titles.append(title)
            result.append(article)

    return result


def format_article_for_digest(article, category: str = ""):
    """将 Article 格式化为苹果风格卡片 HTML"""
    import re

    if not article.summary:
        return f'<p style="margin:6px 0;"><strong>{article.title}</strong></p>'

    text = article.summary
    url = article.url or ""

    # 板块专有色（默认蓝色）
    cat_accent = {
        "官媒信息政策": "#1a73e8",
        "行业信息": "#0f9d58",
        "案例分享": "#d93025",
        "热点关注": "#9334e6",
        "会议培训": "#0dc2b8",
    }
    accent = cat_accent.get(category, "#1a73e8")

    # 解析 AI 摘要的各个字段
    title = re.search(r'【标题】(.*?)(?:核心：|$)', text)
    core = re.search(r'核心：(.*?)(?:影响：|$)', text)
    impact = re.search(r'影响：(.*?)(?:点评：|$)', text)
    comment = re.search(r'点评：(.*?)(?:标签：|$)', text)
    tags = re.search(r'标签：(.*?)$', text)

    if not title:
        text_clean = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text_clean = text_clean.replace("\n", "<br>")
        return f'<p style="margin:6px 0;">{text_clean}</p>'

    title_str = title.group(1).strip()
    core_str = core.group(1).strip() if core else ""
    impact_str = impact.group(1).strip() if impact else ""
    comment_str = comment.group(1).strip() if comment else ""
    tags_str = tags.group(1).strip() if tags else ""

    # 标签
    tag_html = ""
    if tags_str:
        tag_list = [t.strip() for t in tags_str.replace("、", " ").replace("#", "").split() if t.strip()]
        for tag in tag_list[:4]:
            tag_html += f'<span style="display:inline-block;padding:2px 10px;margin:2px 4px 2px 0;font-size:11px;color:#888;background:#f5f5f7;border-radius:12px;">{tag}</span>'

    # 原文链接
    link_html = ""
    if url:
        link_html = f'<a href="{url}" style="display:inline-block;margin-top:10px;font-size:13px;color:{accent};text-decoration:none;font-weight:500;">阅读全文 →</a>'

    # 卡片：颜色随板块变化
    html = f"""\
<div style="margin:16px 0 24px 0;padding:0 0 20px 0;border-bottom:1px solid #e8eaed;">
    <div style="font-size:17px;font-weight:600;color:#1d1d1f;line-height:1.5;margin-bottom:12px;">{title_str}</div>
    <div style="font-size:14px;color:#555;line-height:1.8;">
        <span style="color:{accent};font-weight:500;">核心</span> {core_str}<br>
        <span style="color:{accent};font-weight:500;">影响</span> {impact_str}<br>
        <span style="color:{accent};font-weight:500;">点评</span> {comment_str}
    </div>
    <div style="margin-top:12px;">
        {tag_html}
        {link_html}
    </div>
</div>"""

    return html


def cleanup_old_backups(backup_dir: str, keep_days: int = 7):
    """清理过期备份文件，只保留最近 N 天"""
    import time
    if not os.path.exists(backup_dir):
        return
    now = time.time()
    cutoff = now - keep_days * 86400
    removed = 0
    for fname in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath) and fname.startswith("digest_"):
            mtime = os.path.getmtime(fpath)
            if mtime < cutoff:
                os.remove(fpath)
                removed += 1
    if removed:
        logger.info(f"  清理了 {removed} 个过期备份文件（>{keep_days}天）")


def main():
    """主流程"""
    logger.info("=" * 50)
    logger.info("IP 信息中枢 - 开始每日采集")
    logger.info(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # ---------------------------------------------------------
    # 步骤 1: 采集文章
    # ---------------------------------------------------------
    logger.info("\n📡 阶段1: 采集文章")
    all_articles = []

    # 1a: 国知局（默认开启）
    if SOURCES["cnipa"]["enabled"]:
        try:
            articles = scrape_cnipa(max_articles=10)
            all_articles.extend(articles)
            logger.info(f"  国知局: 采集到 {len(articles)} 篇")
        except Exception as e:
            logger.error(f"  国知局采集失败: {e}")

    # 1b: WIPO（默认关闭，配置中启用）
    if SOURCES.get("wipo", {}).get("enabled", False):
        try:
            articles = scrape_wipo(max_articles=5)
            all_articles.extend(articles)
            logger.info(f"  WIPO: 采集到 {len(articles)} 篇")
        except Exception as e:
            logger.error(f"  WIPO 采集失败: {e}")

    # 1c: 知产媒体（默认关闭，配置中启用）
    if SOURCES.get("zhichanli", {}).get("enabled", False):
        try:
            articles = scrape_media_sites(max_articles=5)
            all_articles.extend(articles)
            logger.info(f"  知产媒体: 采集到 {len(articles)} 篇")
        except Exception as e:
            logger.error(f"  知产媒体采集失败: {e}")

    # 1d: IPRdaily（默认关闭，配置中启用）
    if SOURCES.get("iprdaily", {}).get("enabled", False):
        try:
            articles = scrape_iprdaily(max_articles=8)
            all_articles.extend(articles)
            logger.info(f"  IPRdaily: 采集到 {len(articles)} 篇")
        except Exception as e:
            logger.error(f"  IPRdaily 采集失败: {e}")

    # 1e: 微信公众号（可选，通过环境变量开启）
    wechat_accounts = os.getenv("WECHAT_ACCOUNTS", "")
    if wechat_accounts:
        for account in wechat_accounts.split(","):
            account = account.strip()
            if account:
                try:
                    articles = search_wechat_account(account, max_articles=3)
                    all_articles.extend(articles)
                    logger.info(f"  公众号[{account}]: 采集到 {len(articles)} 篇")
                except Exception as e:
                    logger.error(f"  公众号[{account}] 采集失败: {e}")

    # 1f: 人工推荐的文章链接（单独收集，不受自动筛选影响）
    manual_links_file = os.path.join(DATA_DIR, "manual_links.md")
    manual_articles = []
    try:
        manual_articles = load_manual_links(manual_links_file)
        if manual_articles:
            logger.info(f"  人工推荐: {len(manual_articles)} 篇")
    except Exception as e:
        logger.error(f"  人工推荐加载失败: {e}")

    if not all_articles and not manual_articles:
        logger.warning("⚠️ 今日未采集到任何文章")
        save_last_run(LAST_RUN_FILE)
        return

    logger.info(f"\n📊 共采集 {len(all_articles)} 篇（自动）+ {len(manual_articles)} 篇（人工）")

    # 文章筛选 - 只对自动采集的文章做关键词过滤
    # 人工推荐的文章由用户亲自挑选，直接通过
    if all_articles:
        all_articles = filter_articles(all_articles)
        logger.info(f"  自动采集筛选后: {len(all_articles)} 篇")

    # 合并人工推荐（不经过滤）
    all_articles.extend(manual_articles)
    logger.info(f"  合并后共 {len(all_articles)} 篇")

    # 去重
    if len(all_articles) > 1:
        all_articles = dedup_articles(all_articles)
        logger.info(f"  去重后共 {len(all_articles)} 篇")

    if not all_articles:
        logger.warning("⚠️ 筛选后无符合要求的文章，终止流程")
        save_last_run(LAST_RUN_FILE)
        return

    # ---------------------------------------------------------
    # 步骤 2: AI 摘要
    # ---------------------------------------------------------
    logger.info("\n🤖 阶段2: AI 摘要生成")
    summarizer = AISummarizer()
    all_articles = summarizer.summarize_batch(all_articles)

    # ---------------------------------------------------------
    # 步骤 3: 分类整理
    # ---------------------------------------------------------
    logger.info("\n📂 阶段3: 分类整理")
    categorized = {}
    for article in all_articles:
        cat = categorize_article(article)
        if cat not in categorized:
            categorized[cat] = []
        formatted = format_article_for_digest(article, category=cat)
        categorized[cat].append(formatted)

    for cat, items in categorized.items():
        logger.info(f"  {cat}: {len(items)} 篇")

    # ---------------------------------------------------------
    # 步骤 4: 生成并发布早报
    # ---------------------------------------------------------
    logger.info("\n📰 阶段4: 生成并发布早报")

    date_str = datetime.now().strftime("%Y年%m月%d日")
    title = build_daily_title(date_str)

    # 准备分类数据
    articles_by_category = {}
    for cat, items in categorized.items():
        articles_by_category[cat] = [(item, "") for item in items]

    # 初始化发布器（复用同一个，避免重复获取 token）
    publisher = WeChatDraftPublisher()

    # 生成并上传头图
    header_image_url = ""
    try:
        img_data = generate_header_image(
            title="知产早报",
            date_str=date_str,
            article_count=len(all_articles),
        )
        if img_data:
            header_image_url = publisher.upload_content_image(img_data)
            if header_image_url:
                logger.info(f"头图上传成功")
            else:
                logger.info("头图上传失败，使用纯文字版")
    except Exception as e:
        logger.warning(f"头图生成/上传失败: {e}")

    html_content = generate_daily_digest_html(
        date_str=date_str,
        articles_by_category=articles_by_category,
        header_image_url=header_image_url,
    )
    media_id = publisher.create_draft(
        title=title,
        html_content=html_content,
    )

    if media_id:
        logger.info(f"✅ 早报草稿创建成功！media_id: {media_id}")
        # 同时保存一份 HTML 到本地备份
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        # 清理过期备份
        cleanup_old_backups(backup_dir, BACKUP_RETENTION_DAYS)
        backup_file = os.path.join(
            backup_dir,
            f"digest_{datetime.now().strftime('%Y%m%d')}.html"
        )
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"📁 本地备份已保存: {backup_file}")
    else:
        logger.error("❌ 草稿创建失败！")
        # 降级方案：将 HTML 保存到本地
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        fallback_file = os.path.join(
            backup_dir,
            f"digest_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        with open(fallback_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"📁 已保存降级备份: {fallback_file}")
        logger.info("💡 你可以打开此文件，复制内容手动粘贴到公众号后台")

    # ---------------------------------------------------------
    # 保存运行记录
    # ---------------------------------------------------------
    save_last_run(LAST_RUN_FILE)
    logger.info("\n✅ 今日流程完成！")


if __name__ == "__main__":
    main()
