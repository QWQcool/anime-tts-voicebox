/* 音色库前端：无框架，所有网络访问都打到本地 server.py */
(() => {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  const mb = (n) => (n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.round(n / 1024) + ' KB');
  const toastEl = $('#toast');
  let toastTimer = null;

  function toast(msg, ms = 2600) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
  }

  async function api(path) {
    const r = await fetch(path);
    const j = await r.json();
    if (!r.ok || j.error) throw new Error(j.error || ('HTTP ' + r.status));
    return j;
  }

  /* ------------------------------------------------ 导航 */
  $$('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.nav-item').forEach((b) => b.classList.toggle('is-on', b === btn));
      $$('.tab').forEach((t) => t.classList.toggle('is-on', t.id === 'tab-' + btn.dataset.tab));
      if (btn.dataset.tab === 'dub' && !state.dubLoaded) loadDub();
      if (btn.dataset.tab === 'ms' && !state.msLoaded) loadMs('');
      if (btn.dataset.tab === 'aivis' && !state.avLoaded) loadAivis();
      if (btn.dataset.tab === 'mine') loadMine();
    });
  });

  /* ------------------------------------------------ 服务状态 */
  async function loadStatus() {
    try {
      const s = await api('/api/status');
      setStat('#st-gsvi', s.gsvi, s.gsvi ? '在线' : '未启动');
      setStat('#st-aivis', s.aivis, s.aivis ? '在线' : '未启动');
      state.paths = s;
    } catch (e) {
      setStat('#st-gsvi', false, '连不上');
      setStat('#st-aivis', false, '连不上');
    }
  }

  function setStat(sel, on, text) {
    const el = $(sel);
    el.classList.toggle('on', !!on);
    el.classList.toggle('off', !on);
    el.querySelector('b').textContent = text;
  }

  $('#btn-open-v4').addEventListener('click', () => {
    const p = (state.paths && state.paths.v4Dir) || '';
    fetch('/api/open?path=' + encodeURIComponent(p)).then(() => toast('已打开音色目录')).catch(() => toast('打不开目录'));
  });

  /* ------------------------------------------------ 任务队列 */
  const state = {
    msPath: '', msLoaded: false, msFiles: [], avLoaded: false,
    avModels: [], avTotal: 76, wish: [], jobs: new Map(), paths: null,
    dubLoaded: false, dub: null, engine: 'local',
  };

  try { state.wish = JSON.parse(localStorage.getItem('wish') || '[]'); } catch (e) { state.wish = []; }
  const saveWish = () => localStorage.setItem('wish', JSON.stringify(state.wish));

  async function startJob(url, label, btn) {
    try {
      const j = await api(url);
      state.jobs.set(j.job, { label, id: j.job, state: 'running', phase: '排队中', btn });
      renderJobs();
      poll(j.job);
      toast('已开始：' + label);
    } catch (e) {
      toast('装不了：' + e.message, 4000);
      if (btn) { btn.disabled = false; btn.textContent = '装进音色库'; }
    }
  }

  function settleBtn(j) {
    const b = j.btn;
    if (!b) return;
    if (j.state === 'done' || j.state === 'exists') {
      b.disabled = true;
      b.textContent = j.state === 'exists' ? '已装 ✓' : '装好了 ✓';
    } else if (j.state === 'error') {
      b.disabled = false;
      b.textContent = '重试';
    }
  }

  async function poll(id) {
    const j = await api('/api/job?id=' + encodeURIComponent(id)).catch(() => null);
    if (!j) return;
    const row = state.jobs.get(id) || {};
    Object.assign(row, j, { label: j.title || row.label, id });
    state.jobs.set(id, row);
    renderJobs();
    if (j.state === 'running') setTimeout(() => poll(id), 900);
    else {
      loadStatus();
      settleBtn(row);
      if (j.state === 'done') { toast('装好了：' + (j.result && j.result.name || ''), 4000); markInstalled(); }
      if (j.state === 'exists') toast('这个已经装过了，没动它');
      if (j.state === 'error') toast('失败：' + j.error, 5000);
    }
  }

  function renderJobs() {
    const box = $('#jobs');
    const list = Array.from(state.jobs.values()).reverse();
    $('#vu').classList.toggle('live', list.some((j) => j.state === 'running'));
    if (!list.length) {
      box.innerHTML = '<p class="empty">还没开始装。点卡片上的「装进音色库」。</p>';
      return;
    }
    box.innerHTML = list.map((j) => {
      const done = j.state === 'done';
      const bad = j.state === 'error';
      const size = j.bytes ? mb(j.bytes) : '';
      let line = j.phase || '';
      if (j.state === 'running' && size) line += ' · 已下 ' + size;
      if (done && j.result) line = '已就位 · ' + mb(j.result.size || 0);
      if (bad) line = j.error || '失败';
      const acts = done && j.result
        ? '<div class="acts"><button class="mini-btn" data-open="' + esc(j.result.path) + '">打开所在文件夹</button></div>'
        : '';
      const warn = done && j.result && j.result.warning
        ? '<p class="warn-line">' + esc(j.result.warning) + '</p>' : '';
      return '<div class="job ' + (done ? 'done' : bad ? 'error' : j.state) + '">'
        + '<h4>' + esc(j.label) + '</h4>'
        + '<p>' + esc(line) + '</p>' + warn
        + '<div class="bar"><i></i></div>' + acts + '</div>';
    }).join('');
  }

  $('#jobs').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-open]');
    if (!b) return;
    fetch('/api/open?path=' + encodeURIComponent(b.dataset.open));
  });

  /* ------------------------------------------------ 待装清单 */
  function renderWish() {
    const box = $('#wish');
    if (!state.wish.length) {
      box.innerHTML = '<p class="empty">在卡片上点「加入清单」，攒好后复制给我，我一次帮你装。</p>';
      return;
    }
    box.innerHTML = state.wish.map((w, i) =>
      '<div class="wish-item"><div><b>' + esc(w.name) + '</b><br>' + esc(w.detail) + '</div>'
      + '<button class="rm" data-i="' + i + '" title="移除">×</button></div>').join('');
  }

  $('#wish').addEventListener('click', (ev) => {
    const b = ev.target.closest('.rm');
    if (!b) return;
    state.wish.splice(+b.dataset.i, 1);
    saveWish();
    renderWish();
  });

  function copyText(text) {
    const fallback = () => Promise.resolve(legacyCopy(text));
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(() => true).catch(fallback);
    }
    return fallback();
  }

  function legacyCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;top:-999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }

  $('#btn-copy-list').addEventListener('click', async () => {
    if (!state.wish.length) return toast('清单是空的');
    const text = state.wish.map((w) => w.line).join('\n');
    const ok = await copyText(text);
    toast(ok ? '已复制 ' + state.wish.length + ' 条，粘给我就行' : '复制被拦截，请手动选中清单文字');
  });

  function addWish(item) {
    if (state.wish.some((w) => w.line === item.line)) return toast('清单里已经有它了');
    state.wish.push(item);
    saveWish();
    renderWish();
    toast('已加入清单');
  }

  /* ------------------------------------------------ GPT-SoVITS 浏览 */
  async function loadMs(path) {
    state.msPath = path;
    state.msLoaded = true;
    const body = $('#ms-body');
    body.innerHTML = '<div class="loading">读取目录…</div>';
    renderCrumbs(path);
    try {
      const d = await api('/api/ms/list?path=' + encodeURIComponent(path));
      if (d.dirs.length) {
        $('#ms-filter').hidden = true;
        body.innerHTML = '<p class="count-hint">' + d.dirs.length + ' 个下级目录 · 点进去继续</p>'
          + '<div class="tiles">' + d.dirs.map((x) =>
            '<button class="tile" data-dir="' + esc(x.path) + '">' + esc(x.name) + '<span>›</span></button>').join('')
          + '</div>';
      } else if (d.files.length) {
        state.msFiles = d.files;
        $('#ms-filter').hidden = false;
        $('#ms-q').value = '';
        renderMsFiles();
      } else {
        body.innerHTML = '<p class="empty">这个目录是空的，换一条路。</p>';
      }
    } catch (e) {
      body.innerHTML = '<div class="errbox">读取失败：' + esc(e.message) + '</div>';
    }
  }

  function renderMsFiles() {
    const q = $('#ms-q').value.trim().toLowerCase();
    const all = state.msFiles || [];
    const list = q ? all.filter((f) => f.name.toLowerCase().includes(q)) : all;
    const seg = state.msPath.split('/').filter(Boolean);
    const prefix = seg.length >= 2 ? seg[0] + '-' + seg[1] + '-' : '';
    const avg = all.length ? all.reduce((s, f) => s + (f.size || 0), 0) / all.length : 0;
    let head = '<p class="count-hint">' + all.length + ' 个角色 · 平均 ' + mb(avg)
      + ' · 装好后的目录名形如 <code>' + esc(prefix) + '角色</code>';
    if (q) head += ' · 筛选出 ' + list.length + ' 个';
    head += '</p>';
    $('#ms-body').innerHTML = head + (list.length
      ? '<div class="tape-grid">' + list.map(tapeCard).join('') + '</div>'
      : '<p class="empty">没有匹配的角色，换个关键词。</p>');
  }

  let msTimer = null;
  $('#ms-q').addEventListener('input', () => {
    clearTimeout(msTimer);
    msTimer = setTimeout(renderMsFiles, 120);
  });

  function partsToLabel(path, fname) {
    const seg = path.split('/').filter(Boolean);
    const role = fname.replace(/\.zip$/i, '');
    return seg.length >= 2 ? seg[0] + '-' + seg[1] + '-' + role : role;
  }

  function tapeCard(f) {
    const seg = state.msPath.split('/').filter(Boolean);
    const game = seg[0] || '';
    const lang = seg[1] || '';
    const role = f.name.replace(/\.zip$/i, '');
    const label = game + '-' + lang + '-' + role;
    return '<article class="tape">'
      + '<div class="spine">' + esc(game + ' · ' + lang) + '</div>'
      + '<div class="tape-body">'
      + '<div class="reels"><span class="reel"></span><span class="reel"></span></div>'
      + '<h3 title="' + esc(role) + '">' + esc(role) + '</h3>'
      + '<p class="meta">' + mb(f.size || 0) + ' · ' + esc(label) + '</p>'
      + (f.url ? '<a class="src" target="_blank" rel="noopener" href="' + esc(f.url) + '">在 ModelScope 看这个角色 ↗</a>' : '')
      + '<div class="tape-actions">'
      + '<button class="btn" data-install="' + esc(f.path) + '" data-label="' + esc(label) + '">装进音色库</button>'
      + '<button class="btn sec" data-wish="' + esc(f.path) + '" data-wishname="' + esc(role) + '" title="加入清单">☆</button>'
      + '</div></div></article>';
  }

  function renderCrumbs(path) {
    const seg = path.split('/').filter(Boolean);
    let acc = '';
    let html = '<button class="crumb' + (seg.length ? '' : ' is-here') + '" data-crumb="">全部游戏</button>';
    seg.forEach((s, i) => {
      acc = acc ? acc + '/' + s : s;
      const here = i === seg.length - 1;
      html += '<span>›</span><button class="crumb' + (here ? ' is-here' : '') + '" data-crumb="' + esc(acc) + '">' + esc(s) + '</button>';
    });
    $('#ms-crumbs').innerHTML = html;
  }

  $('#ms-crumbs').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-crumb]');
    if (!b || b.classList.contains('is-here')) return;
    loadMs(b.dataset.crumb);
  });

  $('#ms-body').addEventListener('click', (ev) => {
    const dir = ev.target.closest('[data-dir]');
    if (dir) return loadMs(dir.dataset.dir);
    const ins = ev.target.closest('[data-install]');
    if (ins) {
      const label = ins.dataset.label;
      ins.disabled = true;
      ins.textContent = '下载中…';
      startJob('/api/ms/install?path=' + encodeURIComponent(ins.dataset.install), label, ins);
      return;
    }
    const w = ev.target.closest('[data-wish]');
    if (w) {
      const p = w.dataset.wish;
      addWish({
        name: w.dataset.wishname,
        detail: p,
        line: '[GPT-SoVITS] ' + p + '  -> 目录名 ' + p.split('/').slice(0, 2).join('-') + '-' + w.dataset.wishname,
      });
    }
  });

  /* ------------------------------------------------ AivisSpeech */
  async function loadAivis() {
    state.avLoaded = true;
    const body = $('#av-body');
    body.innerHTML = '<div class="loading">读取 AivisHub（3 页）…</div>';
    try {
      const pages = await Promise.all([1, 2, 3].map((p) => api('/api/aivis/list?page=' + p)));
      state.avModels = pages.flatMap((p) => p.models);
      state.avTotal = pages[0].total;
      renderAivis();
    } catch (e) {
      body.innerHTML = '<div class="errbox">读取失败：' + esc(e.message) + '</div>';
    }
  }

  function renderAivis() {
    const q = $('#av-q').value.trim().toLowerCase();
    const lic = $('#av-lic').value;
    let list = state.avModels;
    if (q) {
      list = list.filter((m) => (m.name + ' ' + m.speaker + ' ' + (m.description || '') + ' ' + (m.timbre || ''))
        .toLowerCase().includes(q));
    }
    if (lic === 'ACML') list = list.filter((m) => /ACML\s*1\.0/i.test(m.license || ''));
    if (lic === 'NC') list = list.filter((m) => /NC/i.test(m.license || ''));

    const head = '<p class="count-hint">共 ' + (state.avTotal || 76) + ' 个公开声线，当前显示 ' + list.length + ' 个</p>';
    if (!list.length) {
      $('#av-body').innerHTML = head + '<p class="empty">没有匹配的声线，换个关键词。</p>';
      return;
    }
    $('#av-body').innerHTML = head + list.map(avCard).join('');
  }

  function licClass(l) {
    if (!l) return 'other';
    if (/NC/i.test(l)) return 'nc';
    if (/ACML\s*1\.0/i.test(l)) return 'ok';
    return 'other';
  }

  function avCard(m) {
    const lc = licClass(m.license);
    const desc = (m.description || '').split('\n')[0];
    return '<article class="avcard">'
      + '<div class="av-top"><h3 title="' + esc(m.name) + '">' + esc(m.name) + '</h3>'
      + '<span class="badge ' + lc + '">' + esc(m.license || '未知') + '</span></div>'
      + '<p class="av-desc">' + esc(desc || '（作者没写简介）') + '</p>'
      + '<p class="av-meta">下载 <b>' + (m.downloads || 0) + '</b> · ' + esc(m.timbre || '-')
      + ' · ' + esc(m.speaker || '-') + '</p>'
      + '<p class="av-meta">' + esc(m.uuid) + '</p>'
      + (m.url ? '<a class="src" target="_blank" rel="noopener" href="' + esc(m.url) + '">在 AivisHub 看介绍 / 试听 ↗</a>' : '')
      + '<div class="tape-actions">'
      + '<button class="btn" data-av="' + esc(m.uuid) + '" data-name="' + esc(m.name) + '"'
      + (m.installed ? ' disabled' : '') + '>' + (m.installed ? '已装' : '装进引擎') + '</button>'
      + '<button class="btn sec" data-avwish="' + esc(m.uuid) + '" data-name="' + esc(m.name) + '"'
      + ' data-lic="' + esc(m.license || '') + '" title="加入清单">☆</button>'
      + '</div></article>';
  }

  let avTimer = null;
  $('#av-q').addEventListener('input', () => {
    clearTimeout(avTimer);
    avTimer = setTimeout(renderAivis, 140);
  });
  $('#av-lic').addEventListener('change', renderAivis);

  $('#av-body').addEventListener('click', (ev) => {
    const ins = ev.target.closest('[data-av]');
    if (ins) {
      ins.disabled = true;
      ins.textContent = '下载中…';
      startJob('/api/aivis/install?uuid=' + encodeURIComponent(ins.dataset.av)
        + '&name=' + encodeURIComponent(ins.dataset.name), ins.dataset.name, ins);
      return;
    }
    const w = ev.target.closest('[data-avwish]');
    if (w) {
      addWish({
        name: w.dataset.name,
        detail: 'AivisSpeech · ' + (w.dataset.lic || '') + ' · ' + w.dataset.avwish,
        line: '[AivisSpeech] ' + w.dataset.name + '  uuid=' + w.dataset.avwish + '  license=' + (w.dataset.lic || '?'),
      });
    }
  });

  function markInstalled() {
    // 下次切到 Aivis 标签时重新拉一次，让「已装」状态是服务端真实值
    state.avLoaded = false;
  }

  /* ------------------------------------------------ 配音台 */
  const dsel = (id) => $(id);

  async function loadDub() {
    state.dubLoaded = true;
    try {
      const d = await api('/api/tts/voices');
      state.dub = d;
      if (d.outDir) $('#dub-dir').textContent = d.outDir;

      // 云端引擎（可选）：无 Key 时按钮置灰并说明原因
      const m = d.mimo || {};
      dsel('#dub-mvoice').innerHTML = (m.voices || [])
        .map((v) => '<option value="' + esc(v.id) + '">' + esc(v.label) + '</option>').join('');
      const mBtn = $('[data-engine="mimo"]');
      mBtn.disabled = !m.ready;
      mBtn.title = m.ready ? '' : '没找到 MiMo API Key（环境变量 MiMo_API_Key / MIMO_API_KEY）';
      dsel('#dub-tlang').innerHTML = d.textLangs.map((t) => '<option>' + esc(t) + '</option>').join('');

      const vs = d.voices.filter((v) => v.hasWeights);
      if (!vs.length) {
        dsel('#dub-voice').innerHTML = '<option value="">（还没有音色）</option>';
        dsel('#dub-go').disabled = true;
        dsel('#dub-hint').textContent = 'models\\v4 里没有可用音色，先去「GPT-SoVITS」标签装一个。';
        return;
      }
      dsel('#dub-voice').innerHTML = vs.map((v) =>
        '<option value="' + esc(v.voice) + '">' + esc(v.role) + ' · ' + esc(v.game) + ' ' + esc(v.lang) + '</option>').join('');
      dsel('#dub-voice').addEventListener('change', onVoiceChange);
      onVoiceChange();

      if (!d.gsvi) dsel('#dub-hint').textContent = 'GSVI 服务没启动（8000 端口无响应），先双击「1-启动GPT-SoVITS配音.bat」。';
    } catch (e) {
      dsel('#dub-hint').textContent = '读不到音色：' + e.message;
    }
  }

  function onVoiceChange() {
    const v = (state.dub.voices || []).find((x) => x.voice === dsel('#dub-voice').value);
    if (!v) return;
    dsel('#dub-plang').innerHTML = v.refLangs.map((l) => '<option>' + esc(l) + '</option>').join('')
      || '<option>中文</option>';
    fillEmotions();
    const refLang = v.refLangs[0] || '中文';
    if (state.dub.textLangs.includes(refLang) && !dsel('#dub-tlang').dataset.touched) {
      dsel('#dub-tlang').value = refLang;
    }
    dsel('#dub-hint').textContent = '参考音频语言 ' + (v.refLangs.join(' / ') || '无')
      + '，来自音色包自带参考音频，不需要你上传。';
  }

  function fillEmotions() {
    const v = (state.dub.voices || []).find((x) => x.voice === dsel('#dub-voice').value);
    const lang = dsel('#dub-plang').value;
    const emos = (v && v.emotions && v.emotions[lang]) || [];
    dsel('#dub-emotion').innerHTML = (emos.length ? emos : ['默认'])
      .map((e) => '<option>' + esc(e) + '</option>').join('');
  }

  dsel('#dub-plang').addEventListener('change', fillEmotions);
  dsel('#dub-tlang').addEventListener('change', (e) => { e.target.dataset.touched = '1'; });

  $$('#dub-engine .seg-b').forEach((b) => {
    b.addEventListener('click', () => {
      if (b.disabled) return;
      state.engine = b.dataset.engine;
      $$('#dub-engine .seg-b').forEach((x) => x.classList.toggle('is-on', x === b));
      dsel('#grp-local').hidden = state.engine !== 'local';
      dsel('#grp-mimo').hidden = state.engine !== 'mimo';
      dsel('#dub-hint').hidden = state.engine === 'mimo';
      if (state.engine === 'mimo') {
        dsel('#dub-hint').textContent = '';
      } else if (state.dub && !state.dub.gsvi) {
        dsel('#dub-hint').textContent = 'GSVI 服务没启动（8000 端口无响应），先双击「1-启动GPT-SoVITS配音.bat」。';
      } else {
        onVoiceChange();
      }
    });
  });

  function dubLines() {
    return dsel('#dub-text').value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  }

  function updateDubCount() {
    const lines = dubLines();
    const chars = lines.join('').length;
    dsel('#dub-count').textContent = lines.length + ' 段 · ' + chars + ' 字';
  }

  dsel('#dub-text').addEventListener('input', updateDubCount);
  dsel('#dub-text').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); dubGo(); }
  });
  dsel('#dub-go').addEventListener('click', dubGo);

  async function dubGo() {
    const lines = dubLines();
    if (!lines.length) return toast('先写点台词');
    const btn = dsel('#dub-go');
    if (btn.disabled) return;
    const payloadBase = state.engine === 'mimo'
      ? { engine: 'mimo', voice: dsel('#dub-mvoice').value, style: dsel('#dub-style').value }
      : {
        engine: 'local',
        voice: dsel('#dub-voice').value,
        promptLang: dsel('#dub-plang').value,
        emotion: dsel('#dub-emotion').value,
        textLang: dsel('#dub-tlang').value,
      };
    btn.disabled = true;
    dsel('#dub-out').innerHTML = '';
    const t0 = Date.now();
    for (let i = 0; i < lines.length; i += 1) {
      btn.textContent = '配音中 ' + (i + 1) + '/' + lines.length + '…';
      try {
        const res = await fetch('/api/tts/say', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.assign({}, payloadBase, { text: lines[i] })),
        });
        const j = await res.json();
        if (!res.ok || j.error) throw new Error(j.error || ('HTTP ' + res.status));
        addDubItem(i + 1, lines[i], j);
      } catch (e) {
        addDubItem(i + 1, lines[i], null, e.message);
      }
    }
    btn.disabled = false;
    btn.textContent = '开始配音 (Ctrl+Enter)';
    const sec = ((Date.now() - t0) / 1000).toFixed(1);
    toast('全部完成，' + lines.length + ' 段 / ' + sec + ' 秒');
  }

  function addDubItem(no, text, r, err) {
    const box = dsel('#dub-out');
    const el = document.createElement('div');
    el.className = 'dub-item' + (err ? ' bad' : '');
    if (err) {
      el.innerHTML = '<span class="no">' + no + '</span>'
        + '<div><p class="say">' + esc(text) + '</p>'
        + '<p class="errmsg">' + esc(err) + '</p></div>'
        + '<div class="stats"><em>失败</em></div>';
      el.title = err;
      box.appendChild(el);
      toast('第 ' + no + ' 段失败：' + err, 6000);
      return;
    }
    const quiet = r.peakDb > -99 && r.peakDb < -25;
    el.innerHTML = '<span class="no">' + no + '</span>'
      + '<div><p class="say">' + esc(text) + '</p>'
      + '<audio controls preload="metadata" src="' + esc(r.url) + '"></audio></div>'
      + '<div class="stats"><b>' + r.duration.toFixed(2) + ' s</b><br>'
      + (quiet ? '<em>峰值 ' + r.peakDb + ' dB（偏静，检查文本语言）</em>' : '峰值 ' + r.peakDb + ' dB') + '<br>'
      + (r.ms / 1000).toFixed(1) + ' s 生成<br>'
      + '<a class="dl" download="' + esc(r.name) + '" href="' + esc(r.url) + '">保存</a> · '
      + '<a class="dl" href="#" data-dl="' + esc(r.file) + '">文件夹</a></div>';
    box.appendChild(el);
  }

  dsel('#dub-out').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-dl]');
    if (b) { ev.preventDefault(); fetch('/api/open?path=' + encodeURIComponent(b.dataset.dl)); }
  });

  /* ------------------------------------------------ 已装 */
  async function loadMine() {
    const box = $('#mine-body');
    box.innerHTML = '<div class="loading">扫描中…</div>';
    try {
      const d = await api('/api/installed');
      const ms = d.gptSovits.map((m) => {
        const ok = m.hasCkpt && m.hasPth;
        return '<div class="mine-row">'
          + '<span class="' + (ok ? 'ok-dot' : 'bad-dot') + '">' + (ok ? '✓' : '✗') + '</span>'
          + '<div><div class="nm">' + esc(m.dir) + '</div>'
          + '<div class="sub">参考音频语言 ' + esc(m.langs.join(' / ') || '无') + '</div></div>'
          + '<div class="sp"><button class="mini-btn" data-open2="' + esc(m.path) + '">打开</button></div></div>';
      }).join('');
      const av = d.aivis.map((m) => '<div class="mine-row"><span class="ok-dot">✓</span>'
        + '<div><div class="nm">' + esc(m.uuid) + '</div><div class="sub">' + mb(m.size) + '</div></div></div>').join('');
      box.innerHTML = '<div class="mine-group"><h3>GPT-SoVITS · ' + d.gptSovits.length + ' 个</h3>'
        + (ms || '<p class="empty">还没有，去「GPT-SoVITS」标签装一个。</p>')
        + '<p class="sub" style="font:11.5px/1.5 var(--mono);color:var(--muted)">目录：' + esc(d.v4Dir) + '</p></div>'
        + '<div class="mine-group"><h3>AivisSpeech · ' + d.aivis.length + ' 个</h3>'
        + (av || '<p class="empty">还没有。</p>')
        + '<p class="sub" style="font:11.5px/1.5 var(--mono);color:var(--muted)">目录：' + esc(d.aivisDir) + '</p></div>';
    } catch (e) {
      box.innerHTML = '<div class="errbox">扫描失败：' + esc(e.message) + '</div>';
    }
  }

  $('#mine-body').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-open2]');
    if (b) fetch('/api/open?path=' + encodeURIComponent(b.dataset.open2));
  });

  $('#btn-refresh-mine').addEventListener('click', loadMine);

  /* ------------------------------------------------ 启动 */
  renderWish();
  loadStatus();
  loadDub();
  updateDubCount();
  setInterval(loadStatus, 8000);
})();
