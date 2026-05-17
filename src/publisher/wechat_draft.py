# -*- coding: utf-8 -*-
"""
微信公众号草稿箱发布模块
------------------------
通过微信公众平台 API 创建草稿。

流程：
  1. 上传默认封面图（永久素材）
  2. 用该封面 media_id 创建草稿
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

import requests

from config import WECHAT_APPID, WECHAT_SECRET

logger = logging.getLogger(__name__)

# 默认封面图路径（项目目录下的默认图片）
DEFAULT_THUMB = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "default_thumb.png"
)


class WeChatDraftPublisher:
    """微信公众号草稿箱发布器"""

    TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
    DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
    MATERIAL_ADD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
    IMAGE_UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"

    def __init__(self, appid: Optional[str] = None, secret: Optional[str] = None):
        self.appid = appid or WECHAT_APPID
        self.secret = secret or WECHAT_SECRET
        self.token = ""
        self.token_expires_at = 0

    def _get_access_token(self) -> str:
        now = time.time()
        if self.token and now < self.token_expires_at - 300:
            return self.token
        if not self.appid or not self.secret:
            raise ValueError("微信公众号 appid 和 secret 未配置")
        params = {"grant_type": "client_credential", "appid": self.appid, "secret": self.secret}
        resp = requests.get(self.TOKEN_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        self.token = data["access_token"]
        self.token_expires_at = now + data.get("expires_in", 7200)
        logger.info("access_token 刷新成功")
        return self.token

    def _upload_thumb(self, image_path: str) -> Optional[str]:
        """上传永久素材封面图，返回 media_id"""
        try:
            token = self._get_access_token()
            url = f"{self.MATERIAL_ADD_URL}?access_token={token}&type=image"
            with open(image_path, "rb") as f:
                resp = requests.post(url, files={"media": f}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if "media_id" in data:
                logger.info(f"封面图上传成功: {data['media_id']}")
                return data["media_id"]
            else:
                logger.warning(f"封面图上传失败: {data}")
                return None
        except Exception as e:
            logger.warning(f"封面图上传异常: {e}")
            return None

    def upload_content_image(self, image_data: bytes) -> Optional[str]:
        """
        上传正文图片到微信，返回可用于 <img> 标签的 URL。

        使用 cgi-bin/media/uploadimg 接口（不占用永久素材额度）。

        Args:
            image_data: 图片的二进制数据（PNG/JPEG）

        Returns:
            图片 URL，失败返回 None
        """
        try:
            token = self._get_access_token()
            url = f"{self.IMAGE_UPLOAD_URL}?access_token={token}"

            # 用 BytesIO 包装后上传
            from io import BytesIO
            files = {"media": ("header.png", BytesIO(image_data), "image/png")}
            resp = requests.post(url, files=files, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "url" in data:
                logger.info(f"正文图片上传成功")
                return data["url"]
            else:
                logger.error(f"正文图片上传失败: {data}")
                return None
        except Exception as e:
            logger.error(f"正文图片上传异常: {e}")
            return None

    def create_draft(self, title: str, html_content: str,
                     thumb_media_id: str = "") -> Optional[str]:
        try:
            token = self._get_access_token()
        except (ValueError, RuntimeError) as e:
            logger.error(f"token 获取失败: {e}")
            return None

        # 如果没有提供 media_id，尝试上传默认封面图
        if not thumb_media_id and os.path.exists(DEFAULT_THUMB):
            thumb_media_id = self._upload_thumb(DEFAULT_THUMB) or ""

        article = {
            "title": title,
            "content": html_content,
        }

        if thumb_media_id:
            article["thumb_media_id"] = thumb_media_id

        payload = {"articles": [article]}

        try:
            # 关键：ensure_ascii=False 保证中文不转成 \uXXXX
            body = json.dumps(payload, ensure_ascii=False, default=str)
            resp = requests.post(
                self.DRAFT_ADD_URL,
                params={"access_token": token},
                data=body.encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if "media_id" in data:
                logger.info(f"草稿创建成功！media_id: {data['media_id']}")
                return data["media_id"]
            else:
                logger.error(f"创建草稿失败。完整响应: {data}")
                logger.info("尝试不带封面图再试一次...")

                # 尝试不带封面图
                payload2 = {"articles": [{"title": title, "content": html_content}]}
                resp2 = requests.post(
                    self.DRAFT_ADD_URL,
                    params={"access_token": token},
                    json=payload2,
                    timeout=30,
                )
                data2 = resp2.json()
                if "media_id" in data2:
                    logger.info(f"草稿创建成功！media_id: {data2['media_id']}")
                    return data2["media_id"]
                else:
                    logger.error(f"再次失败: {data2}")
                    return None

        except requests.RequestException as e:
            logger.error(f"创建草稿请求失败: {e}")
            return None


# ============================================================
# 早报 HTML 模板
# ============================================================

def generate_daily_digest_html(date_str: str, articles_by_category: dict,
                                digest_title: str = "知产早报",
                                header_image_url: str = "") -> str:
    total = sum(len(items) for items in articles_by_category.values())

    # 头图（如果有）
    header_html = ""
    if header_image_url:
        header_html = f'''
<div style="margin:0 -16px 6px -16px;">
    <img src="{header_image_url}" alt="{digest_title}"
         style="width:100%;max-width:100%;display:block;">
</div>'''

    # 5大板块定义
    sections_def = [
        ("官媒信息政策", "#1a73e8", "📋"),
        ("行业信息", "#0f9d58", "🏢"),
        ("案例分享", "#d93025", "⚖️"),
        ("热点关注", "#9334e6", "🔥"),
        ("会议培训", "#0dc2b8", "📅"),
    ]

    # 只包含有内容的板块
    active_sections = [(n, c, i) for n, c, i in sections_def
                       if articles_by_category.get(n, [])]

    # --- 导航栏 ---
    nav_html = ""
    if active_sections:
        nav_items = "".join(
            f'<span style="display:inline-block;padding:5px 14px;margin:3px 3px;font-size:12px;'
            f'color:{c};background:{c}0d;border-radius:16px;'
            f'font-weight:500;">{i} {n}</span>'
            for n, c, i in active_sections
        )
        nav_html = f'<div style="margin:14px -4px 0 -4px;text-align:center;">{nav_items}</div>'

    # --- 内容 ---
    content_html = ""
    for name, color, icon in active_sections:
        items = articles_by_category.get(name, [])
        content_html += f'''
<div style="margin-top:20px;padding:16px 0 4px 0;">
    <div style="display:flex;align-items:center;">
        <span style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:{color};border-radius:7px;margin-right:10px;">
            <span style="font-size:14px;">{icon}</span>
        </span>
        <span style="font-size:20px;font-weight:700;color:#1d1d1f;letter-spacing:-0.3px;">{name}</span>
        <span style="margin-left:8px;font-size:13px;color:#86868b;font-weight:400;">{len(items)}篇</span>
    </div>
    <div style="width:24px;height:3px;background:{color};border-radius:2px;margin-top:8px;margin-left:38px;"></div>
</div>'''
        for item in items:
            text = item[0] if isinstance(item, tuple) else item
            content_html += f'<div style="margin:2px 0 0 0;">{text}</div>'

    return f"""\
<section style="padding:6px 16px 24px 16px;max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif;color:#1d1d1f;background:#fff;">
    {header_html}
    <div style="text-align:center;padding:20px 0 8px 0;">
        <div style="font-size:26px;font-weight:700;color:#1d1d1f;letter-spacing:-0.5px;">知产早报</div>
        <div style="font-size:14px;color:#86868b;margin-top:6px;">{date_str}</div>
        <div style="margin-top:14px;font-size:13px;color:#86868b;">
            今日收录 <span style="font-weight:700;color:#1d1d1f;">{total}</span> 条知识产权要闻
        </div>
    </div>
    {nav_html}
    <div style="height:1px;background:#e8eaed;margin:18px 0 0 0;"></div>
    {content_html}
    <div style="margin-top:36px;padding:20px;background:#f5f5f7;border-radius:12px;">
        <div style="font-size:13px;color:#86868b;line-height:1.8;">
            <span style="font-weight:600;color:#1d1d1f;">免责声明</span><br>
            本文由 AI 辅助整理生成，仅供参考，不构成任何法律意见。<br>
            请以官方原文为准，如需专业意见请咨询知识产权律师。<br>
            内容来源：国家知识产权局（CNIPA）及公开网络信息
        </div>
    </div>
    <div style="text-align:center;padding:24px 0 6px 0;">
        <span style="font-size:12px;color:#c7c7cc;">知产早报 · AI 驱动的知识产权资讯</span>
    </div>
</section>"""


def build_daily_title(date_str: str) -> str:
    return f"知产早报 | {date_str}"
