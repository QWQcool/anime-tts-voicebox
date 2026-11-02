"""给配音加电音质感（ffmpeg 滤镜链，可批量出多档）

用法：
  python _fx_electronic.py <输入.wav> [输出目录] [档位...]

档位（不写则全部生成）：
  A   轻电音：升半音 + 合唱叠层 + 微延迟 + 提亮
  B   硬电音：升 1 半音 + 强合唱 + 位深压缩
  B0  硬电音·不移调（推荐，实测声纹相似度最高）
  D   强电音：更重压缩 + 更亮
  C   机器人：环形调制（实测最差，仅作对比）

例：
  python _fx_electronic.py samples\\某条.wav
  python _fx_electronic.py in.wav out B0 D
"""
import os
import subprocess
import sys

CHAINS = {
    "A_轻电音": (
        "rubberband=pitch=1.0:formant=preserved,"
        "chorus=0.7:0.9:45|60:0.35|0.28:0.28|0.22:1.8|1.2,"
        "aecho=0.75:0.85:35:0.22,"
        "highshelf=f=6000:g=2.5,volume=1.6"
    ),
    "B_硬电音": (
        "rubberband=pitch=1.0:formant=preserved,"
        "chorus=0.8:0.95:40|55|70:0.45|0.35|0.28:0.35|0.28|0.2:2.2|1.6|1.1,"
        "acrusher=bits=10:mix=0.35:mode=log,"
        "equalizer=f=2500:t=q:w=1.2:g=3,volume=1.5"
    ),
    "B0_硬电音不移调": (
        "chorus=0.8:0.95:40|55|70:0.45|0.35|0.28:0.35|0.28|0.2:2.2|1.6|1.1,"
        "acrusher=bits=10:mix=0.35:mode=log,"
        "equalizer=f=2500:t=q:w=1.2:g=3,volume=1.5"
    ),
    "D_强电音": (
        "rubberband=pitch=1.0:formant=preserved,"
        "chorus=0.85:0.95:38|52|68:0.5|0.4|0.3:0.4|0.3|0.22:2.4|1.7|1.2,"
        "acrusher=bits=8:mix=0.3:mode=log,"
        "equalizer=f=3200:t=q:w=1.4:g=4.5,highshelf=f=5500:g=4,"
        "aecho=0.7:0.8:30:0.18,volume=1.4"
    ),
    "C_机器人": (
        "aeval=exprs='0.78*val(0)+0.3*val(0)*sin(2*PI*t*55)',"
        "chorus=0.6:0.85:50:0.3:0.9:1.5,highpass=f=90,volume=1.5"
    ),
}


def run(src, dst, chain, sr=44100):
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src, "-af", chain,
           "-ar", str(sr), "-ac", "1", "-c:a", "pcm_s16le", dst]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        print("  失败:", (p.stderr or "").strip()[:200])
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = os.path.abspath(sys.argv[1])
    if not os.path.isfile(src):
        print("找不到输入文件:", src)
        return 2

    rest = sys.argv[2:]
    out_dir = os.path.dirname(src)
    picks = []
    for a in rest:
        if os.path.isdir(a) or (os.sep in a or "/" in a):
            out_dir = os.path.abspath(a)
        else:
            picks.append(a.upper())

    keys = [k for k in CHAINS if not picks or k.split("_")[0] in picks]
    if not keys:
        keys = list(CHAINS)

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    print("源:", os.path.basename(src))
    for k in keys:
        dst = os.path.join(out_dir, "%s_%s.wav" % (stem, k.split("_")[0]))
        if run(src, dst, CHAINS[k]):
            print("  OK", k, "->", os.path.basename(dst))
    return 0


if __name__ == "__main__":
    sys.exit(main())
