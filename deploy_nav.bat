@echo off
chcp 65001 >nul
title 知产导航 - GitHub Pages 部署工具
echo ============================================
echo   知产导航 GitHub Pages 部署
echo ============================================
echo.
echo 此脚本将把你的 ip-nav.html 部署到 GitHub Pages
echo.
echo 准备步骤：
echo  1. 打开 https://github.com/new
echo  2. 仓库名填: ip-nav
echo  3. 选 Public，不要勾选任何初始化选项
echo  4. 点击 "Create repository"
echo  5. 复制显示的仓库地址 (https://github.com/你的用户名/ip-nav.git)
echo.
set /p REPO_URL="请输入仓库地址: "
if "%REPO_URL%"=="" (
    echo 错误：仓库地址不能为空
    pause
    exit /b 1
)

echo.
echo 正在部署...
cd /d D:\daily\ip-news-hub

:: 初始化 git 仓库（如果还没有）
if not exist .git (
    git init
    echo Git 仓库初始化完成
) else (
    echo Git 仓库已存在
)

:: 创建 gh-pages 分支（只含导航页）
git checkout --orphan gh-pages 2>nul
if %errorlevel% neq 0 (
    git checkout -b gh-pages
)

:: 只保留导航页
git rm -r --cached . 2>nul
git add ip-nav.html
git -c user.name="IP Nav" -c user.email="ipnav@local" commit -m "deploy: 知产导航页"

:: 推送到 GitHub
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git push -f origin gh-pages

if %errorlevel% equ 0 (
    echo.
    echo ===========================================
    echo ✅ 部署成功！
    echo.
    echo 下一步：
    echo  1. 打开 https://github.com/你的用户名/ip-nav/settings/pages
    echo  2. Source 选 "Deploy from a branch"
    echo  3. Branch 选 "gh-pages" / 根目录 "(root)"
    echo  4. 点 Save
    echo  5. 等待 1-2 分钟，访问：
    echo     https://你的用户名.github.io/ip-nav/
    echo.
    echo 设为浏览器新标签页：
    echo  - Edge: 设置 → 开始、主页和新建标签页
    echo  - Chrome: 安装 "New Tab Redirect" 扩展
    echo ===========================================
) else (
    echo.
    echo ❌ 推送失败，请检查：
    echo  1. 仓库地址是否正确
    echo  2. 是否已在 GitHub 创建仓库
    echo  3. 网络是否正常
)

pause
