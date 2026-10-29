@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0音色库"

echo ==========================================================
echo   音色库 · 配音台 / 角色声音安装
echo   默认地址 : http://127.0.0.1:8899
echo   （8899 被别的程序占用时会自动换 8900~8910，
echo     具体地址看下面这行输出，浏览器也会自动打开）
echo   关闭本窗口 = 停止这个工具（不影响配音服务）
echo ==========================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  py server.py --open
) else (
  python server.py --open
)

echo.
echo 工具已退出。
pause
endlocal
