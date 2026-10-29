<#
  本地二次元 TTS 环境 · 一键安装
  ---------------------------------------------------------------
  作用：把 GPT-SoVITS 推理包、中文/日语音色、AivisSpeech 装到本目录。
  不包含：模型权重本身（约 15 GB，全部现下），音色与音频产物。

  用法（在本目录打开 PowerShell）：
      powershell -ExecutionPolicy Bypass -File .\setup.ps1

  可选参数：
      -SkipGsv            跳过 14 GB 的 GPT-SoVITS 推理包
      -SkipAivis          跳过 AivisSpeech（日语专用，可选）
      -SkipVoices         跳过音色下载
      -WithAivisVoices    额外下 2 个 AivisHub 声线（约 480 MB）
      -Voices '蔚蓝档案/中文/白子','蔚蓝档案/中文/爱丽丝'

  要求：Windows 10/11 + NVIDIA 显卡（驱动 ≥551）+ D 盘 ≥30 GB + 能访问 modelscope.cn
#>
[CmdletBinding()]
param(
    [string]$Root = '',
    [switch]$SkipGsv,
    [switch]$SkipAivis,
    [switch]$SkipVoices,
    [switch]$WithAivisVoices,
    [string[]]$Voices = @('蔚蓝档案/中文/爱丽丝', '蔚蓝档案/日语/爱丽丝')
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- 常量
$GSV_REPO = 'aihobbyist/GPT-SoVITS-Inference'
$GSV_FILE = 'GPT-SoVITS-1007-cu124.7z'
$GSV_URL = "https://www.modelscope.cn/models/$GSV_REPO/resolve/master/$GSV_FILE"
$GSV_BYTES = 7844088481
$VOICE_REPO = 'aihobbyist/GPT-SoVITS_Model_Collection'
$AIVIS_URL = 'https://github.com/Aivis-Project/AivisSpeech/releases/download/1.0.0/AivisSpeech-Windows-x64-1.0.0.zip'
$AIVIS_VOICES = @(
    @{ name = 'まお'; uuid = 'a59cb814-0083-4369-8542-f51a29e72af7' },
    @{ name = 'コハク'; uuid = '22e8ed77-94fe-4ef2-871f-a86f94e9a579' }
)

if (-not $Root) {
    $Root = $PSScriptRoot
    if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $Root) { $Root = (Get-Location).Path }
}
$Root = (Resolve-Path -LiteralPath $Root).Path
$GsvDir = Join-Path $Root 'GSVI\GPT-SoVITS-1007-cu124'
$V4Dir = Join-Path $GsvDir 'models\v4'
$TmpDir = Join-Path $Root '_packages'
$aivisDir = Join-Path $Root 'AivisSpeech'
$aivisModels = Join-Path $env:APPDATA 'AivisSpeech-Engine\Models'
$sevenZip = Join-Path $Root '7zr.exe'

# ---------------------------------------------------------------- 输出helper
function Info($m) { Write-Host "[..] $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[!!] $m" -ForegroundColor Yellow }
function Step($m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Magenta }

# ---------------------------------------------------------------- env check
function Test-Environment {
    Step '环境检查'

    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $info = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
        Ok "显卡: $info"
        $drv = ($info -split ',')[-1].Trim()
        $major = [int]($drv.Split('.')[0])
        if ($major -lt 551) { Warn "驱动 $drv < 551，CUDA 12.4 可能初始化失败，建议先升级驱动" }
    }
    else {
        Warn '没有检测到 nvidia-smi。这套包是 CUDA 版，纯 CPU 机器跑不动，请先确认显卡。'
    }

    $free = (Get-PSDrive -Name ([IO.Path]::GetPathRoot($Root).TrimEnd(':\')) -ErrorAction SilentlyContinue)
    if ($free) {
        $gb = [math]::Round($free.Free / 1GB, 1)
        if ($gb -lt 25) { Warn "目标盘剩余 $gb GB，建议 ≥30 GB（解压后 14 GB + 安装包 7.5 GB）" } else { Ok "目标盘剩余 $gb GB" }
    }

    foreach ($need in @('curl.exe')) {
        if (-not (Get-Command $need -ErrorAction SilentlyContinue)) { throw "缺少 $need（Windows 10 1803+ 自带）" }
    }
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
}

# ---------------------------------------------------------------- python
$script:PyCmd = $null
function Resolve-Python {
    if ($script:PyCmd) { return }
    if (Get-Command python -ErrorAction SilentlyContinue) { $script:PyCmd = @('python'); return }
    $bundled = Join-Path $GsvDir 'runtime\python.exe'
    if (Test-Path $bundled) { $script:PyCmd = @($bundled); return }
    if (Get-Command py -ErrorAction SilentlyContinue) { $script:PyCmd = @('py', '-3'); return }
    throw '需要 Python 3.11+（音色 zip 里是 GBK 文件名，只有 Python 能正确解压）'
}
function Invoke-Python([string]$Code, [string[]]$Arguments) {
    Resolve-Python
    $exe = $script:PyCmd[0]
    $pre = @()
    if ($script:PyCmd.Count -gt 1) { $pre = $script:PyCmd[1..($script:PyCmd.Count - 1)] }
    & $exe @pre @('-c', $Code) @Arguments
    if ($LASTEXITCODE -ne 0) { throw "python 执行失败，退出码 $LASTEXITCODE" }
}

# ---------------------------------------------------------------- download
function Download([string]$Url, [string]$Dest, [long]$Expect = 0) {
    if ($Expect -gt 0 -and (Test-Path $Dest) -and ((Get-Item $Dest).Length -eq $Expect)) {
        Ok "已存在且大小正确: $(Split-Path $Dest -Leaf)"
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest -Parent) | Out-Null
    Info "下载 $(Split-Path $Dest -Leaf)"
    & curl.exe -L -C - --retry 8 --retry-delay 5 --connect-timeout 30 -o $Dest $Url
    if ($LASTEXITCODE -ne 0) {
        Warn "curl 退出码 $LASTEXITCODE，再续传一次"
        & curl.exe -L -C - --retry 8 --retry-delay 5 -o $Dest $Url
    }
    if ($Expect -gt 0) {
        $len = (Get-Item $Dest).Length
        if ($len -ne $Expect) { throw "字节数不符: $len != $Expect。删除 $Dest 后重跑本脚本" }
        Ok "校验通过: $len 字节"
    }
}

# ---------------------------------------------------------------- GPT-SoVITS
function Install-Gsv {
    Step 'GPT-SoVITS 推理包（约 14 GB 解压 / 7.5 GB 下载）'
    if (Test-Path (Join-Path $GsvDir 'gsvi.bat')) { Ok '已安装，跳过'; return }

    if (-not (Test-Path $sevenZip)) {
        Info '下载 7zr.exe（解压工具）'
        & curl.exe -L --retry 3 -o $sevenZip 'https://www.7-zip.org/a/7zr.exe'
        if ($LASTEXITCODE -ne 0) { throw '7zr.exe 下载失败' }
    }

    $archive = Join-Path $TmpDir $GSV_FILE
    Download $GSV_URL $archive $GSV_BYTES

    Info '解压中（65088 个文件，约 5~10 分钟）'
    & $sevenZip x $archive "-o$Root\GSVI" -y -bsp1
    if ($LASTEXITCODE -ne 0) { throw "7zr 解压失败，退出码 $LASTEXITCODE" }

    $count = (Get-ChildItem (Join-Path $Root 'GSVI') -Recurse -File | Measure-Object).Count
    if ($count -lt 60000) { throw "解压后只有 $count 个文件，预期 65088 个，压缩包可能不完整" }
    Ok "解压完成: $count 个文件"
    Ok "安装包保留在 $archive（可删，省 7.5 GB）"
}

# ---------------------------------------------------------------- 音色
$GBK_EXTRACT = @'
import sys, zipfile
zipfile.ZipFile(sys.argv[1], metadata_encoding='gbk').extractall(sys.argv[2])
print('extracted')
'@

function Install-Voice([string]$RelPath) {
    $parts = $RelPath -split '/' | Where-Object { $_ }
    if ($parts.Count -lt 3) { throw "音色路径要写成 游戏/语言/角色：$RelPath" }

    $game = $parts[0]
    $lang = $parts[1]
    $file = $parts[-1]
    if (-not $file.ToLower().EndsWith('.zip')) { $file = "$file.zip" }
    $role = [IO.Path]::GetFileNameWithoutExtension($file)
    $target = Join-Path $V4Dir ('{0}-{1}-{2}' -f $game, $lang, $role)

    if (Test-Path $target) { Ok "已装: $game-$lang-$role"; return }

    $encoded = ($parts[0..($parts.Count - 2)] | ForEach-Object { [uri]::EscapeDataString($_) }) -join '/'
    $url = "https://www.modelscope.cn/models/$VOICE_REPO/resolve/master/$encoded/$([uri]::EscapeDataString($file))"

    $zip = Join-Path $TmpDir "dl_$role.zip"
    $stage = Join-Path $TmpDir "stage_$role"
    Download $url $zip

    Info "解压 $role（GBK 文件名）"
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    Invoke-Python $GBK_EXTRACT @($zip, $stage)

    $src = Get-ChildItem -Path $stage -Recurse -Directory |
        Where-Object { (Get-ChildItem $_.FullName -File -Filter '*.ckpt' -ErrorAction SilentlyContinue).Count -gt 0 } |
        Select-Object -First 1
    if (-not $src) { throw "$role 解压后没找到 .ckpt，压缩包结构不对" }

    $ckpt = (Get-ChildItem $src.FullName -File -Filter '*.ckpt' | Measure-Object).Count
    $pth = (Get-ChildItem $src.FullName -File -Filter '*.pth' | Measure-Object).Count
    if ($ckpt -lt 1 -or $pth -lt 1) { throw "$role 缺权重（ckpt=$ckpt pth=$pth）" }

    New-Item -ItemType Directory -Force -Path $V4Dir | Out-Null
    Move-Item -LiteralPath $src.FullName -Destination $target
    Remove-Item -LiteralPath $stage -Recurse -Force
    Remove-Item -LiteralPath $zip -Force
    Ok "装好: $game-$lang-$role"
}

# ---------------------------------------------------------------- AivisSpeech
function Install-Aivis {
    Step 'AivisSpeech（纯日语，可选）'
    if (Test-Path (Join-Path $aivisDir 'AivisSpeech.exe')) { Ok '已安装，跳过' }
    else {
        $zip = Join-Path $TmpDir 'AivisSpeech-Windows-x64-1.0.0.zip'
        Download $AIVIS_URL $zip
        Info '解压中'
        if (Test-Path $aivisDir) { Remove-Item $aivisDir -Recurse -Force }
        Expand-Archive -LiteralPath $zip -DestinationPath $aivisDir -Force
        $inner = Join-Path $aivisDir 'AivisSpeech'
        if (Test-Path $inner) {
            Get-ChildItem $inner | Move-Item -Destination $aivisDir -Force
            Remove-Item $inner -Recurse -Force
        }
        if (-not (Test-Path (Join-Path $aivisDir 'AivisSpeech.exe'))) { throw '解压后没找到 AivisSpeech.exe' }
        Ok '装好 AivisSpeech'
    }

    if ($WithAivisVoices) {
        New-Item -ItemType Directory -Force -Path $aivisModels | Out-Null
        foreach ($v in $AIVIS_VOICES) {
            $dest = Join-Path $aivisModels ($v.uuid + '.aivmx')
            if (Test-Path $dest) { Ok "声线已存在: $($v.name)"; continue }
            $url = "https://api.aivis-project.com/v1/aivm-models/$($v.uuid)/download?model_type=AIVMX"
            Download $url $dest
            Ok "声线: $($v.name)"
        }
    }
    else {
        Info '未下载声线（加 -WithAivisVoices 可自动下 2 个；也可用 3-打开音色库.bat 点选）'
    }
}

# ---------------------------------------------------------------- main
Write-Host ''
Write-Host '本地二次元 TTS 环境 · 一键安装' -ForegroundColor White
Write-Host "安装目录: $Root" -ForegroundColor Gray

Test-Environment

if (-not $SkipGsv) { Install-Gsv } else { Warn '按参数跳过 GPT-SoVITS' }

if (-not $SkipGsv -and -not $SkipVoices) {
    Step '音色（每个约 213 MB）'
    foreach ($v in $Voices) { Install-Voice $v }
}
elseif (-not $SkipVoices) { Warn '没有 GSVI 目录，跳过音色' }

if (-not $SkipAivis) { Install-Aivis } else { Warn '按参数跳过 AivisSpeech' }

Step '完成'
Write-Host '下一步：' -ForegroundColor White
Write-Host '  1) 双击 1-启动GPT-SoVITS配音.bat      -> http://127.0.0.1:8000' -ForegroundColor Gray
Write-Host '  2) 双击 3-打开音色库.bat              -> 配音台（端口 8899，被占用会自动换）' -ForegroundColor Gray
Write-Host '  3) 需要日语声线：双击 2-启动AivisSpeech日语配音.bat' -ForegroundColor Gray
Write-Host '  详细说明见 使用说明.md' -ForegroundColor Gray
Write-Host ''
