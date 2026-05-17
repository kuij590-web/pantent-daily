## 当前状态检查清单

### ✅ 已完成
- [x] 项目骨架搭建（目录结构、配置系统）
- [x] CNIPA 通知公告采集器
- [x] WIPO 新闻采集器（待启用测试）
- [x] 知产媒体采集器（待启用测试）
- [x] URL 手动链接导入
- [x] AI 摘要生成（DeepSeek API）
- [x] 微信公众号草稿箱发布
- [x] 头图生成（Pillow）
- [x] 5 板块分类系统
- [x] 文章筛选器（包含/排除关键词）
- [x] GitHub Actions 定时任务
- [x] 知产导航页面（105+ 链接，10 板块，favicon）
- [x] 添加链接页面（add_link.html）
- [x] 项目说明文档（CLAUDE.md、README.md）
- [x] IPRdaily 采集器（src/scrapers/iprdaily.py）
- [x] 文章去重逻辑（URL + 标题相似度）
- [x] 备份保留策略（保留 7 天，自动清理）
- [x] 导航页实时搜索过滤
- [x] 导航页暗黑模式（带 localStorage 记忆）
- [x] 部署脚本（deploy_nav.bat）
- [x] 完整实施计划（PLAN.md）

### 🔧 需在 Windows 环境测试启用
- [ ] 测试 WIPO 采集：`python -m src.scrapers.wipo`
- [ ] 测试知产力采集：config.py 中启用 zhichanli → True
- [ ] 测试 IPRdaily 采集：config.py 中启用 iprdaily → True
- [ ] 测试完整流程：`python scripts/collect.py`

### 📅 需手动完成
- [ ] GitHub 创建仓库 ip-nav → 运行 deploy_nav.bat → 启用 Pages
- [ ] 将导航页设为浏览器新标签页
- [ ] 配置 GitHub Actions Secrets（DEEPSEEK_API_KEY / WECHAT_APPID / WECHAT_SECRET）
- [ ] 微信公众号添加 IP 白名单

### 🎯 长期规划
- [ ] 浏览器新标签页扩展
- [ ] 数据看板（IP 行业统计）
- [ ] 团队协作（多人提交链接）
- [ ] 知产行业日历