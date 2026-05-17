# -*- coding: utf-8 -*-
"""
IP 信息中枢 - 配置文件

配置读取优先级：
1. 环境变量（最高优先级，GitHub Actions 使用）
2. .env 文件（本地开发使用）
"""
import os

# ============================================================
# 自动从 .env 文件加载配置（如果存在）
# ============================================================
_env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_file):
    with open(_env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            # 只在环境变量未设置时使用 .env 的值
            if key not in os.environ:
                os.environ[key] = value

# ============================================================
# AI API 配置
# ============================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ============================================================
# 微信公众号配置
# ============================================================
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

# ============================================================
# 采集源配置
# ============================================================
SOURCES = {
    "cnipa": {
        "name": "国家知识产权局",
        "type": "gov",
        "list_url": "https://www.cnipa.gov.cn/col/col75/index.html",
        "enabled": True,
    },
    "wipo": {
        "name": "WIPO",
        "type": "gov",
        "list_url": "https://www.wipo.int/pressroom/en/",
        "enabled": True,       # ✅ 已启用
    },
    "zhichanli": {
        "name": "知产力",
        "type": "media",
        "list_url": "https://www.zhichanli.com/",
        "enabled": True,       # ✅ 已启用
    },
    "iprdaily": {
        "name": "IPRdaily",
        "type": "media",
        "list_url": "https://www.iprdaily.cn/",
        "enabled": True,       # ✅ 已启用
    },
}

# ============================================================
# 数据管理
# ============================================================
BACKUP_RETENTION_DAYS = 7     # 备份文件保留天数

# ============================================================
# 代理配置
# ============================================================
HTTP_PROXY = os.getenv("HTTP_PROXY", "")

# ============================================================
# 请求配置
# ============================================================
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 3

# ============================================================
# 数据路径
# ============================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LAST_RUN_FILE = os.path.join(DATA_DIR, "last_run.json")
