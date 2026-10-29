@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0GSVI\GPT-SoVITS-1007-cu124"

echo ==========================================================
echo   GPT-SoVITS 本地配音服务  ^(中文 / 日语 / 跨语言^)
echo   接口地址 : http://127.0.0.1:8000
echo   浏览器   : 服务就绪后自动打开（约 12 秒）
echo   音色目录 : models\v4\^<类别-语言-角色名^>
echo   关闭本窗口 = 停止服务
echo ==========================================================
echo.

rem 延迟打开浏览器，避免页面先于服务就绪而显示“无法连接”
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 12; Start-Process 'http://127.0.0.1:8000'"

call gsvi.bat

echo.
echo 服务已退出。
pause
endlocal
