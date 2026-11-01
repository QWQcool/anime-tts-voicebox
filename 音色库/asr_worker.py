"""参考音频自动识别（供 server.py 调用，必须用 GSVI 自带运行时执行）

用法：runtime\\python.exe asr_worker.py <音频路径> [权重缓存目录]
输出：最后一行是 JSON —— {"text": ..., "language": ..., "langProb": ...} 或 {"error": ...}
"""
import contextlib
import io
import json
import os
import sys

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': '缺少音频路径'}, ensure_ascii=False))
        return
    path = sys.argv[1]
    cache = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    if not os.path.isfile(path):
        print(json.dumps({'error': '音频不存在：%s' % path}, ensure_ascii=False))
        return

    try:
        from faster_whisper import WhisperModel
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'error': 'faster_whisper 不可用：%s' % e}, ensure_ascii=False))
        return

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            model = WhisperModel('small', device='cpu', compute_type='int8', download_root=cache)
            segments, info = model.transcribe(path, language=None, beam_size=5,
                                              vad_filter=False, condition_on_previous_text=True)
            text = ''.join(s.text for s in segments).strip()
        print(json.dumps({'text': text, 'language': info.language,
                          'langProb': round(float(info.language_probability), 2)},
                         ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({'error': '识别失败：%s' % e}, ensure_ascii=False))


if __name__ == '__main__':
    main()
