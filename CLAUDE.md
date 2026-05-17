# IP 信息中枢 - 知产早报

## 项目概述
每日自动采集知识产权新闻（CNIPA 官网），AI 生成摘要，发布到微信公众号草稿箱。

## 技术栈
- Python 3.14 (Windows)
- Pillow (头图生成)
- DeepSeek API (AI 摘要)
- 微信公众号 API (草稿箱发布)

## 快速启动

```bash
D: && cd \daily\ip-news-hub && python scripts\collect.py
```

## 项目结构
```
ip-news-hub/
├── scripts/
│   └── collect.py          # 主流程
├── src/
│   ├── scrapers/
│   │   ├── base.py          # 采集器基类
│   │   ├── cnipa.py         # 国知局采集
│   │   └── url_loader.py    # 手动链接导入
│   ├── ai/
│   │   └── summarizer.py    # DeepSeek 摘要
│   ├── publisher/
│   │   └── wechat_draft.py  # 微信草稿箱发布
│   └── utils/
│       ├── filter.py        # 文章筛选
│       └── image_gen.py     # 头图生成
├── data/
│   ├── manual_links.md      # 人工推荐链接（放 URL 的地方）
│   └── backups/             # 备份文件
├── config.py                # 配置文件
├── .env                     # API 密钥（勿提交）
└── CLAUDE.md                # 本文件
```

## 配置说明
- `.env` 文件存放：`DEEPSEEK_API_KEY`、`WECHAT_APPID`、`WECHAT_SECRET`
- 微信 API 需要在公众号后台配置 IP 白名单
- `data/manual_links.md` 中粘贴 URL（每行一个，不要放在 `#` 开头行）

## 文章分类
采集的文章自动归入 5 大板块：
1. **官媒信息政策**（CNIPA 通知/办法/意见等）
2. **行业信息**（行业动态/媒体报道）
3. **案例分享**（诉讼/侵权/判决案例）
4. **热点关注**（海外知产/前沿趋势）
5. **会议培训**（论坛/讲座/培训活动）

## 注意
- 不要在 `manual_links.md` 中使用中文注释，避免编码问题
- 图片上传依赖微信 `media/uploadimg` 接口
- 头图生成依赖 Pillow（无需额外安装）
