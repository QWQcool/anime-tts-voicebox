# 本地二次元 TTS 配音环境（一键复刻）

给视频配音用的**全本地**语音合成工作台：中文 / 日语动漫声线、逐句出片、剪映可直接用。

**一个命令装好，三个 bat 开始干活。** 模型权重不随仓库走，`setup.ps1` 会现下（约 22 GB）。

![配音台](音色库/shots/guide-dub.png)

---

## 它由四块组成

| 组件 | 来源 | 装到哪 | 作用 |
|---|---|---|---|
| **配音台 / 音色库**（本仓库代码） | 本仓库 | `音色库\` | 网页端：写台词 → 出 wav；搜角色 → 一键装；双引擎切换 |
| **GPT-SoVITS 推理包** | ModelScope（AI-Hobbyist） | `GSVI\` | 本地推理主力：中文 + 日语 + 跨语言，自带 Python/PyTorch/CUDA 运行时 |
| **角色音色** | ModelScope | `GSVI\...\models\v4\` | 每个角色一个文件夹（`.ckpt` + `.pth` + 参考音频） |
| **AivisSpeech**（可选） | GitHub Releases | `AivisSpeech\` | 纯日语声线，VOICEVOX 兼容 API，带情绪风格 |

另有一个**可选**的云端引擎：小米 MiMo TTS（`mimo-v2.5-tts`）。默认关，需要自己的 API Key，且**台词会上传到小米服务器**——介意隐私就别开。

---

## 机器要求

| 项 | 要求 | 说明 |
|---|---|---|
| 系统 | Windows 10/11 64 位 | CUDA 运行时已打包，不用装 Python / PyTorch |
| 显卡 | NVIDIA，驱动 **≥ 551**（CUDA 12.4） | 50 系需换 `GPT-SoVITS-1007-cu128.7z` |
| 显存 | ≥ 6 GB | 实测 RTX 3080 10GB，两个服务同开占 6.7 GB |
| 磁盘 | **≥ 30 GB**，路径不要带空格 | 解压 14 GB + 安装包 7.5 GB + 音色 + AivisSpeech |
| 网络 | 首次安装需要 | `modelscope.cn`（直连可用）、`github.com`、`hf-mirror.com` |

---

## 三步装好

```powershell
git clone https://github.com/QWQcool/anime-tts-voicebox.git D:\TTS
cd D:\TTS
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

脚本按顺序做这些事，**可重复运行**（已装的自动跳过）：

1. 查显卡/驱动/剩余空间
2. 下 `7zr.exe`（只有 600 KB）
3. 下 `GPT-SoVITS-1007-cu124.7z`（7.5 GB，断点续传）→ **校验字节数必须等于 7,844,088,481**
4. 解压到 `GSVI\`（65088 个文件，5~10 分钟）
5. 下两个爱丽丝音色（中文 + 日语，各 213 MB）→ GBK 解压 → 重命名成 `蔚蓝档案-中文-爱丽丝`
6. 下 AivisSpeech 1.0.0（370 MB）→ 解压

常用参数：

```powershell
.\setup.ps1 -SkipAivis                          # 不要日语引擎
.\setup.ps1 -WithAivisVoices                    # 顺手装 2 个 AivisHub 声线（+480 MB）
.\setup.ps1 -Voices '蔚蓝档案/中文/白子','蔚蓝档案/中文/爱丽丝'
```

耗时参考（100 Mbps 家宽）：下载 ≈ 12 分钟，解压 ≈ 8 分钟，音色 ≈ 2 分钟。

---

## 装完怎么用

| 双击 | 干什么 | 地址 |
|---|---|---|
| `1-启动GPT-SoVITS配音.bat` | 本地推理服务 + 网页 | <http://127.0.0.1:8000> |
| `3-打开音色库.bat` | **配音台**（写台词出音频）+ 音色搜索安装 | <http://127.0.0.1:8899> |
| `2-启动AivisSpeech日语配音.bat` | 日语引擎 + 编辑器 | 编辑器自动拉起 :10101 |

配音台里**一段一行**，每行出一个 wav，落在 `音色库\out\`，显示时长 / 峰值电平 / 生成耗时。
峰值低于 -25 dB 会标“偏静”——基本是文本语言选错了，别当成功。

> 端口 8899 如果被别的程序占用，工具会自动换 8900~8910，**实际地址看黑窗口第一行**。

---

## 仓库里有什么 / 没有什么

```
.
├─ setup.ps1                 一键安装
├─ 使用说明.md               完整手册（语言参数、坑点、授权边界、验收数据）
├─ 1-启动GPT-SoVITS配音.bat
├─ 2-启动AivisSpeech日语配音.bat
├─ 3-打开音色库.bat
└─ 音色库/                   配音台本体（纯标准库 Python + 原生 JS，无 npm 依赖）
   ├─ server.py              静态服务 + 代理 ModelScope/AivisHub + 调 GSVI/MiMo
   ├─ index.html / style.css / app.js
   ├─ shots/                 文档截图
   └─ out/                   生成音频（不入库）
```

**不入库**（见 `.gitignore`）：`GSVI/`、`AivisSpeech/`、`_packages/`、`*.7z`、`*.zip`、`*.wav`、`音色库/out/`、`7zr.exe`。

**没有密钥**：云端 MiMo 的 Key 只从环境变量读（`MiMo_API_Key`，找不到时回退读注册表用户变量），仓库里是空。

---

## 授权边界（别踩）

| 对象 | 授权 | 商用 |
|---|---|---|
| GPT-SoVITS 代码 | MIT | ✅ |
| AivisSpeech / AivisHub 声线 | ACML 1.0 | ✅（`ACML-NC` ❌） |
| AI-Hobbyist 角色模型（如蔚蓝档案-爱丽丝） | **CC-BY-NC** | ❌ 仅个人学习与二次创作 |
| 声优 / 动漫角色本人的声音 | 人格权 / 肖像权 | ❌ 与模型许可证无关 |

**模型许可证 ≠ 音色许可证。** 上架带广告分成的视频，请换 ACML 声线并保留署名。

---

## 给 AI 的任务提示词

把下面整段粘给新电脑上的 AI 助手（Claude / Codex / CodeBuddy 等），它就能自己装完并验证。**只需把第一行的路径换成目标目录**。

```text
任务：在这台 Windows 机器上部署"本地二次元 TTS 配音环境"，并验证可用。

目标目录：D:\TTS（不要用带空格的路径；如果 D 盘空间不足，换其它盘的同名目录，
         后面的路径全部跟着换）

第 1 步 环境探测（先别动手，把结果报给我）
  - nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
    驱动 < 551 就停下告诉我；没有 NVIDIA 显卡直接停
  - 目标盘剩余空间，需要 ≥ 30 GB
  - curl.exe --version（Win10 1803+ 自带）

第 2 步 拉代码并跑安装脚本
  git clone https://github.com/QWQcool/anime-tts-voicebox.git D:\TTS
  cd /d D:\TTS
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  说明：脚本会下 7.5 GB 安装包（校验 7,844,088,481 字节）、解压 65088 个文件、
  装两个中/日音色、装 AivisSpeech。可重复运行，已装的会跳过。
  如果 7z 解压报错，先确认安装包字节数，不一致就删掉重下（脚本支持断点续传）。

第 3 步 启动并验收（不要只看接口 200，要真出音频）
  a) 双击/运行 1-启动GPT-SoVITS配音.bat，等 60~120 秒
     curl http://127.0.0.1:8000/models/v4
     应返回 蔚蓝档案-中文-爱丽丝 与 蔚蓝档案-日语-爱丽丝（各带 ["默认"] 情感）
  b) 实跑合成（首次会慢，含模型预热）：
     POST http://127.0.0.1:8000/infer_single
     {"version":"v4","model_name":"蔚蓝档案-中文-爱丽丝","prompt_text_lang":"中文",
      "emotion":"默认","text":"老师，今天也一起加油吧！","text_lang":"中文"}
     返回 {"msg":"合成成功","audio_url":"http://0.0.0.0:8000/outputs/xxx.wav"}
     （audio_url 里的 0.0.0.0 要换成 127.0.0.1 才能下）
  c) 用 ffprobe 查时长 > 2 秒；用 ffmpeg -af volumedetect 查峰值，
     正常在 -10 dB ~ -1 dB；低于 -40 dB 说明没出人声，别当通过
  d) 运行 3-打开音色库.bat，打开 http://127.0.0.1:8899
     （8899 被占用会自动换 8900+，看启动行打印的实际地址）
     在配音台选音色、填一句台词、点"开始配音"，应出现可播放的 wav 卡片，
     卡片上带时长和峰值；同时确认 音色库\out\ 里有对应文件

第 4 步 汇报
  显卡型号 / 驱动版本 / 安装路径 / 实际占用 / 每步验收结果（含音频时长与峰值 dB）/
  遇到的坑。不要隐瞒失败项。

硬性约束：
  - 语言参数的合法值只有：中文 英语 日语 粤语 韩语 中英混合 日英混合 粤英混合
    韩英混合 多语种混合。写"日文"会直接报参数错误。
  - 音色目录命名必须是 <游戏>-<语言>-<角色名>，否则扫不到。
  - 不要用 & 或 nohup 挂后台跑服务，用 bat 双击或 Start-Process。
  - 云端 MiMo 引擎是可选项：需要环境变量 MiMo_API_Key，且台词会上传到小米服务器，
    未经我同意不要开启。
  - 不要为了"跑通"去改 language 参数或伪造音频，失败就如实报。
```

---

## 常见问题

**Q：网页让我上传参考音频？**
你点到了 GSVI 的「经典模式」。回 <http://127.0.0.1:8000/>（情感模式），参考音频音色包里带了，不用传。

**Q：装完音色扫不到？**
目录名必须是 `游戏-语言-角色名`，里面要有 `.ckpt` + `.pth` + `reference_audios\<语言>\emotions\*.wav`。

**Q：中文音色说日语 / 日语音色说中文？**
跨语言可以：`text_lang` 改成目标语言即可（实测日语音色说中文正常）。

**Q：AivisSpeech 引擎起不来？**
它首次要下 1.3 GB BERT，直连 huggingface.co 会超时。必须带 `HF_ENDPOINT=https://hf-mirror.com`（两个 bat 已内置）。

**Q：能商用吗？**
看音色授权，不看代码授权。见上面「授权边界」。

更细的说明（参数表、9 条坑、验收记录）在 [使用说明.md](使用说明.md)。

---

## English quick start

Local anime-style TTS for video dubbing: GPT-SoVITS (zh/ja) + AivisSpeech (ja) + a web dubbing console.
Fully offline inference; models are downloaded on install, never committed.

```powershell
git clone https://github.com/QWQcool/anime-tts-voicebox.git D:\TTS
cd D:\TTS
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Then run `1-启动GPT-SoVITS配音.bat` (API on :8000) and `3-打开音色库.bat` (console on :8899).
Requires an NVIDIA GPU with driver ≥ 551, ~30 GB free, Windows 10/11.
Character models are **CC-BY-NC** — personal / derivative use only.
