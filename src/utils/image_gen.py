"""
每日头图生成器
--------------
用 Pillow 生成早报头图：标题 + 日期 + 文章数
输出为 PNG 字节流，用于上传到微信素材库。
"""
import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

# 品牌色
PRIMARY_BLUE = (26, 115, 232)
DARK_BLUE = (21, 92, 186)
WHITE = (255, 255, 255)
LIGHT_GRAY = (240, 244, 249)
ACCENT_GOLD = (255, 183, 64)

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")

# 字体搜索路径（Windows 优先，其次 Linux）
_WINDOWS_FONTS = [
    "C:/Windows/Fonts/msyhbd.ttc",    # 微软雅黑 Bold
    "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑 Regular
    "C:/Windows/Fonts/simhei.ttf",     # 黑体
    "C:/Windows/Fonts/simsun.ttc",     # 宋体
]

_LINUX_FONTS = [
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]


def _find_font(bold: bool = False) -> Optional[str]:
    """搜索可用的中文字体"""
    # 优先 Windows 字体
    for font_path in _WINDOWS_FONTS:
        if os.path.exists(font_path):
            return font_path
    # Linux 兜底
    for font_path in _LINUX_FONTS:
        if os.path.exists(font_path):
            return font_path
    # assets/fonts 目录
    os.makedirs(FONT_DIR, exist_ok=True)
    for fname in os.listdir(FONT_DIR):
        if fname.endswith((".ttf", ".ttc")):
            return os.path.join(FONT_DIR, fname)
    return None


def generate_header_image(
    title: str = "知产早报",
    date_str: str = "",
    article_count: int = 0,
    width: int = 600,
    height: int = 240,
) -> Optional[bytes]:
    """
    生成早报头图

    Returns:
        PNG 图片的字节数据，失败返回 None
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("Pillow 未安装，无法生成头图")
        return None

    # 创建画布
    img = Image.new("RGB", (width, height), PRIMARY_BLUE)
    draw = ImageDraw.Draw(img)

    # --- 背景装饰：渐变效果 ---
    for y in range(height):
        ratio = y / height
        r = int(PRIMARY_BLUE[0] * (1 - ratio) + DARK_BLUE[0] * ratio)
        g = int(PRIMARY_BLUE[1] * (1 - ratio) + DARK_BLUE[1] * ratio)
        b = int(PRIMARY_BLUE[2] * (1 - ratio) + DARK_BLUE[2] * ratio)
        for x in range(width):
            draw.point((x, y), fill=(r, g, b))

    # --- 装饰斜线/几何元素 ---
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # 右下角装饰圆
    overlay_draw.ellipse(
        [width - 120, height - 110, width - 20, height - 10],
        fill=(255, 255, 255, 18),
    )
    overlay_draw.ellipse(
        [width - 90, height - 90, width - 40, height - 40],
        fill=(255, 255, 255, 12),
    )
    # 左上角小装饰
    overlay_draw.ellipse(
        [-30, -30, 60, 60], fill=(255, 255, 255, 15)
    )
    # 底部分隔线
    overlay_draw.rectangle(
        [0, height - 4, width, height], fill=(255, 183, 64, 200)
    )

    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    # --- 绘制文字 ---
    draw = ImageDraw.Draw(img)

    font_path = _find_font()

    # 标题文字（大号）
    try:
        font_title = ImageFont.truetype(font_path, 48) if font_path else ImageFont.load_default()
    except Exception:
        font_title = ImageFont.load_default()

    # 日期（中号）
    try:
        font_date = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
    except Exception:
        font_date = ImageFont.load_default()

    # 统计信息（小号）
    try:
        font_stat = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default()
    except Exception:
        font_stat = ImageFont.load_default()

    # 标题
    title_x = 40
    title_y = 50
    draw.text((title_x, title_y), title, fill=WHITE, font=font_title)

    # 标题下方装饰线
    draw.rectangle(
        [title_x, title_y + 58, title_x + 60, title_y + 62],
        fill=ACCENT_GOLD,
    )

    # 日期
    if not date_str:
        date_str = datetime.now().strftime("%Y年%m月%d日")
    draw.text((title_x, title_y + 80), date_str, fill=(220, 230, 245), font=font_date)

    # 文章统计
    if article_count > 0:
        stat_text = f"收录 {article_count} 条 IP 要闻"
        # 在右下角显示
        try:
            stat_bbox = draw.textbbox((0, 0), stat_text, font=font_stat)
            stat_w = stat_bbox[2] - stat_bbox[0]
            stat_x = width - stat_w - 30
            stat_y = height - 45
        except Exception:
            stat_x = 40
            stat_y = height - 45
        draw.text((stat_x, stat_y), stat_text, fill=(180, 200, 230), font=font_stat)

    # --- 输出为 PNG 字节 ---
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    logger.info(f"头图生成成功: {width}x{height}, 文章数={article_count}")
    return buf.getvalue()
