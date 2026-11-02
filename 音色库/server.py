"""本地音色库浏览 / 安装服务（仅监听 127.0.0.1，标准库实现，无第三方依赖）

职责：
  1) 代理 ModelScope 目录列举与 AivisHub 检索（两者浏览器直连都会被 CORS 拦）
  2) 把选中的角色 zip 下载、按 GBK 解压、重命名成 <游戏>-<语言>-<角色> 放进 models/v4
  3) 把 AivisHub 的 .aivmx 下到 %APPDATA%\\AivisSpeech-Engine\\Models
"""

import array
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import wave
import webbrowser
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL_ROOT = os.path.dirname(HERE)                      # D:\TTS
GSVI_DIR = os.path.join(INSTALL_ROOT, 'GSVI', 'GPT-SoVITS-1007-cu124')
V4_DIR = os.path.join(GSVI_DIR, 'models', 'v4')
# 音色可能分散在不同世代目录：官方合集是 v4，社区模型多为 v2
MODELS_ROOT = os.path.join(GSVI_DIR, 'models')
VERSION_DIRS = [(v, os.path.join(MODELS_ROOT, v))
                for v in ('v4', 'v3', 'v2', 'v2Pro', 'v2ProPlus')]
TMP_DIR = os.path.join(INSTALL_ROOT, '_packages')
AIVIS_MODELS = os.path.join(os.environ['APPDATA'], 'AivisSpeech-Engine', 'Models')

MS_REPO = 'aihobbyist/GPT-SoVITS_Model_Collection'
MS_LIST = 'https://www.modelscope.cn/api/v1/models/%s/repo/files' % MS_REPO
MS_RESOLVE = 'https://www.modelscope.cn/models/%s/resolve/master/' % MS_REPO
MS_FILE_VIEW = 'https://www.modelscope.cn/models/%s/file/view/master/%%s' % MS_REPO
MS_REPO_URL = 'https://www.modelscope.cn/models/%s/files' % MS_REPO
AIVIS_API = 'https://api.aivis-project.com/v1/aivm-models'
AIVIS_HUB = 'https://hub.aivis-project.com/aivm-models/%s'
AIVIS_HUB_URL = 'https://hub.aivis-project.com/'

GSVI_INFER = 'http://127.0.0.1:8000/infer_single'
OUT_DIR = os.path.join(HERE, 'out')          # 生成的配音落这里，随页面一起可播放/下载
TEXT_LANGS = ['中文', '英语', '日语', '粤语', '韩语', '中英混合', '日英混合', '粤英混合', '韩英混合', '多语种混合']

# ---- 参考人声克隆：上传 3~10 秒音频 + 对应文本 → 用这个音色念新台词（零样本，不训练）
GSVI_CLASSIC = 'http://127.0.0.1:8000/infer_classic'
GSVI_MODELS = 'http://127.0.0.1:8000/classic_model_list/v4'
CLONE_DIR = os.path.join(GSVI_DIR, 'custom_refs')      # 参考音频落地目录（与网页上传一致）
RUNTIME_PY = os.path.join(GSVI_DIR, 'runtime', 'python.exe')
ASR_CACHE = os.path.join(INSTALL_ROOT, 'models_asr')   # Whisper 权重缓存
REF_MIN, REF_MAX = 3.0, 10.0                           # GSVI 对参考音频的硬性要求
FFMPEG = os.environ.get('FFMPEG') or shutil.which('ffmpeg') or 'ffmpeg'

# ---- 云端可选引擎：小米 MiMo TTS（OpenAI 兼容；文本会上传到小米服务器）
MIMO_URL = 'https://api.xiaomimimo.com/v1/chat/completions'
MIMO_MODEL = 'mimo-v2.5-tts'
MIMO_VOICES = [
    {'id': '冰糖', 'label': '冰糖 · 中文女声（甜美）'},
    {'id': '茉莉', 'label': '茉莉 · 中文女声（温柔）'},
    {'id': '苏打', 'label': '苏打 · 中文男声（清爽）'},
    {'id': '白桦', 'label': '白桦 · 中文男声（沉稳）'},
    {'id': 'mimo_default', 'label': 'MiMo-默认（中国集群=冰糖）'},
    {'id': 'Mia', 'label': 'Mia · 英文女声'},
    {'id': 'Chloe', 'label': 'Chloe · 英文女声'},
    {'id': 'Milo', 'label': 'Milo · 英文男声'},
    {'id': 'Dean', 'label': 'Dean · 英文男声'},
]

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
JOBS = {}
LOCK = threading.Lock()
PORT = 8899


# ---------------------------------------------------------------- helpers
def http_json(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\r\n]+', '_', s).strip() or 'x'


def job_new(kind, title):
    jid = uuid.uuid4().hex[:12]
    with LOCK:
        JOBS[jid] = {'id': jid, 'kind': kind, 'title': title, 'state': 'running',
                     'phase': '排队中', 'bytes': 0, 'result': None, 'error': None,
                     'started': time.time()}
    return jid


def job_set(jid, **kw):
    with LOCK:
        if jid in JOBS:
            JOBS[jid].update(kw)


def download(url, dest, jid=None):
    """流式下载；ModelScope 返回 chunked 无 Content-Length，进度只能报已下字节"""
    req = urllib.request.Request(url, headers=UA)
    got = 0
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, 'wb') as f:
        total = r.headers.get('Content-Length')
        total = int(total) if total else 0
        while True:
            chunk = r.read(262144)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if jid:
                job_set(jid, bytes=got, total=total)
    return got


# ---------------------------------------------------------------- 安装：GPT-SoVITS
def do_ms_install(jid, rel_path):
    """rel_path 形如 蔚蓝档案/中文/白子.zip"""
    try:
        parts = [p for p in rel_path.split('/') if p]
        if len(parts) < 3:
            raise RuntimeError('路径不完整，需要 游戏/语言/角色.zip')
        game, lang, fname = parts[0], parts[1], parts[-1]
        role = fname[:-4] if fname.lower().endswith('.zip') else fname
        target = os.path.join(V4_DIR, '%s-%s-%s' % (game, lang, role))

        if os.path.isdir(target):
            job_set(jid, state='exists', phase='已存在，跳过',
                    result={'path': target, 'note': '同目录名已存在，未覆盖'})
            return

        os.makedirs(TMP_DIR, exist_ok=True)
        os.makedirs(V4_DIR, exist_ok=True)
        zip_path = os.path.join(TMP_DIR, 'dl_%s.zip' % safe_name(role))

        job_set(jid, phase='下载中')
        url = MS_RESOLVE + urllib.parse.quote(rel_path)
        n = download(url, zip_path, jid)
        if n < 1024 * 1024:
            raise RuntimeError('下载体积异常（%d 字节），可能不是压缩包' % n)

        job_set(jid, phase='解压中')
        stage = os.path.join(TMP_DIR, 'stage_%s' % safe_name(role))
        shutil.rmtree(stage, ignore_errors=True)
        with zipfile.ZipFile(zip_path, metadata_encoding='gbk') as zf:
            names = zf.namelist()
            zf.extractall(stage)

        # zip 内通常是 v4/<角色>/...，也可能是 <角色>/...
        src = None
        for root, dirs, files in os.walk(stage):
            if any(f.endswith(('.ckpt', '.pth')) for f in files):
                src = root
                if root.count(os.sep) > stage.count(os.sep):
                    break
        if not src:
            raise RuntimeError('解压后没找到 .ckpt/.pth，压缩包结构不符合预期')

        ckpt = [f for f in os.listdir(src) if f.endswith('.ckpt')]
        pth = [f for f in os.listdir(src) if f.endswith('.pth')]
        if not ckpt or not pth:
            raise RuntimeError('缺少权重文件（ckpt:%d / pth:%d）' % (len(ckpt), len(pth)))

        ref = os.path.join(src, 'reference_audios')
        ref_langs = sorted(os.listdir(ref)) if os.path.isdir(ref) else []

        job_set(jid, phase='落位中')
        shutil.move(src, target)

        for p in (zip_path, stage):
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)

        job_set(jid, state='done', phase='完成',
                result={'path': target, 'name': '%s-%s-%s' % (game, lang, role),
                        'ckpt': ckpt[0], 'pth': pth[0], 'refLangs': ref_langs,
                        'size': n,
                        'warning': None if lang in ref_langs else
                        '注意：参考音频语言是 %s，与你选择的 %s 不一致，可能扫不到' % ('/'.join(ref_langs) or '无', lang)})
    except Exception as e:  # noqa: BLE001
        job_set(jid, state='error', phase='失败', error=str(e))


# ---------------------------------------------------------------- 安装：AivisSpeech
def do_aivis_install(jid, model_uuid, name):
    try:
        os.makedirs(AIVIS_MODELS, exist_ok=True)
        dest = os.path.join(AIVIS_MODELS, '%s.aivmx' % model_uuid)
        if os.path.isfile(dest) and os.path.getsize(dest) > 1024 * 1024:
            job_set(jid, state='exists', phase='已存在，跳过',
                    result={'path': dest, 'note': '这个 .aivmx 已经在 Models 里'})
            return
        job_set(jid, phase='下载中')
        url = '%s/%s/download?model_type=AIVMX' % (AIVIS_API, model_uuid)
        n = download(url, dest + '.part', jid)
        if n < 1024 * 1024:
            os.remove(dest + '.part')
            raise RuntimeError('下载体积异常（%d 字节）' % n)
        os.replace(dest + '.part', dest)
        job_set(jid, state='done', phase='完成',
                result={'path': dest, 'name': name, 'size': n,
                        'note': '重启 AivisSpeech 引擎后新声线才会出现在 /speakers'})
    except Exception as e:  # noqa: BLE001
        job_set(jid, state='error', phase='失败', error=str(e))


# ---------------------------------------------------------------- 查询
def ms_list(path):
    q = urllib.parse.urlencode({'Revision': 'master', 'Recursive': 'false', 'Root': path})
    d = http_json(MS_LIST + '?' + q)
    files = ((d.get('Data') or {}).get('Files') or [])
    dirs = [{'name': f['Name'], 'path': f['Path']} for f in files if f.get('Type') == 'tree']
    blobs = [{'name': f['Name'], 'path': f['Path'], 'size': f.get('Size', 0),
              'url': MS_FILE_VIEW % urllib.parse.quote(f['Path'], safe='')}
             for f in files if f.get('Type') == 'blob' and f['Name'].lower().endswith('.zip')]
    dirs.sort(key=lambda x: x['name'])
    blobs.sort(key=lambda x: x['name'])
    return {'root': path, 'dirs': dirs, 'files': blobs, 'total': len(files),
            'repoUrl': MS_REPO_URL}


def aivis_search(page, limit=30):
    d = http_json('%s/search?limit=%d&page=%d' % (AIVIS_API, limit, page))
    out = []
    for m in d.get('aivm_models', []):
        mf = (m.get('model_files') or [{}])[0]
        out.append({
            'uuid': m.get('aivm_model_uuid'),
            'url': AIVIS_HUB % m.get('aivm_model_uuid'),
            'name': m.get('name'),
            'downloads': m.get('total_download_count', 0),
            'license': mf.get('license_type'),
            'timbre': m.get('voice_timbre'),
            'category': m.get('category'),
            'speaker': m.get('user', {}).get('name'),
            'description': (m.get('description') or '').strip(),
            'installed': os.path.isfile(os.path.join(AIVIS_MODELS, '%s.aivmx' % m.get('aivm_model_uuid'))),
        })
    out.sort(key=lambda x: x['downloads'], reverse=True)
    return {'page': page, 'total': d.get('total', 0), 'models': out, 'hubUrl': AIVIS_HUB_URL}


def installed():
    ms = []
    if os.path.isdir(V4_DIR):
        for name in sorted(os.listdir(V4_DIR)):
            p = os.path.join(V4_DIR, name)
            if not os.path.isdir(p):
                continue
            files = os.listdir(p)
            ref = os.path.join(p, 'reference_audios')
            langs = sorted(os.listdir(ref)) if os.path.isdir(ref) else []
            emo = {}
            for lg in langs:
                ed = os.path.join(ref, lg, 'emotions')
                emo[lg] = sorted(os.listdir(ed)) if os.path.isdir(ed) else []
            ms.append({'dir': name, 'hasCkpt': any(f.endswith('.ckpt') for f in files),
                       'hasPth': any(f.endswith('.pth') for f in files), 'langs': langs,
                       'emotions': emo, 'path': p})
    av = []
    if os.path.isdir(AIVIS_MODELS):
        for f in sorted(os.listdir(AIVIS_MODELS)):
            if f.endswith('.aivmx'):
                av.append({'file': f, 'uuid': f[:-6],
                           'size': os.path.getsize(os.path.join(AIVIS_MODELS, f))})
    return {'gptSovits': ms, 'aivis': av, 'v4Dir': V4_DIR, 'aivisDir': AIVIS_MODELS}


# ---------------------------------------------------------------- 配音（文本 → 音频）
def voices():
    """扫描 models/<版本>，拆出 游戏-语言-角色 + 该音色自带的参考语言与情感

    不同世代的权重必须用对应版本目录（社区模型多为 v2，官方合集是 v4），
    所以每个音色带一个 version 字段，合成时回传给 GSVI。
    """
    out = []
    for ver, root in VERSION_DIRS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if not os.path.isdir(p):
                continue
            parts = name.split('-')
            game = parts[0] if len(parts) > 2 else ''
            lang = parts[1] if len(parts) > 2 else ''
            role = '-'.join(parts[2:]) if len(parts) > 2 else name
            ref = os.path.join(p, 'reference_audios')
            emotions = {}
            if os.path.isdir(ref):
                for lg in sorted(os.listdir(ref)):
                    ed = os.path.join(ref, lg, 'emotions')
                    emos = []
                    if os.path.isdir(ed):
                        for f in sorted(os.listdir(ed)):
                            m = re.match(r'【(.+?)】', f)
                            if f.lower().endswith('.wav') and m:
                                emos.append(m.group(1))
                    emotions[lg] = emos
            out.append({'voice': name, 'game': game, 'lang': lang, 'role': role,
                        'version': ver,
                        'refLangs': list(emotions.keys()), 'emotions': emotions,
                        'hasWeights': any(f.endswith('.ckpt') for f in os.listdir(p))
                        and any(f.endswith('.pth') for f in os.listdir(p))})
    return out


def voice_version(name):
    """按目录归属判断这个音色属于哪个版本（v4 优先）"""
    for ver, root in VERSION_DIRS:
        if name and os.path.isdir(os.path.join(root, name)):
            return ver
    return 'v4'


def wav_stats(path):
    """时长 + 峰值电平（dBFS）。峰值太低说明没出人声，别当成功。"""
    try:
        with wave.open(path, 'rb') as w:
            n, fr, sw = w.getnframes(), w.getframerate(), w.getsampwidth()
            frames = w.readframes(n)
            ch = w.getnchannels()
        dur = n / float(fr) if fr else 0.0
        peak, full = 0, 1.0
        if sw == 2:
            a = array.array('h')
            a.frombytes(frames[:len(frames) // 2 * 2])
            peak, full = (max(max(a), -min(a)) if a else 0), 32768.0
        elif sw == 1:
            a = array.array('b')
            a.frombytes(frames)
            peak, full = (max(max(a), -min(a)) if a else 0), 128.0
        db = 20 * math.log10(peak / full) if peak > 0 else -99.0
        return round(dur, 2), round(db, 1), fr, ch
    except Exception:  # noqa: BLE001
        return 0.0, 0.0, 0, 0


def say(voice, prompt_lang, emotion, text_lang, text):
    ver = voice_version(voice)
    vdir = os.path.join(MODELS_ROOT, ver, voice)
    if not voice or os.path.basename(voice) != voice or not os.path.isdir(vdir):
        raise RuntimeError('音色不存在：%s' % voice)
    if text_lang not in TEXT_LANGS:
        raise RuntimeError('文本语言不合法：%s（只能是 %s）' % (text_lang, ' / '.join(TEXT_LANGS)))
    if not text.strip():
        raise RuntimeError('文本是空的')

    payload = {'version': ver, 'model_name': voice, 'prompt_text_lang': prompt_lang,
               'emotion': emotion, 'text': text, 'text_lang': text_lang}
    req = urllib.request.Request(GSVI_INFER, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.loads(r.read().decode('utf-8'))
    ms = int((time.time() - t0) * 1000)

    msg = res.get('msg') or ''
    url = res.get('audio_url') or ''
    if not url:
        raise RuntimeError(msg or '合成失败（没有返回音频）')

    src_name = urllib.parse.urlparse(url).path.rsplit('/', 1)[-1]
    src = os.path.join(GSVI_DIR, 'outputs', src_name)
    os.makedirs(OUT_DIR, exist_ok=True)
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', text.strip())[:14] or 'seg'
    dst_name = '%s_%s_%s.wav' % (time.strftime('%Y%m%d-%H%M%S'), voice.split('-')[-1], stem)
    dst = os.path.join(OUT_DIR, dst_name)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
    else:
        with urllib.request.urlopen(url.replace('0.0.0.0', '127.0.0.1'), timeout=120) as r:
            open(dst, 'wb').write(r.read())

    dur, db, sr, ch = wav_stats(dst)
    return {'msg': msg or '合成成功', 'file': dst, 'name': dst_name,
            'url': 'out/' + urllib.parse.quote(dst_name), 'duration': dur, 'peakDb': db,
            'sampleRate': sr, 'channels': ch, 'ms': ms, 'bytes': os.path.getsize(dst),
            'voice': voice, 'text': text}


def mimo_key():
    """Key 可能只写在用户环境变量里（当前进程没继承），所以环境变量找不到时读注册表"""
    names = ('MIMO_API_KEY', 'MIMO_APIKEY', 'MIMO_KEY', 'MIMO_TTS_KEY')
    for k, v in os.environ.items():
        if k.upper() in names and v.strip():
            return v.strip()
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
            for name in ('MiMo_API_Key', 'MiMo_API_KEY', 'MIMO_API_KEY', 'MiMo_Key', 'MIMO_KEY'):
                try:
                    v, _ = winreg.QueryValueEx(h, name)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                except FileNotFoundError:
                    continue
    except Exception:  # noqa: BLE001
        pass
    return ''


def mimo_say(voice, style, text):
    key = mimo_key()
    if not key:
        raise RuntimeError('没找到 MiMo API Key（需要环境变量 MiMo_API_Key 或 MIMO_API_KEY）')
    if not text.strip():
        raise RuntimeError('文本是空的')

    messages = []
    if (style or '').strip():
        messages.append({'role': 'user', 'content': style.strip()})
    messages.append({'role': 'assistant', 'content': text})

    payload = {'model': MIMO_MODEL, 'messages': messages,
               'audio': {'format': 'wav', 'voice': voice or '冰糖'}}
    req = urllib.request.Request(MIMO_URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            d = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'ignore')[:300]
        raise RuntimeError('MiMo 返回 %s：%s' % (e.code, detail)) from None
    ms = int((time.time() - t0) * 1000)

    try:
        b64 = d['choices'][0]['message']['audio']['data']
    except (KeyError, IndexError, TypeError):
        raise RuntimeError('MiMo 响应里没有音频：%s' % json.dumps(d, ensure_ascii=False)[:200]) from None
    raw = base64.b64decode(b64)
    if len(raw) < 2048:
        raise RuntimeError('MiMo 返回的音频过小（%d 字节）' % len(raw))

    os.makedirs(OUT_DIR, exist_ok=True)
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', text.strip())[:14] or 'seg'
    dst_name = '%s_MiMo%s_%s.wav' % (time.strftime('%Y%m%d-%H%M%S'), voice or '默认', stem)
    dst = os.path.join(OUT_DIR, dst_name)
    open(dst, 'wb').write(raw)

    dur, db, sr, ch = wav_stats(dst)
    return {'msg': '合成成功', 'engine': 'mimo', 'file': dst, 'name': dst_name,
            'url': 'out/' + urllib.parse.quote(dst_name), 'duration': dur, 'peakDb': db,
            'sampleRate': sr, 'channels': ch, 'ms': ms, 'bytes': len(raw),
            'voice': voice, 'text': text}


# ---------------------------------------------------------------- 参考人声克隆
def _safe_stem(name):
    stem = os.path.splitext(os.path.basename(name or 'ref'))[0]
    return re.sub(r'[\\/:*?"<>|\s]+', '_', stem)[:40] or 'ref'


def _ffmpeg_prep(src, dst, start=None, length=None):
    """任意格式 → 32k 单声道 16bit wav，音量压 -2dB 防削波；给定 start/length 时只截这一段"""
    cmd = [FFMPEG, '-y', '-v', 'error']
    if start is not None:
        cmd += ['-ss', '%.2f' % start]
    if length is not None:
        cmd += ['-t', '%.2f' % length]
    cmd += ['-i', src, '-ac', '1', '-ar', '32000', '-af', 'volume=-2dB',
            '-c:a', 'pcm_s16le', dst]
    p = subprocess.run(cmd, capture_output=True, timeout=180)
    if p.returncode != 0 or not os.path.isfile(dst) or os.path.getsize(dst) < 1024:
        raise RuntimeError('音频解码失败：%s'
                           % (p.stderr.decode('utf-8', 'ignore').strip()[:200] or '格式不支持'))


def classic_pick(hint=''):
    """从 GSVI 已装音色里挑一对 GPT/SoVITS 当底模（底模只管发音功底，音色由参考音频决定）"""
    try:
        d = json.loads(urllib.request.urlopen(GSVI_MODELS, timeout=20).read().decode('utf-8'))
    except Exception:  # noqa: BLE001
        raise RuntimeError('连不上 GSVI（127.0.0.1:8000），先双击 1-启动GPT-SoVITS配音.bat') from None
    gpt = list(dict.fromkeys(d.get('gpt') or []))
    sovits = list(dict.fromkeys(d.get('sovits') or []))
    if not gpt or not sovits:
        raise RuntimeError('没有可用的底模，先在「GPT-SoVITS」标签装一个音色')
    gi = hint if hint in gpt else gpt[0]
    si = hint if hint in sovits else sovits[0]
    return gi, si


def clone_upload(fname, raw, start=None, length=None):
    """保存上传的参考音频并统一转成 wav；超长自动截断到 9.5 秒"""
    os.makedirs(CLONE_DIR, exist_ok=True)
    ext = (os.path.splitext(fname)[1] or '.bin').lstrip('.')
    stamp = time.strftime('%Y%m%d-%H%M%S')
    raw_path = os.path.join(CLONE_DIR, '%s_%s.%s' % (stamp, _safe_stem(fname), ext))
    open(raw_path, 'wb').write(raw)

    wav_path = os.path.join(CLONE_DIR, '%s_%s.wav' % (stamp, _safe_stem(fname)))
    _ffmpeg_prep(raw_path, wav_path, start, length)
    dur, db, sr, ch = wav_stats(wav_path)

    trimmed = False
    if dur > REF_MAX:  # 太长就自动取前 9.5 秒，先能跑起来
        cut_path = wav_path.replace('.wav', '_cut.wav')
        _ffmpeg_prep(raw_path, cut_path, 0, 9.5)
        wav_path = cut_path
        dur, db, sr, ch = wav_stats(wav_path)
        trimmed = True

    if dur < REF_MIN:
        raise RuntimeError('参考音频只有 %.1f 秒，至少要 3 秒（建议 5~8 秒）' % dur)

    warn = ''
    if trimmed:
        warn = '原音频超过 10 秒，已自动截取前 9.5 秒；想换更干净的片段，改「起始秒」后重新上传'
    if db < -30:
        warn = (warn + '；' if warn else '') + '这段音频偏静（峰值 %.1f dB），可能是纯伴奏或静音' % db
    return {'msg': '上传成功', 'path': wav_path, 'name': os.path.basename(wav_path),
            'duration': dur, 'peakDb': db, 'sampleRate': sr, 'channels': ch,
            'trimmed': trimmed, 'warn': warn, 'source': raw_path}


def clone_asr(path):
    """用包里自带的 faster-whisper 识别参考音频文本（首次会下 ~480MB 权重）"""
    if not path or not os.path.isfile(path):
        raise RuntimeError('参考音频不存在，请先上传')
    worker = os.path.join(HERE, 'asr_worker.py')
    if not os.path.isfile(worker):
        raise RuntimeError('缺少 asr_worker.py')
    env = dict(os.environ)
    env.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
    p = subprocess.run([RUNTIME_PY, worker, path, ASR_CACHE],
                       capture_output=True, timeout=900, env=env)
    out = p.stdout.decode('utf-8', 'ignore').strip()
    last = out.splitlines()[-1] if out else ''
    try:
        d = json.loads(last)
    except Exception:  # noqa: BLE001
        err = p.stderr.decode('utf-8', 'ignore').strip()[-300:]
        raise RuntimeError('识别失败：%s' % (err or out[-300:] or '未知错误')) from None
    if d.get('error'):
        raise RuntimeError(d['error'])
    return d


def clone_say(ref_path, prompt_text, prompt_lang, text, text_lang, model_hint=''):
    """零样本克隆：参考音频 + 参考文本 → 用这个音色念新台词"""
    if not ref_path or not os.path.isfile(ref_path):
        raise RuntimeError('参考音频无效，请重新上传')
    if os.path.abspath(os.path.dirname(ref_path)) != os.path.abspath(CLONE_DIR):
        raise RuntimeError('参考音频必须来自本页上传')
    dur, db, _, _ = wav_stats(ref_path)
    if not (REF_MIN <= dur <= REF_MAX):
        raise RuntimeError('参考音频 %.1f 秒，必须在 3~10 秒之间' % dur)
    if not (prompt_text or '').strip():
        raise RuntimeError('请填写参考文本：这段音频里说的是什么，要逐字一致')
    if text_lang not in TEXT_LANGS:
        raise RuntimeError('文本语言不合法：%s' % text_lang)
    if not (text or '').strip():
        raise RuntimeError('台词是空的')

    gpt, sovits = classic_pick(model_hint)
    payload = {'version': 'v4', 'gpt_model_name': gpt, 'sovits_model_name': sovits,
               'ref_audio_path': ref_path, 'prompt_text': prompt_text,
               'prompt_text_lang': prompt_lang, 'text': text, 'text_lang': text_lang}
    req = urllib.request.Request(GSVI_CLASSIC,
                                 data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=900) as r:
        res = json.loads(r.read().decode('utf-8'))
    ms = int((time.time() - t0) * 1000)

    msg = res.get('msg') or ''
    url = res.get('audio_url') or ''
    if not url:
        raise RuntimeError(msg or '克隆失败（没有返回音频）')

    src_name = urllib.parse.urlparse(url).path.rsplit('/', 1)[-1]
    src = os.path.join(GSVI_DIR, 'outputs', src_name)
    os.makedirs(OUT_DIR, exist_ok=True)
    stem = re.sub(r'[\\/:*?"<>|\s]+', '_', text.strip())[:14] or 'seg'
    dst_name = '%s_克隆_%s.wav' % (time.strftime('%Y%m%d-%H%M%S'), stem)
    dst = os.path.join(OUT_DIR, dst_name)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
    else:
        with urllib.request.urlopen(url.replace('0.0.0.0', '127.0.0.1'), timeout=120) as r:
            open(dst, 'wb').write(r.read())

    d2, db2, sr2, ch2 = wav_stats(dst)
    return {'msg': msg or '克隆成功', 'file': dst, 'name': dst_name,
            'url': 'out/' + urllib.parse.quote(dst_name), 'duration': d2, 'peakDb': db2,
            'sampleRate': sr2, 'channels': ch2, 'ms': ms, 'bytes': os.path.getsize(dst),
            'voice': '克隆·' + os.path.basename(ref_path), 'text': text,
            'refDuration': dur, 'promptText': prompt_text,
            'baseModel': '%s / %s' % (gpt, sovits)}


def probe(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- HTTP
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        one = lambda k, d='': (q.get(k) or [d])[0]  # noqa: E731
        try:
            if u.path == '/api/status':
                return self._json({
                    'gsvi': probe('http://127.0.0.1:8000/models/v4'),
                    'aivis': probe('http://127.0.0.1:10101/version'),
                    'installRoot': INSTALL_ROOT, 'v4Dir': V4_DIR, 'aivisDir': AIVIS_MODELS})
            if u.path == '/api/ms/list':
                return self._json(ms_list(one('path')))
            if u.path == '/api/aivis/list':
                return self._json(aivis_search(int(one('page', '1') or 1)))
            if u.path == '/api/installed':
                return self._json(installed())
            if u.path == '/api/job':
                jid = one('id')
                with LOCK:
                    j = dict(JOBS.get(jid) or {})
                return self._json(j or {'state': 'missing'})
            if u.path == '/api/ms/install':
                rel = one('path')
                jid = job_new('ms', rel)
                threading.Thread(target=do_ms_install, args=(jid, rel), daemon=True).start()
                return self._json({'job': jid})
            if u.path == '/api/aivis/install':
                mu, nm = one('uuid'), one('name')
                jid = job_new('aivis', nm or mu)
                threading.Thread(target=do_aivis_install, args=(jid, mu, nm), daemon=True).start()
                return self._json({'job': jid})
            if u.path == '/api/open':
                p = one('path')
                if p and os.path.exists(p):
                    # 传文件时打开它所在的文件夹，别把 wav 直接播了
                    target = p if os.path.isdir(p) else os.path.dirname(p)
                    os.startfile(target)  # noqa: S606
                    return self._json({'ok': True, 'opened': target})
                return self._json({'ok': False, 'error': '目录不存在'}, 404)
            if u.path == '/api/clone/models':
                try:
                    gpt, sovits = classic_pick('')
                    ok = True
                except Exception as e:  # noqa: BLE001
                    return self._json({'error': str(e), 'gpt': [], 'sovits': []}, 200)
                d = json.loads(urllib.request.urlopen(GSVI_MODELS, timeout=20).read().decode('utf-8'))
                return self._json({'gpt': list(dict.fromkeys(d.get('gpt') or [])),
                                   'sovits': list(dict.fromkeys(d.get('sovits') or [])),
                                   'default': {'gpt': gpt, 'sovits': sovits},
                                   'textLangs': TEXT_LANGS, 'refMin': REF_MIN, 'refMax': REF_MAX,
                                   'cloneDir': CLONE_DIR, 'outDir': OUT_DIR, 'ready': ok})
            if u.path == '/api/tts/voices':
                return self._json({'voices': voices(), 'textLangs': TEXT_LANGS,
                                   'outDir': OUT_DIR,
                                   'gsvi': probe('http://127.0.0.1:8000/models/v4'),
                                   'mimo': {'ready': bool(mimo_key()), 'voices': MIMO_VOICES,
                                            'model': MIMO_MODEL}})
        except Exception as e:  # noqa: BLE001
            return self._json({'error': str(e)}, 500)
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            if u.path == '/api/clone/upload':
                # 裸字节上传：?name=xxx&start=&len=，避免 multipart 解析
                qs = urllib.parse.parse_qs(u.query)
                one = lambda k, d=None: (qs.get(k) or [d])[0]  # noqa: E731
                raw = self.rfile.read(n) if n else b''
                if not raw:
                    raise RuntimeError('没有收到音频数据')
                def _num(k):
                    v = one(k)
                    try:
                        return float(v) if v not in (None, '') else None
                    except ValueError:
                        return None
                return self._json(clone_upload(one('name') or 'ref.bin', raw, _num('start'), _num('len')))
            data = json.loads(self.rfile.read(n).decode('utf-8')) if n else {}
            if u.path == '/api/clone/asr':
                return self._json(clone_asr(data.get('path', '')))
            if u.path == '/api/clone/say':
                return self._json(clone_say(data.get('refPath', ''), data.get('promptText', ''),
                                            data.get('promptLang', '中文'), data.get('text', ''),
                                            data.get('textLang', '中文'), data.get('model', '')))
            if u.path == '/api/tts/say':
                if data.get('engine') == 'mimo':
                    res = mimo_say(data.get('voice', ''), data.get('style', ''), data.get('text', ''))
                else:
                    res = say(data.get('voice', ''), data.get('promptLang', ''),
                              data.get('emotion', '默认'), data.get('textLang', ''),
                              data.get('text', ''))
                return self._json(res)
        except urllib.error.HTTPError as e:
            return self._json({'error': 'GSVI 返回 %s：%s' % (e.code, e.reason)}, 500)
        except Exception as e:  # noqa: BLE001
            return self._json({'error': str(e)}, 500)
        return self._json({'error': '未知接口'}, 404)


def main():
    httpd, used = None, PORT
    for p in range(PORT, PORT + 12):
        try:
            httpd = ThreadingHTTPServer(('127.0.0.1', p), Handler)
            used = p
            break
        except OSError:
            continue
    if httpd is None:
        print('8899-8910 全被占用，放弃启动', flush=True)
        return

    url = 'http://127.0.0.1:%d' % used
    print('音色库服务: %s' % url, flush=True)
    print('模型目录: %s' % V4_DIR, flush=True)
    if used != PORT:
        print('提示: %d 被别的程序占用，已自动改用 %d（浏览器地址以上面这行为准）' % (PORT, used), flush=True)
    if '--open' in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()


if __name__ == '__main__':
    main()
