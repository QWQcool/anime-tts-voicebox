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

rem 依次尝试：系统 python -> py 启动器 -> GSVI 自带运行时（setup.ps1 一定装过）
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE (
  where py >nul 2>nul && set "PYEXE=py"
)
if not defined PYEXE (
  if exist "%~dp0GSVI\GPT-SoVITS-1007-cu124\runtime\python.exe" (
    set "PYEXE=%~dp0GSVI\GPT-SoVITS-1007-cu124\runtime\python.exe"
  )
)

if not defined PYEXE (
  echo [错误] 找不到 Python。
  echo        先跑一遍 setup.ps1（会把自带运行时装到 GSVI\），
  echo        或者自己装 Python 3.11+ 并勾选 "Add to PATH"。
  pause
  exit /b 1
)

echo 使用解释器: %PYEXE%
echo.
"%PYEXE%" server.py --open

echo.
echo 工具已退出。
pause
endlocal
