"""
工具函数
--------
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def load_last_run(data_file: str) -> Optional[str]:
    """
    读取上次运行记录，返回上次成功运行的日期字符串 "YYYY-MM-DD"
    如果文件不存在或出错，返回 None
    """
    try:
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_run_date")
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"读取上次运行记录失败: {e}")
    return None


def save_last_run(data_file: str, date_str: Optional[str] = None):
    """保存本次运行记录"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump({"last_run_date": date_str}, f, ensure_ascii=False, indent=2)
        logger.info(f"运行记录已保存: {date_str}")
    except OSError as e:
        logger.error(f"保存运行记录失败: {e}")


def trim_text(text: str, max_length: int = 5000) -> str:
    """截断文本到指定长度，用于 API 调用限制"""
    if len(text) > max_length:
        return text[:max_length] + "...[已截断]"
    return text


def is_same_day(articles: list, date_str: str) -> bool:
    """判断文章列表是否都是某一天的（按发布日期筛选）"""
    if not date_str:
        return False
    for a in articles:
        if date_str in a.get("publish_date", ""):
            return True
    return False


def format_date_for_display(date_str: str) -> str:
    """格式化日期为显示友好的格式"""
    if not date_str:
        return "未知"
    return date_str
