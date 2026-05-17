# IP 信息中枢 - 零服务器知识产权资讯自动化

每日自动采集知产资讯 → AI 摘要 → 推送微信公众号草稿箱。

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/你的用户名/ip-news-hub.git
cd ip-news-hub
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

需要准备：
- **DeepSeek API Key**：在 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取
- **微信公众号 appid + secret**：公众号后台 → 开发 → 基本配置

### 4. 本地测试
```bash
# 测试国知局采集
python -m src.scrapers.cnipa

# 测试全流程
python scripts/collect.py
```

### 5. 部署到 GitHub Actions

1. 在 GitHub 创建仓库并推送代码
2. 进入仓库 Settings → Secrets and variables → Actions
3. 添加以下 Secrets：
   - `DEEPSEEK_API_KEY`
   - `WECHAT_APPID`
   - `WECHAT_SECRET`
4. Workflow 会自动在北京时间工作日 05:30 运行

## 项目结构

```
ip-news-hub/
├── .github/workflows/daily-digest.yml   # GitHub Actions 定时任务
├── scripts/collect.py                   # 主流程脚本
├── src/
│   ├── scrapers/                        # 采集器
│   │   ├── base.py                      # 基类
│   │   ├── cnipa.py                     # 国知局
│   │   ├── wipo.py                      # WIPO
│   │   ├── media_sites.py               # 知产媒体
│   │   └── wechat.py                    # 公众号(搜狗)
│   ├── ai/summarizer.py                 # AI 摘要
│   ├── publisher/wechat_draft.py        # 公众号发布+HTML模板
│   └── utils/helpers.py                 # 工具函数
├── config.py                            # 配置文件
├── requirements.txt
└── .env.example
```

## 合规说明

- 采集的文章仅提取标题+摘要+链接，不全文搬运
- 文末标注 AI 辅助生成声明
- 最终发布前仍需人工审核
