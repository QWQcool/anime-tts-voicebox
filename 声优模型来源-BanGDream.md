# BanG Dream! 声优模型 · 来源与获取指南

> 记录 MyGO!!!!! 与 Ave Mujica 这些音色的**原始出处**、下载方式、安装步骤，
> 方便任何人拿到这个仓库后，照着复现同样的音色库。
>
> 最后更新：2026-11-02

---

## 一、已装的音色一览

| 角色 | 乐队 | 音色目录（`models/v2/`） | 权重文件 | 参考音频 |
|---|---|---|---|---|
| 高松灯 | MyGO!!!!! | `MyGO-日语-高松灯` | `tomori1-e20.ckpt` / `tomori1_e12_s2664.pth` | 包内 13 条之一 |
| 千早爱音 | MyGO!!!!! | `MyGO-日语-千早爱音` | `anon1-e15.ckpt` / `anon1_e8_s2184.pth` | 包内 23 条之一 |
| 要乐奈 | MyGO!!!!! | `MyGO-日语-要乐奈` | `rana1-e20.ckpt` / `rana1_e12_s1176.pth` | 包内 5 条之一 |
| 椎名立希 | MyGO!!!!! | `MyGO-日语-椎名立希` | `riki1-e15.ckpt` / `riki1_e8_s3128.pth` | 包内 17 条之一 |
| 长崎素世 | MyGO!!!!! | `MyGO-日语-长崎素世` | `soyo1-e20.ckpt` / `soyo1_e12_s1428.pth` | 夹子音参考（9 条） |
| 长崎素世（另一版） | MyGO!!!!! | `MyGO-日语-长崎素世v0` | `soyo0-e20.ckpt` / `soyo0_e12_s1116.pth` | 正常参考（13 条） |
| 丰川祥子 | Ave Mujica | `AveMujica-日语-丰川祥子` | `sakiko1-e15.ckpt` / `sakiko1_e8_s560.pth` | 包内 156 条之一 |
| 若叶睦 | Ave Mujica | `AveMujica-日语-若叶睦` | `mu-e40.ckpt` / `mu_e12_s384.pth` | 演示视频提取（见 §2.2） |

**全部是 v2 世代的权重**，必须放在 `models/v2/` 下，放到 `models/v4/` 会加载失败。

---

## 二、素材从哪来

### 2.1 MyGO 五人 + 丰川祥子（同一个整合包）

| 项目 | 内容 |
|---|---|
| 作者 | B站 UP **Bjsjsk** |
| 视频 | [BV1XH4y137Lk](https://www.bilibili.com/video/BV1XH4y137Lk) 《MyGO角色GPT-SoVITS语音模型分享和使用教程》 |
| 主下载（Google Drive） | `https://drive.google.com/file/d/1bySYnuZjCgb_GWlWeSF6LenU0FrJKmGn/view` （2.66 GB，RAR5） |
| 百度网盘 | `https://pan.baidu.com/s/1R0TdgZpE4SkTq48mGM_-iQ` 提取码 `p6sg` |
| 备用百度 | `https://pan.baidu.com/s/1dHp9bFsCgkGZLfYOE88T0Q?pwd=0000` |

**包内结构**：

```
GPT_weights/          anon1-e15.ckpt  rana1-e20.ckpt  riki1-e15.ckpt
                      sakiko1-e15.ckpt  soyo0-e20.ckpt  soyo1-e20.ckpt  tomori1-e20.ckpt
SoVITS_weights/       与上面一一对应的 *.pth
参考音频/
  Anon干声素材/参考音频/      23 条，文件名就是日文台词
  Rana干声素材/参考音频/       5 条
  Taki干声素材/参考音频/      17 条（另有一条 100MB+ 的整段干声）
  Soyo干声素材/夹参考/         9 条（夹子音）
  Soyo干声素材/正常参考/      13 条（正常语调）
  Soyo干声素材/新建文件夹0/  271 条（完整训练集）
  Tomori干声素材/参考/        13 条
  sakiko/参考/               156 条
```

> **这个包最舒服的地方**：参考音频的文件名就是台词本身（例如
> `ああ、そういうパターンもあるんだ。あ、やば。.wav`），
> 不需要跑 ASR 打标，直接当 `prompt_text` 用，文本 100% 准确。

**下载注意**：
- Google Drive 直连在国内不通，需要代理；大文件会先跳"病毒扫描警告"页，
  要先从页面里抓出 `id / export / confirm / uuid` 四个参数再请求
  `drive.usercontent.google.com/download?...` 才能拿到真正的文件。
- 百度网盘必须登录才能下载（未登录只能用提取码验证，拿不到直链）。

### 2.2 若叶睦（独立包）

| 项目 | 内容 |
|---|---|
| 作者 | B站 UP **贤狼_Holo** |
| 发布视频 | [BV1X1wNeeE3F](https://www.bilibili.com/video/BV1X1wNeeE3F) 《若叶睦 GPT-Sovits模型发布》 |
| 使用示例 | [BV11mfGYvEyP](https://www.bilibili.com/video/BV11mfGYvEyP) 《【ai睦头】Ave Mujica 03》 |
| 下载 | `https://pan.baidu.com/s/1T3el07gpDoUbPWxt3Hkeng` 提取码 `xirj`（**在视频评论区置顶**，不在简介里） |

**包内只有权重，没有参考音频**：

```
GPT_weights_v2/mu-e40.ckpt
SoVITS_weights_v2/mu_e12_s384.pth
直接放进整合包的根目录就行了.txt   （空文件）
```

所以睦的参考音频是**自己从演示视频里提取的**，做法：

1. 下载发布视频 `BV1X1wNeeE3F`（267 秒，全程带 BGM）
2. `ffmpeg` 抽音轨 → 声道 1、32kHz 单声道
3. **UVR 人声分离**（包里自带）去掉 BGM：
   `tools/uvr5` 的 `AudioPre`，模型 `uvr5_weights/HP2_all_vocals.pth`
   （首次需要 `runtime\python.exe -m pip install resampy`，否则报 `No module named 'resampy'`）
4. 纯人声轨里搜「私はむつみです」，在 `214.0s ~ 218.2s` 处取 4.2 秒
5. Whisper 复核识别结果 = `私はむつみです`，作为参考文本

### 2.3 找到了但**不适用**的资源

| 资源 | 链接 | 为什么不能用 |
|---|---|---|
| 【SVC AI翻唱】若叶睦模型 | `pan.quark.cn/s/5bee6293bd4d`（BV1Yu9FBREXe） | SVC 是**歌声转换**，要有源唱段，不能念台词 |
| 【RVC若叶睦】模型 | `pan.baidu.com/s/1frxg69J0h9tRvQqaAxUV3A` 提取码 `r8aq`（BV1i2MC6uE9k） | RVC 是**变声**，需要输入音频去转换 |

判断方法：看文件名/说明里是 `GPT_weights` + `SoVITS_weights`（TTS，能直接文生音）
还是 `.pth` 单文件 + `index`（RVC/SVC，必须喂音频）。

---

## 三、安装步骤（三步）

### 1. 放权重

```
GSVI\GPT-SoVITS-1007-cu124\models\v2\<作品>-<语言>-<角色>\
├─ xxx.ckpt      （GPT 权重）
└─ xxx.pth       （SoVITS 权重）
```

目录名规则：`<作品>-<语言>-<角色>`，用 `-` 分三段以上，
面板会拆成"角色 · 作品 语言"显示，比如 `MyGO-日语-高松灯`。

### 2. 放参考音频

```
...\<角色目录>\reference_audios\<语言>\emotions\【默认】<参考文本>.wav
```

- 语言目录名要和权重语言一致（`日语` / `中文`）
- **文件名里的中括号部分 = 情感名，`【】` 之后的部分 = 参考文本**，程序靠它解析
- 参考文本必须与音频**逐字一致**，宁可短一点也不要写错

### 3. 刷新页面

不用重启服务，面板音色下拉会重新扫描（v2 音色后面带 `[v2]` 标记）。

### 现成脚本

| 脚本 | 用途 |
|---|---|
| `_install_mygo.py` | 批量装 MyGO 整合包（自动配对权重 + 挑 5~9 秒参考音频） |
| `_import_voice_pack.py` | 通用导入：给一个目录，自动找 ckpt+pth 和参考音频，用 Whisper 识别文本后建包 |

```bash
# 通用导入示例
GSVI\GPT-SoVITS-1007-cu124\runtime\python.exe _import_voice_pack.py "D:\下载\某个模型包" 前缀名
```

---

## 四、踩过的坑（重要）

1. **版本不能混**：2024 年前后的社区权重是 **v2**，放进 `models/v4` 会加载失败。
   用 `curl http://127.0.0.1:8000/version` 可以看到当前支持
   `["v2","v2Pro","v2ProPlus","v3","v4"]`。
2. **v2 对参考音频极度敏感**：同一份权重，换一句参考，输出的语调音高就跟着变。
   实测素世两版：参考 329.7Hz → 输出 330Hz；参考 235.1Hz → 输出 308Hz。
   所以"哪个权重更好"其实常常是"你贴的哪句参考"。
3. **参考文本错了会塌缩**：实测文本与音频对不上时，生成会提前收尾（只出 2 秒）。
4. **没有参考音频怎么办**：从演示视频取 → UVR 去 BGM → 静音检测切段 → Whisper 复核。
   完整流程见 §2.2。
5. **改完 `音色库/server.py` 必须重启**，而且要先杀掉旧进程，否则端口被占、
   新代码会起在 8900，你会以为改动没生效。

---

## 五、还缺谁

| 角色 | 乐队 | 状态 |
|---|---|---|
| 三角初华 | Ave Mujica | 未找到公开的 GPT-SoVITS 权重 |
| 八幡海铃 | Ave Mujica | 未找到 |
| 祐天寺若麦（喵梦） | Ave Mujica | 未找到 |

B站上这几个只有 RVC / SVC 版本，不是 TTS。如果你找到 GPT-SoVITS 权重，
按 §3 装或者直接用 `_import_voice_pack.py`。

---

## 六、版权说明

这些权重和音频都是**社区二创产物**，训练素材来自游戏/动画的干声。
- 自己本地玩、做二创视频：属于灰色地带
- 公开发布、商用、接单：**需要权利方授权**，否则有侵权风险
- 角色音色涉及声优的表演者权，标注来源不等于获得授权

本仓库只记录**来源与安装方法**，不附带任何权重文件。
