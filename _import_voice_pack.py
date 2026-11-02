"""把社区下载的 GPT-SoVITS 模型包自动装成音色包

用法：
  runtime\\python.exe _import_voice_pack.py <解压后的目录> [标签前缀] [版本]
  版本默认 v2（社区权重多是 v2），可选 v4 / v3 / v2Pro / v2ProPlus

行为：
  1. 递归找出「同一目录下同时有 .ckpt 和 .pth」的文件夹
  2. 在同目录/上级找一段参考音频（wav/mp3/m4a/flac）
  3. 用 Whisper 识别参考音频的语言与文本
  4. 在 models/<版本>/<前缀>-<语言>-<文件夹名>/ 建包（权重 + 参考音频，文件名带识别文本）
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GSVI = os.path.join(ROOT, "GSVI", "GPT-SoVITS-1007-cu124")
VERSION = sys.argv[3] if len(sys.argv) > 3 else "v2"
V4 = os.path.join(GSVI, "models", VERSION)
ASR_CACHE = os.path.join(ROOT, "models_asr")
AUDIO_EXT = (".wav", ".mp3", ".m4a", ".flac", ".ogg")
LANG_MAP = {"zh": "中文", "ja": "日语", "en": "英语", "ko": "韩语", "yue": "粤语"}


def find_models(root):
    hits = []
    for dirpath, _, files in os.walk(root):
        ck = [f for f in files if f.lower().endswith(".ckpt")]
        pt = [f for f in files if f.lower().endswith(".pth")]
        if ck and pt:
            hits.append((dirpath, ck, pt))
    return hits


def find_audio(dirpath, max_hops=2):
    d = dirpath
    for _ in range(max_hops + 1):
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(AUDIO_EXT) and os.path.getsize(os.path.join(d, f)) > 4096:
                return os.path.join(d, f)
        parent = os.path.dirname(d)
        if parent == d or os.path.abspath(parent) < os.path.abspath(dirpath):
            break
        d = parent
    # 递归兜底
    for dirpath2, _, files in os.walk(dirpath):
        for f in files:
            if f.lower().endswith(AUDIO_EXT) and os.path.getsize(os.path.join(dirpath2, f)) > 4096:
                return os.path.join(dirpath2, f)
    return None


def asr(path):
    code = (
        "import sys,os,json\n"
        "os.environ.setdefault('HF_ENDPOINT','https://hf-mirror.com')\n"
        "from faster_whisper import WhisperModel\n"
        "m=WhisperModel('small',device='cpu',compute_type='int8',download_root=r'%s')\n"
        "segs,info=m.transcribe(sys.argv[1],language=None,beam_size=5,vad_filter=True)\n"
        "print(json.dumps({'lang':info.language,'text':''.join(s.text for s in segs).strip()},ensure_ascii=False))\n"
    ) % ASR_CACHE
    p = subprocess.run([os.path.join(GSVI, "runtime", "python.exe"), "-c", code, path],
                       capture_output=True, text=True, timeout=600, errors="replace")
    import json
    for line in reversed(p.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except Exception:  # noqa: BLE001
            continue
    return {"lang": "zh", "text": ""}


def main():
    if len(sys.argv) < 2:
        print("用法: _import_voice_pack.py <目录> [前缀]")
        return 1
    src, prefix = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "导入")
    hits = find_models(src)
    print(f"发现 {len(hits)} 组模型（ckpt+pth）")
    for dirpath, cks, pts in hits:
        role = os.path.basename(dirpath.rstrip("\\/")) or "未命名"
        audio = find_audio(dirpath)
        if not audio:
            print(f"  跳过 {role}: 找不到参考音频")
            continue
        info = asr(audio)
        lang = LANG_MAP.get(info["lang"], "日语")
        text = (info["text"] or "").strip() or "参考音频"
        text = "".join(ch for ch in text if ch not in '\\/:*?"<>|')[:60]

        pack = os.path.join(V4, f"{prefix}-{lang}-{role}")
        emo = os.path.join(pack, "reference_audios", lang, "emotions")
        os.makedirs(emo, exist_ok=True)
        for f in os.listdir(emo):
            os.remove(os.path.join(emo, f))

        # 取最大的 ckpt / pth（通常是最终权重）
        ck = max(cks, key=lambda f: os.path.getsize(os.path.join(dirpath, f)))
        pt = max(pts, key=lambda f: os.path.getsize(os.path.join(dirpath, f)))
        shutil.copyfile(os.path.join(dirpath, ck), os.path.join(pack, ck))
        shutil.copyfile(os.path.join(dirpath, pt), os.path.join(pack, pt))
        shutil.copyfile(audio, os.path.join(emo, "【默认】%s.wav" % text))
        print(f"  OK {pack}")
        print(f"     权重 {ck} + {pt} | 参考 {os.path.basename(audio)} -> {lang}「{text[:30]}」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
