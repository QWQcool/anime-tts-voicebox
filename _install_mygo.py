"""把 MyGO / Ave Mujica 社区模型装成音色包（v2 世代权重）

参考音频文件名本身就是日文台词，直接当 prompt_text 用，不用跑 ASR。
每个角色挑一段 5~9 秒的参考音频。
"""
import os
import re
import shutil
import sys
import wave

ROOT = os.path.dirname(os.path.abspath(__file__))
GSVI = os.path.join(ROOT, "GSVI", "GPT-SoVITS-1007-cu124")
V2 = os.path.join(GSVI, "models", "v2")
# 解压目录：默认 <仓库>/download/mygo/extracted，可用第一个命令行参数覆盖
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "download", "mygo", "extracted")
REF = os.path.join(SRC, "参考音频")

# 角色名 -> (gpt权重前缀, sovits权重前缀, 参考音频目录)
CAST = [
    ("千早爱音", "anon1", "anon1", os.path.join(REF, "Anon干声素材", "参考音频")),
    ("要乐奈", "rana1", "rana1", os.path.join(REF, "Rana干声素材", "参考音频")),
    ("椎名立希", "riki1", "riki1", os.path.join(REF, "Taki干声素材", "参考音频")),
    ("高松灯", "tomori1", "tomori1", os.path.join(REF, "Tomori干声素材", "参考")),
    ("长崎素世", "soyo1", "soyo1", os.path.join(REF, "Soyo干声素材", "夹参考")),
    ("丰川祥子", "sakiko1", "sakiko1", os.path.join(REF, "sakiko", "参考")),
]


def dur(p):
    try:
        w = wave.open(p, "rb")
        d = w.getnframes() / w.getframerate()
        w.close()
        return d
    except Exception:  # noqa: BLE001
        return 0.0


def pick_ref(d):
    if not os.path.isdir(d):
        return None
    cands = [f for f in os.listdir(d) if f.lower().endswith(".wav")]
    scored = []
    for f in cands:
        p = os.path.join(d, f)
        x = dur(p)
        if 5.0 <= x <= 9.5:
            scored.append((abs(x - 7.0), p))
    if not scored:
        scored = [(abs(dur(os.path.join(d, f)) - 7.0), os.path.join(d, f))
                  for f in cands if dur(os.path.join(d, f)) >= 3.0]
    return sorted(scored)[0][1] if scored else None


def safe(text):
    return re.sub(r'[\\/:*?"<>|\r\n]+', "", text).strip()[:70]


def main():
    for role, gpt_pre, sov_pre, refdir in CAST:
        gpt = os.path.join(SRC, "GPT_weights", gpt_pre + "-e15.ckpt")
        if not os.path.isfile(gpt):
            gpt = os.path.join(SRC, "GPT_weights", gpt_pre + "-e20.ckpt")
        sov = [f for f in os.listdir(os.path.join(SRC, "SoVITS_weights")) if f.startswith(sov_pre)]
        if not os.path.isfile(gpt) or not sov:
            print(f"跳过 {role}: 缺权重")
            continue
        sovp = os.path.join(SRC, "SoVITS_weights", sov[0])
        ref = pick_ref(refdir)
        if not ref:
            print(f"跳过 {role}: 找不到 3~10s 参考音频")
            continue

        pack = os.path.join(V2, "MyGO-日语-" + role)
        emo = os.path.join(pack, "reference_audios", "日语", "emotions")
        os.makedirs(emo, exist_ok=True)
        for f in os.listdir(emo):
            os.remove(os.path.join(emo, f))

        shutil.copyfile(gpt, os.path.join(pack, os.path.basename(gpt)))
        shutil.copyfile(sovp, os.path.join(pack, os.path.basename(sovp)))
        text = safe(os.path.splitext(os.path.basename(ref))[0]) or "参考音频"
        shutil.copyfile(ref, os.path.join(emo, "【默认】%s.wav" % text))
        print(f"OK {role}: {os.path.basename(gpt)} + {sov[0]} | 参考 {dur(ref):.1f}s「{text[:34]}」")


if __name__ == "__main__":
    main()
