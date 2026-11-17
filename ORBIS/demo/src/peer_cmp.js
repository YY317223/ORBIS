/* ============================================================
   对比盒子（Atlas 那一版）
   ------------------------------------------------------------
   和搭档那版「加入对比 → 左下角折线」不同，这版是：
     把国家拖进盒子 → 点「生成对比图」→ 四个指标并排 + GDP 走势（对数刻度）
   入口有三个，都指向这里：
     · 卡片右上角「对比」
     · 搭档左侧面板的「＋ 加入对比」（捕获阶段拦下来，不让他打开自己那套）
     · 地球页面右上角如果有对比按钮，也走这里
   数据仍然用 build/card_data.js 那一份，不额外请求。
   ============================================================ */
(function () {
  'use strict';
  var D = window.__PCARD__;
  if (!D) return;

  var YEARS = D.years, IDX = D.index, SER = D.series, WLD = D.wld, FLAGS = D.flags || {};
  var N = YEARS.length;
  var CMPC = ['#6fb4d8', '#e8a34a', '#7fc08a', '#b58ac0', '#e07a6a', '#5fb8b0'];
  var MAX = 6;

  var st = { open: false, list: [], q: '', view: 'pick' };
  var el = null;

  /* ---------- 格式化 ---------- */
  function moneyFull(v) {
    if (v == null) return '—';
    if (v >= 1e12) return '$' + (v / 1e12).toFixed(v >= 1e13 ? 1 : 2) + '万亿';
    if (v >= 1e8) return '$' + Math.round(v / 1e8).toLocaleString('en-US') + '亿';
    if (v >= 1e4) return '$' + Math.round(v / 1e4) + '万';
    return '$' + Math.round(v);
  }
  function popFull(v) {
    if (v == null) return '—';
    if (v >= 1e8) return (v / 1e8).toFixed(2) + ' 亿';
    if (v >= 1e4) return (v / 1e4).toFixed(0) + ' 万';
    return Math.round(v).toString();
  }
  /* 坐标轴上的金额要短：$10.0万亿 会顶出左边距 */
  function axisMoney(v) {
    if (v >= 1e12) return (v / 1e12).toFixed(v >= 1e13 ? 0 : 1) + '万亿';
    if (v >= 1e8) return Math.round(v / 1e8) + '亿';
    if (v >= 1e4) return Math.round(v / 1e4) + '万';
    return String(Math.round(v));
  }
  function val(iso, m, yi) {
    var s = SER[iso];
    if (!s || !s[m]) return null;
    return s[m][yi];
  }
  function fmt(m, v) {
    if (v == null) return '—';
    if (m === 'pop') return popFull(v);
    if (m === 'life') return v.toFixed(1) + ' 岁';
    if (m === 'gdppc') return '$' + Math.round(v).toLocaleString('en-US');
    return moneyFull(v);
  }
  function curYi() {
    var e = document.getElementById('dyr');
    var y = e ? parseInt(String(e.textContent).replace(/[^\d]/g, ''), 10) : NaN;
    var i = YEARS.indexOf(y);
    return i < 0 ? N - 2 : i;
  }
  function curMetric() {
    var b = document.querySelector('#dchips button.on');
    var k = b && b.getAttribute('data-i');
    if (k === 'pc') return 'gdppc';
    if (k === 'le') return 'life';
    if (k === 'pop') return 'pop';
    return 'gdp';
  }
  function toast(msg) {
    if (typeof window.__pshellToast === 'function') { window.__pshellToast(msg); return; }
  }
  function color(k) {
    var i = st.list.indexOf(k);
    return CMPC[(i < 0 ? 0 : i) % CMPC.length];
  }

  /* ---------- 面板骨架 ---------- */
  function ensure() {
    if (el) return el;
    el = document.createElement('aside');
    el.id = 'pcmp';
    document.body.appendChild(el);
    el.addEventListener('click', onClick);
    el.addEventListener('input', function (e) {
      if (e.target.id === 'pcmpQ') { st.q = e.target.value.trim(); renderList(); }
    });
    return el;
  }

  function open(iso) {
    ensure();
    if (iso && SER[iso] && st.list.indexOf(iso) < 0) {
      if (st.list.length >= MAX) toast('最多对比 ' + MAX + ' 个国家');
      else st.list.push(iso);
    }
    st.view = 'pick';
    st.open = true;
    document.body.classList.add('pcmp-on');
    el.classList.add('on');
    render();
    if (iso) toast('已加入对比 · 再选一个就能生成');
  }

  function close() {
    st.open = false;
    document.body.classList.remove('pcmp-on');
    if (el) el.classList.remove('on', 'result');
  }

  function toggle(iso) { st.open ? close() : open(iso); }

  /* ---------- 选国家 ---------- */
  function render() {
    ensure();
    el.classList.toggle('result', st.view === 'result');
    if (st.view === 'pick') renderPick(); else renderResult();
  }

  function renderPick() {
    el.innerHTML =
      '<div class="pcmp-head">' +
        '<div><div class="k">Compare</div><h2>把国家放进盒子</h2>' +
        '<div class="sub">拖进来，或者直接点下面的国家</div></div>' +
        '<button class="pcmp-ico" data-act="close" aria-label="关闭">✕</button>' +
      '</div>' +
      '<div class="pcmp-body">' +
        '<div class="pcmp-drop" id="pcmpDrop"></div>' +
        '<div class="pcmp-sect"><span>候选国家</span><span>拖动 / 点击添加</span></div>' +
        '<div class="pcmp-search">' +
          '<svg viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>' +
          '<input id="pcmpQ" placeholder="搜索国家 / 地区" autocomplete="off" spellcheck="false" value="' + (st.q || '') + '">' +
        '</div>' +
        '<div class="pcmp-list" id="pcmpList"></div>' +
      '</div>' +
      '<div class="pcmp-foot"><button class="pcmp-go" id="pcmpGo" disabled>生成对比图</button></div>';
    bindDrop();
    renderChips();
    renderList();
  }

  function bindDrop() {
    var drop = el.querySelector('#pcmpDrop');
    if (!drop) return;
    drop.addEventListener('dragover', function (e) {
      e.preventDefault();
      try { e.dataTransfer.dropEffect = 'copy'; } catch (x) {}
      drop.classList.add('over');
    });
    drop.addEventListener('dragleave', function (e) {
      if (!drop.contains(e.relatedTarget)) drop.classList.remove('over');
    });
    drop.addEventListener('drop', function (e) {
      e.preventDefault();
      drop.classList.remove('over');
      var iso = e.dataTransfer.getData('text/plain');
      add(iso);
    });
  }

  function add(iso) {
    if (!iso || !SER[iso] || st.list.indexOf(iso) >= 0) return;
    if (st.list.length >= MAX) { toast('最多对比 ' + MAX + ' 个国家'); return; }
    st.list.push(iso);
    renderChips();
    renderList();
  }

  function remove(iso) {
    var i = st.list.indexOf(iso);
    if (i < 0) return;
    st.list.splice(i, 1);
    renderChips();
    renderList();
  }

  function renderChips() {
    var drop = el.querySelector('#pcmpDrop');
    if (!drop) return;
    if (!st.list.length) {
      drop.classList.remove('full');
      drop.innerHTML = '<div class="pcmp-ph">' +
        '<svg viewBox="0 0 24 24"><path d="M12 3v12M7 11l5 5 5-5M4 20h16"/></svg>' +
        '<span>把国家拖进这里</span><em>最多 ' + MAX + ' 个 · 也可以点下面的国家</em></div>';
    } else {
      drop.classList.add('full');
      drop.innerHTML = st.list.map(function (k) {
        return '<span class="chip" data-k="' + k + '">' +
          '<i style="background:' + color(k) + '"></i>' +
          (IDX[k].iso2 && FLAGS[k] ? '<img src="' + FLAGS[k] + '" alt="">' : '') +
          '<span>' + IDX[k].zh + '</span>' +
          '<button data-rm="' + k + '" aria-label="移除">×</button></span>';
      }).join('');
    }
    var go = el.querySelector('#pcmpGo');
    if (go) {
      go.disabled = st.list.length < 2;
      go.textContent = st.list.length < 2
        ? (st.list.length ? '再选一个' : '至少选两个国家')
        : '生成对比图 · ' + st.list.length + ' 个国家';
    }
  }

  function renderList() {
    var box = el.querySelector('#pcmpList');
    if (!box) return;
    var yi = curYi(), metric = curMetric();
    var v = (st.q || '').toLowerCase(), rows;
    if (v) {
      rows = [];
      for (var k in IDX) {
        var m = IDX[k];
        if (m.zh.toLowerCase().indexOf(v) >= 0 ||
            (m.en || '').toLowerCase().indexOf(v) >= 0 ||
            k.toLowerCase().indexOf(v) === 0) rows.push(k);
      }
      rows.sort(function (a, b) { return (val(b, metric, yi) || -1) - (val(a, metric, yi) || -1); });
      rows = rows.slice(0, 24);
    } else {
      rows = Object.keys(SER).filter(function (k) {
        return val(k, metric, yi) != null && IDX[k] && !IDX[k].na;
      }).sort(function (a, b) {
        return (val(b, metric, yi) || 0) - (val(a, metric, yi) || 0);
      }).slice(0, 16);
    }
    if (!rows.length) {
      box.innerHTML = '<div class="pcmp-ph" style="padding:16px 0"><span>没有匹配的国家</span></div>';
      return;
    }
    box.innerHTML = rows.map(function (k) {
      var used = st.list.indexOf(k) >= 0;
      return '<div class="crow' + (used ? ' used' : '') + '" draggable="true" data-k="' + k + '">' +
        '<span class="grip"><svg viewBox="0 0 24 24"><circle cx="9" cy="6" r="1.4"/><circle cx="9" cy="12" r="1.4"/>' +
        '<circle cx="9" cy="18" r="1.4"/><circle cx="15" cy="6" r="1.4"/><circle cx="15" cy="12" r="1.4"/>' +
        '<circle cx="15" cy="18" r="1.4"/></svg></span>' +
        (IDX[k].iso2 && FLAGS[k] ? '<img src="' + FLAGS[k] + '" alt="">' : '<span style="width:18px"></span>') +
        '<span class="n">' + IDX[k].zh + '</span>' +
        '<span class="v">' + fmt(metric, val(k, metric, yi)) + '</span>' +
        '<span class="add">+</span></div>';
    }).join('');

    Array.prototype.forEach.call(box.querySelectorAll('.crow'), function (row) {
      var k = row.getAttribute('data-k');
      row.addEventListener('dragstart', function (e) {
        try {
          e.dataTransfer.setData('text/plain', k);
          e.dataTransfer.effectAllowed = 'copy';
        } catch (x) {}
        row.classList.add('drag');
      });
      row.addEventListener('dragend', function () { row.classList.remove('drag'); });
    });
  }

  /* ---------- 结果 ---------- */
  var METRICS = [
    { id: 'gdp', label: 'GDP', note: '总量' },
    { id: 'gdppc', label: '人均 GDP', note: '每人每年' },
    { id: 'pop', label: '人口', note: '总人口' },
    { id: 'life', label: '预期寿命', note: '出生时' }
  ];

  function renderResult() {
    var yi = curYi(), isos = st.list.slice();
    var legend = isos.map(function (k) {
      return '<span class="cl"><i style="background:' + color(k) + '"></i><b>' + IDX[k].zh + '</b></span>';
    }).join('');

    var rows = METRICS.map(function (m) {
      var vals = isos.map(function (k) { return val(k, m.id, yi); });
      var mx = 0;
      vals.forEach(function (x) { if (x != null && x > mx) mx = x; });
      if (!mx) mx = 1;
      var top = vals.indexOf(mx);
      return '<div class="cmrow"><div class="h"><span>' + m.label + '</span><em>' + m.note + ' · ' + YEARS[yi] + '</em></div>' +
        isos.map(function (k, i) {
          var v = vals[i];
          var pct = v == null ? 0 : Math.max(1.5, v / mx * 100);
          return '<div class="cmb' + (i === top ? ' top' : '') + '">' +
            '<span class="nm">' + IDX[k].zh + '</span>' +
            '<span class="tr"><i style="width:' + pct.toFixed(1) + '%;background:' + color(k) + '"></i></span>' +
            '<span class="vv">' + fmt(m.id, v) + '</span></div>';
        }).join('') + '</div>';
    }).join('');

    var metric = curMetric(), gv = isos.map(function (k) {
      return { k: k, v: val(k, metric, yi) };
    }).filter(function (x) { return x.v != null; });
    gv.sort(function (a, b) { return b.v - a.v; });
    var insight = '';
    if (gv.length >= 2) {
      var r = gv[0].v / gv[gv.length - 1].v;
      var mname = { gdp: 'GDP', gdppc: '人均 GDP', pop: '人口', life: '预期寿命' }[metric];
      insight = mname + ' 最高的是 <b>' + IDX[gv[0].k].zh + '</b>，是 <b>' + IDX[gv[gv.length - 1].k].zh +
        '</b> 的 <b>' + (r >= 10 ? r.toFixed(0) : r.toFixed(1)) + ' 倍</b>。';
    }

    el.innerHTML =
      '<div class="pcmp-head">' +
        '<button class="pcmp-ico back" data-act="back" aria-label="返回">‹</button>' +
        '<div><div class="k">Result</div><h2>' + isos.length + ' 个国家，放在一起看</h2>' +
        '<div class="sub">' + YEARS[yi] + ' 年 · 世界银行 WDI</div></div>' +
        '<button class="pcmp-ico" data-act="close" aria-label="关闭">✕</button>' +
      '</div>' +
      '<div class="pcmp-body">' +
        '<div class="pcmp-legend">' + legend + '</div>' +
        rows +
        '<div class="cmrow"><div class="h"><span>GDP 走势</span><em>对数刻度 · 2000–' + YEARS[N - 1] + '</em></div>' +
          '<div class="pcmp-trend" id="pcmpTrend"></div></div>' +
        '<div class="pcmp-note">' + insight + ' 指标随底部指标条切换，这里的数字会一起变。</div>' +
      '</div>' +
      '<div class="pcmp-foot"><button class="pcmp-go ghost" data-act="back">重新选择国家</button>' +
        '<button class="pcmp-go" data-act="snap">存为图片</button></div>';

    requestAnimationFrame(function () { drawTrend(document.getElementById('pcmpTrend'), isos, yi); });
  }

  function drawTrend(target, isos, yi) {
    if (!target) return;
    var w = target.clientWidth || 380, h = 112;
    var pad = { t: 8, r: 6, b: 20, l: 58 };
    var iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
    var lo = Infinity, hi = 0;
    isos.forEach(function (k) {
      (SER[k].gdp || []).forEach(function (v) { if (v > 0) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
    });
    if (!isFinite(lo) || !hi) { target.innerHTML = '<div class="pcmp-note">该年无数据</div>'; return; }

    var x = function (i) { return pad.l + i / (N - 1) * iw; };
    var y = function (v) { return pad.t + ih - (Math.log10(v) - Math.log10(lo * 0.72)) /
      (Math.log10(hi * 1.3) - Math.log10(lo * 0.72)) * ih; };

    var svg = '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" preserveAspectRatio="xMidYMid meet">';
    var p0 = Math.ceil(Math.log10(lo * 0.72)), p1 = Math.floor(Math.log10(hi * 1.3));
    for (var p = p0; p <= p1; p++) {
      var vv = Math.pow(10, p);
      if (vv < lo * 0.72 || vv > hi * 1.3) continue;
      var yy = y(vv);
      svg += '<line x1="' + pad.l + '" x2="' + (pad.l + iw) + '" y1="' + yy.toFixed(1) + '" y2="' + yy.toFixed(1) +
        '" stroke="rgba(150,185,215,.10)" stroke-width="1"/>';
      svg += '<text x="' + (pad.l - 6) + '" y="' + (yy + 3).toFixed(1) + '" text-anchor="end" font-size="8.5" fill="#71869b">' +
        axisMoney(vv) + '</text>';
    }
    isos.forEach(function (k) {
      var d = '', pen = false;
      for (var i = 0; i < N; i++) {
        var g = val(k, 'gdp', i);
        if (g == null || g <= 0) { pen = false; continue; }
        d += (pen ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(g).toFixed(1) + ' ';
        pen = true;
      }
      svg += '<path d="' + d + '" fill="none" stroke="' + color(k) + '" stroke-width="1.8" ' +
        'stroke-linejoin="round" stroke-linecap="round"/>';
      var cur = val(k, 'gdp', yi);
      if (cur) svg += '<circle cx="' + x(yi).toFixed(1) + '" cy="' + y(cur).toFixed(1) +
        '" r="3" fill="#0b131b" stroke="' + color(k) + '" stroke-width="1.8"/>';
    });
    [0, 10, 20, N - 1].forEach(function (i) {
      svg += '<text x="' + x(i).toFixed(1) + '" y="' + (h - 4) + '" text-anchor="' +
        (i === 0 ? 'start' : (i === N - 1 ? 'end' : 'middle')) + '" font-size="9" fill="#71869b">' + YEARS[i] + '</text>';
    });
    svg += '</svg>';
    target.innerHTML = svg;
  }

  /* ---------- 存为图片（1080×1440） ---------- */
  function snap() {
    var yi = curYi(), isos = st.list.slice();
    var W = 1080, H = 1440, M = 72;
    var FONT = '-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif';
    var cv = document.createElement('canvas');
    cv.width = W; cv.height = H;
    var ctx = cv.getContext('2d');

    var bg = ctx.createLinearGradient(0, 0, W * 0.4, H);
    bg.addColorStop(0, '#12212e'); bg.addColorStop(0.55, '#0b1620'); bg.addColorStop(1, '#060a0f');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    var glow = ctx.createRadialGradient(W * 0.5, 150, 40, W * 0.5, 210, 760);
    glow.addColorStop(0, 'rgba(70,140,185,.30)'); glow.addColorStop(1, 'rgba(70,140,185,0)');
    ctx.fillStyle = glow; ctx.fillRect(0, 0, W, 760);

    /* 品牌行 */
    ctx.fillStyle = '#eaf3fa';
    ctx.font = '700 34px ' + FONT;
    ctx.fillText('ORBIS', M, 104);
    ctx.fillStyle = 'rgba(157,178,198,.72)';
    ctx.font = '400 17px ' + FONT;
    ctx.fillText('从太空看地球 · 国家对比', M, 136);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#e8a34a';
    ctx.font = '600 20px ' + FONT;
    ctx.fillText(YEARS[yi] + ' 年', W - M, 104);
    ctx.fillStyle = 'rgba(157,178,198,.55)';
    ctx.font = '400 15px ' + FONT;
    ctx.fillText('世界银行 WDI', W - M, 130);
    ctx.textAlign = 'left';
    ctx.strokeStyle = 'rgba(150,185,215,.18)';
    ctx.beginPath(); ctx.moveTo(M, 176); ctx.lineTo(W - M, 176); ctx.stroke();

    /* 标题 */
    ctx.fillStyle = '#fff';
    ctx.font = '700 52px ' + FONT;
    ctx.fillText(isos.length + ' 个国家，放在一起看', M, 262);

    /* 图例 */
    var lx = M, ly = 306;
    isos.forEach(function (k) {
      ctx.fillStyle = color(k);
      ctx.fillRect(lx, ly - 13, 12, 12);
      ctx.fillStyle = 'rgba(233,242,248,.88)';
      ctx.font = '400 20px ' + FONT;
      ctx.fillText(IDX[k].zh, lx + 19, ly);
      lx += 19 + ctx.measureText(IDX[k].zh).width + 28;
    });

    /* 版式：先算行高，保证 6 国也放得下 */
    var top = 370, footY = H - 128;
    var trendH = isos.length <= 4 ? 210 : 0;
    var avail = footY - top - trendH - 34;
    var labelH = 30;
    var rowH = Math.min(54, Math.max(22,
      (avail - labelH * METRICS.length - 16 * METRICS.length) / (METRICS.length * isos.length)));

    var y = top;
    var barX = M + 168, barMax = 620, valX = W - M;
    METRICS.forEach(function (m) {
      var vals = isos.map(function (k) { return val(k, m.id, yi); });
      var mx = 0;
      vals.forEach(function (v) { if (v != null && v > mx) mx = v; });
      if (!mx) mx = 1;

      ctx.fillStyle = 'rgba(157,178,198,.62)';
      ctx.font = '600 16px ' + FONT;
      ctx.fillText(m.label, M, y + 15);
      ctx.textAlign = 'right';
      ctx.fillStyle = 'rgba(157,178,198,.45)';
      ctx.font = '400 15px ' + FONT;
      ctx.fillText(m.note + ' · ' + YEARS[yi], valX, y + 15);
      ctx.textAlign = 'left';
      y += labelH;

      isos.forEach(function (k, i) {
        var v = vals[i];
        var cy = y + rowH / 2;
        ctx.fillStyle = 'rgba(233,242,248,.86)';
        ctx.font = '400 18px ' + FONT;
        ctx.fillText(IDX[k].zh, M, cy + 6);

        ctx.fillStyle = 'rgba(255,255,255,.07)';
        ctx.fillRect(barX, cy - 7, barMax, 14);
        if (v != null) {
          var bw = Math.max(3, v / mx * barMax);
          ctx.fillStyle = CMPC[i % CMPC.length];
          ctx.fillRect(barX, cy - 7, bw, 14);
        }
        ctx.textAlign = 'right';
        ctx.fillStyle = '#e9f2f8';
        ctx.font = '500 18px ' + FONT;
        ctx.fillText(fmt(m.id, v), valX, cy + 6);
        ctx.textAlign = 'left';
        y += rowH;
      });
      y += 16;
    });

    /* GDP 走势（对数刻度），国家多时让位给条形 */
    if (trendH) {
      var ty = footY - trendH + 6, th = trendH - 46;
      var tx = M + 78, tw = W - M - tx;
      var lo = Infinity, hi = 0;
      isos.forEach(function (k) {
        (SER[k].gdp || []).forEach(function (v) { if (v > 0) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
      });
      if (isFinite(lo) && hi) {
        var lg = function (v) { return Math.log10(v); };
        var y0 = lg(lo * 0.72), y1 = lg(hi * 1.3);
        var px = function (i) { return tx + i / (N - 1) * tw; };
        var py = function (v) { return ty + th - (lg(v) - y0) / (y1 - y0) * th; };

        ctx.fillStyle = 'rgba(157,178,198,.62)';
        ctx.font = '600 16px ' + FONT;
        ctx.fillText('GDP 走势', M, ty - 12);
        ctx.fillStyle = 'rgba(157,178,198,.45)';
        ctx.font = '400 15px ' + FONT;
        ctx.fillText('对数刻度 · 2000–' + YEARS[N - 1], M, ty + 10);

        for (var p = Math.ceil(y0); p <= Math.floor(y1); p++) {
          var vv = Math.pow(10, p);
          if (vv < lo * 0.72 || vv > hi * 1.3) continue;
          var yy = py(vv);
          ctx.strokeStyle = 'rgba(150,185,215,.10)';
          ctx.beginPath(); ctx.moveTo(tx, yy); ctx.lineTo(tx + tw, yy); ctx.stroke();
          ctx.textAlign = 'right';
          ctx.fillStyle = 'rgba(157,178,198,.55)';
          ctx.font = '400 14px ' + FONT;
          ctx.fillText(axisMoney(vv), tx - 8, yy + 4);
          ctx.textAlign = 'left';
        }
        isos.forEach(function (k, i) {
          ctx.strokeStyle = CMPC[i % CMPC.length];
          ctx.lineWidth = 3; ctx.lineJoin = 'round';
          ctx.beginPath();
          var pen = false;
          for (var j = 0; j < N; j++) {
            var g = val(k, 'gdp', j);
            if (g == null || g <= 0) { pen = false; continue; }
            if (!pen) { ctx.moveTo(px(j), py(g)); pen = true; } else ctx.lineTo(px(j), py(g));
          }
          ctx.stroke();
          var cur = val(k, 'gdp', yi);
          if (cur) {
            ctx.fillStyle = '#0b131b';
            ctx.beginPath(); ctx.arc(px(yi), py(cur), 5, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = CMPC[i % CMPC.length]; ctx.lineWidth = 2.5; ctx.stroke();
          }
          ctx.lineWidth = 1;
        });
        ctx.fillStyle = 'rgba(157,178,198,.5)';
        ctx.font = '400 14px ' + FONT;
        ctx.fillText(String(YEARS[0]), tx, ty + th + 22);
        ctx.textAlign = 'right';
        ctx.fillText(String(YEARS[N - 1]), tx + tw, ty + th + 22);
        ctx.textAlign = 'left';
      }
    }

    /* 页脚 */
    ctx.strokeStyle = 'rgba(150,185,215,.16)';
    ctx.beginPath(); ctx.moveTo(M, footY); ctx.lineTo(W - M, footY); ctx.stroke();
    ctx.fillStyle = 'rgba(157,178,198,.6)';
    ctx.font = '400 17px ' + FONT;
    ctx.fillText('数据来源 · 世界银行 WDI · ' + YEARS[yi], M, footY + 44);
    ctx.textAlign = 'right';
    ctx.fillText('ORBIS · 从太空看地球', W - M, footY + 44);
    ctx.textAlign = 'left';

    openModal(cv, '对比-' + isos.join('_') + '-' + YEARS[yi]);
  }

  function openModal(cv, name) {
    var box = document.getElementById('psnap');
    if (!box) {
      box = document.createElement('div');
      box.id = 'psnap';
      box.innerHTML = '<div class="box"><img alt="对比图">' +
        '<div class="row"><button class="pri">下载图片</button><button class="cls">关闭</button></div>' +
        '<div class="note">1080 × 1440 · 直接发微信 / 贴文档都能看清</div></div>';
      document.body.appendChild(box);
      box.addEventListener('click', function (e) {
        if (e.target === box || e.target.classList.contains('cls')) box.classList.remove('on');
      });
    }
    var url = cv.toDataURL('image/png');
    box.querySelector('img').src = url;
    box.querySelector('.pri').onclick = function () {
      var a = document.createElement('a');
      a.href = url;
      a.download = 'ORBIS-' + name + '.png';
      document.body.appendChild(a); a.click(); a.remove();
    };
    box.classList.add('on');
  }

  /* ---------- 事件 ---------- */
  function onClick(e) {
    var t = e.target;
    var act = t.closest && t.closest('[data-act]');
    if (act && el.contains(act)) {
      var a = act.getAttribute('data-act');
      if (a === 'close') close();
      else if (a === 'back') { st.view = 'pick'; render(); }
      else if (a === 'snap') snap();
      return;
    }
    var rm = t.closest && t.closest('[data-rm]');
    if (rm && el.contains(rm)) { remove(rm.getAttribute('data-rm')); return; }
    var go = t.closest && t.closest('#pcmpGo');
    if (go && !go.disabled) {
      if (st.list.length < 2) { toast('至少选两个国家'); return; }
      st.view = 'result';
      render();
      return;
    }
    var row = t.closest && t.closest('.crow');
    if (row && el.contains(row) && !t.closest('[data-rm]')) add(row.getAttribute('data-k'));
  }

  window.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && st.open) close();
  });

  /* 搭档那颗「＋ 加入对比」也接到这里：捕获阶段拦下来，就不进他那一套 */
  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    var b = e.target.closest('#cadd');
    if (!b) return;
    if (document.body.classList.contains('plan-free')) return;   /* 基础版由门控层处理 */
    e.preventDefault();
    e.stopPropagation();
    var m = /^#\/c\/([A-Za-z]{3})/.exec(location.hash || '');
    open(m ? m[1].toUpperCase() : null);
  }, true);

  /* ---------- 地球页上的入口 ----------
     对比原来只在「国家面板 / 档案卡」里，站在地球这一层根本找不到。
     直接把按钮插进搭档右侧那根工具条，样式跟「洲别」一致，不另起一套。 */
  function mountEntry() {
    var zoom = document.getElementById('zoom');
    if (!zoom || document.getElementById('pcmpEntry')) return;
    var b = document.createElement('button');
    b.id = 'pcmpEntry';
    b.className = 'pol';
    b.title = '把国家拖进盒子，做数据对比';
    b.textContent = '对比';
    var sep = document.createElement('div');
    sep.className = 'sep';
    zoom.insertBefore(sep, zoom.firstChild);
    zoom.insertBefore(b, sep);
    b.addEventListener('click', function () {
      if (document.body.classList.contains('plan-free')) { toast('多国对比属于完整版'); return; }
      var m = /^#\/c\/([A-Za-z]{3})/.exec(location.hash || '');
      open(m ? m[1].toUpperCase() : null);
    });
  }
  mountEntry();

  window.__PCMP__ = {
    open: open,
    close: close,
    toggle: toggle,
    add: add,
    isOpen: function () { return st.open; }
  };
})();
