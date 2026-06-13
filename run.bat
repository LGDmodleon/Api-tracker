@echo off
chcp 65001 >nul
cd /d "%~dp0"
title API供应商排行榜追踪系统

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║     API供应商排行榜数据采集系统           ║
echo   ╚══════════════════════════════════════════╝
echo.

:: 检查Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [错误] 未检测到Python环境
    echo   请先安装Python 3.8+: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 运行数据采集
echo   [数据采集]
python "%~dp0main.py"
if %errorlevel% neq 0 (
    echo.
    echo   [错误] 数据采集失败，请检查网络连接。
    echo.
    pause
    exit /b 1
)

:: 打开网站
echo.
echo   正在打开可视化网站...
start "" "%~dp0site\index.html"

echo.
echo   ✓ 完成！网站已在浏览器中打开。
echo.
echo   按任意键关闭此窗口...
pause >nul
