@echo off
chcp 65001 >nul
setlocal
rem BERT 模型走国内镜像，直连 huggingface.co 会超时导致引擎起不来
set "HF_ENDPOINT=https://hf-mirror.com"
cd /d "%~dp0AivisSpeech"

echo ==========================================================
echo   AivisSpeech 日语配音  ^(VOICEVOX 兼容引擎^)
echo   编辑器   : %~dp0AivisSpeech\AivisSpeech.exe
echo   引擎接口 : http://127.0.0.1:10101 （由编辑器自动拉起）
echo   声线目录 : %%APPDATA%%\AivisSpeech-Engine\Models
echo ==========================================================
echo.

start "" "%~dp0AivisSpeech\AivisSpeech.exe"

echo 已启动 AivisSpeech 编辑器。
echo 首次启动需要下载 BERT 模型（约 1.3GB，已走 hf-mirror 镜像）。
echo 如需只用接口（不打开编辑器），可在 AivisSpeech-Engine 目录执行：
echo   run.exe --host 127.0.0.1 --port 10101 --use_gpu
echo.
timeout /t 5 /nobreak >nul
endlocal
