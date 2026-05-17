@echo off
chcp 65001 >nul
echo ====================================
echo   IP 早报 - 添加文章链接
echo ====================================
echo.
echo 把今天看到的好文章链接贴进来
echo 一行一个，输完后输入 "end" 结束
echo.
echo 示例:
echo   https://mp.weixin.qq.com/s/xxxxx
echo   https://mp.weixin.qq.com/s/yyyyy # 商标新规
echo.
echo ====================================
echo.

setlocal enabledelayedexpansion

set FILE=%~dp0data\manual_links.md

echo # 人工采集的文章链接 > "%FILE%"
echo # 添加时间：%date% %time% >> "%FILE%"
echo # ------------------------------------------------- >> "%FILE%"
echo. >> "%FILE%"

:loop
set /p INPUT=^> 
if /i "!INPUT!"=="end" goto done
if "!INPUT!"=="" goto loop
echo !INPUT! >> "%FILE%"
goto loop

:done
echo.
echo ====================================
echo ✅ 已保存到 data\manual_links.md
echo 共 %INPUT_COUNT% 个链接
echo.
echo 现在运行: python scripts\collect.py
echo ====================================
pause
