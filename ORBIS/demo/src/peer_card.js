/* ============================================================
   国家档案卡（右侧） —— 把 Atlas 的国家卡片接到搭档那版地球上
   ------------------------------------------------------------
   为什么不改搭档的代码：
     他的主逻辑压缩过，而且已经有自己的左下面板（加入对比 / 城市列表）。
     这张卡是「加一层」，只读他的 hash 路由（#/c/RUS）、顶部指标条（#dchips）
     和年份（#dyr），不碰他任何一行渲染逻辑。

   数据从哪来：
     build/card_data.js（由 build/mk_carddata.py 生成）
     26 年 × 10 指标 + 全球合计 + 国旗 + 陆地邻国
   ============================================================ */
(function () {
  'use strict';
  var D = window.__PCARD__;
  if (!D) return;

  var YEARS = D.years, IDX = D.index, SER = D.series, WLD = D.wld;
  var FLAGS = D.flags || {}, NEI = D.nei || {}, SUB = D.sub || {};
  var N = YEARS.length;
  var MET_NAME = { gdp: 'GDP', gdppc: '人均 GDP', pop: '人口', life: '预期寿命' };

  /* 提示条复用方案外壳那一颗；没有外壳时自己兜一个 */
  function toast(msg) {
    if (typeof window.__pshellToast === 'function') { window.__pshellToast(msg); return; }
    var el = document.querySelector('.pshell-toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'pshell-toast';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add('on');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.classList.remove('on'); }, 2100);
  }

  /* ------------------------------------------------------------
     格式化
     ------------------------------------------------------------ */
  function moneyParts(v) {
    if (v == null) return { n: '—', u: '' };
    if (v >= 1e12) return { n: (v / 1e12).toFixed(v >= 1e13 ? 1 : 2), u: '万亿' };
    if (v >= 1e8) return { n: Math.round(v / 1e8).toLocaleString('en-US'), u: '亿' };
    if (v >= 1e4) return { n: Math.round(v / 1e4), u: '万' };
    return { n: Math.round(v).toString(), u: '' };
  }
  function popParts(v) {
    if (v == null) return { n: '—', u: '' };
    if (v >= 1e8) return { n: (v / 1e8).toFixed(2), u: '亿' };
    if (v >= 1e4) return { n: Math.round(v / 1e4), u: '万' };
    return { n: Math.round(v).toString(), u: '' };
  }
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
  function partsFn(m, v) {
    return m === 'pop' ? popParts(v) : m === 'life'
      ? (v == null ? { n: '—', u: '' } : { n: v.toFixed(1), u: '岁' })
      : moneyParts(v);
  }
  function fullFn(m, v) {
    if (m === 'pop') return popFull(v);
    if (m === 'life') return v == null ? '—' : v.toFixed(1) + ' 岁';
    return moneyFull(v);
  }
  function val(iso, m, yi) {
    var s = SER[iso];
    if (!s || !s[m]) return null;
    return s[m][yi];
  }

  /* ------------------------------------------------------------
     排名 / 全球年龄结构
     ------------------------------------------------------------ */
  var RC = {};
  function rankMap(m, yi) {
    var key = m + '|' + yi;
    if (RC[key]) return RC[key];
    var arr = [];
    for (var k in SER) {
      var v = val(k, m, yi);
      if (v != null) arr.push([k, v]);
    }
    arr.sort(function (a, b) { return b[1] - a[1]; });
    var map = new Map();
    arr.forEach(function (d, i) { map.set(d[0], i + 1); });
    map.count = arr.length;
    RC[key] = map;
    return map;
  }

  var WORLD_AGE = YEARS.map(function (y, yi) {
    var s14 = 0, s65 = 0, sp = 0;
    for (var k in SER) {
      var s = SER[k], p = s.pop ? s.pop[yi] : null;
      if (!p || s.g14 == null) continue;
      s14 += p * s.g14; s65 += p * s.g65; sp += p;
    }
    return sp ? { g14: s14 / sp, g65: s65 / sp } : { g14: 25, g65: 10 };
  });

  /* ------------------------------------------------------------
     洞察两句话
     ------------------------------------------------------------ */
  function insightHTML(iso, yi) {
    var s = SER[iso], out = [];
    var gdp = val(iso, 'gdp', yi), gW = WLD.gdp[yi];
    var pc = val(iso, 'gdppc', yi), pcW = WLD.pc[yi];
    var lf = val(iso, 'life', yi), lfW = WLD.lp[yi];

    if (gdp != null && gW) {
      var r = rankMap('gdp', yi).get(iso), pct = gdp / gW * 100;
      var t = 'GDP 全球第 <b>' + r + '</b>，占全球 <b>' + (pct >= 1 ? pct.toFixed(1) : pct.toFixed(2)) + '%</b>';
      var ref = null;
      if (iso !== 'USA' && SER.USA && SER.USA.gdp[yi] && gdp < SER.USA.gdp[yi] * 0.92) ref = 'USA';
      else if (iso !== 'CHN' && SER.CHN && SER.CHN.gdp[yi]) ref = 'CHN';
      if (ref) {
        var ratio = gdp / SER[ref].gdp[yi];
        if (ratio >= 0.86 && ratio < 1.18) t += '，与' + IDX[ref].zh + '相当';
        else if (ratio > 0.04 && ratio < 0.86) t += '，约为' + IDX[ref].zh + '的 <b>1/' + Math.round(1 / ratio) + '</b>';
        else if (ratio >= 1.18 && ratio < 40) t += '，约为' + IDX[ref].zh + '的 <b>' + ratio.toFixed(1) + ' 倍</b>';
      }
      out.push(t + '。');
    }

    if (pc != null && pcW) {
      var k2 = pc / pcW;
      var t2 = k2 >= 1.06 ? '人均 GDP 是全球均值的 <b>' + k2.toFixed(1) + ' 倍</b>'
        : k2 <= 0.94 ? '人均 GDP 仅为全球均值的 <b>' + Math.round(k2 * 100) + '%</b>'
        : '人均 GDP 与全球均值持平';
      if (lf != null && lfW != null) {
        t2 += '；预期寿命 <b>' + lf.toFixed(1) + '</b> 岁，' + (lf >= lfW ? '高' : '低') +
          '出 ' + Math.abs(lf - lfW).toFixed(1) + ' 年。';
      } else t2 += '。';
      out.push(t2);
    }
    return out.map(function (t) { return '<span class="q">' + t + '</span>'; }).join('');
  }

  /* ------------------------------------------------------------
     GDP 走势（纯 SVG，不依赖 d3）
     ------------------------------------------------------------ */
  function sparkPath(pts) {
    var d = '', pen = false;
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      if (p == null) { pen = false; continue; }
      d += (pen ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ' ';
      pen = true;
    }
    return d;
  }

  function drawTrend(el, iso, yi) {
    if (!el) return;
    var s = SER[iso], W = el.clientWidth || 356, H = 108;
    var pad = { t: 10, r: 4, b: 18, l: 2 };
    var iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;

    var act = [], imp = [], mx = 0;
    for (var i = 0; i < N; i++) {
      var g = val(iso, 'gdp', i);
      var p = val(iso, 'pop', i);
      var pcW = WLD.pc[i];
      var im = (pcW != null && p != null) ? pcW * p : null;
      act.push(g); imp.push(im);
      if (g != null && g > mx) mx = g;
      if (im != null && im > mx) mx = im;
    }
    if (!mx) { el.innerHTML = '<div class="pc-cap" style="margin:0">该年无数据</div>'; return; }

    var x = function (i) { return pad.l + i / (N - 1) * iw; };
    var y = function (v) { return pad.t + ih - v / (mx * 1.12) * ih; };

    var actPts = act.map(function (v, i) { return v == null ? null : [x(i), y(v)]; });
    var impPts = imp.map(function (v, i) { return v == null ? null : [x(i), y(v)]; });

    var area = '';
    var first = null, last = null;
    actPts.forEach(function (p, i) { if (p) { if (!first) first = i; last = i; } });
    if (first != null) {
      area = 'M' + x(first).toFixed(1) + ' ' + (pad.t + ih).toFixed(1) + ' ';
      for (var j = first; j <= last; j++) if (actPts[j]) area += 'L' + actPts[j][0].toFixed(1) + ' ' + actPts[j][1].toFixed(1) + ' ';
      area += 'L' + x(last).toFixed(1) + ' ' + (pad.t + ih).toFixed(1) + ' Z';
    }

    var gid = 'pcg' + iso;
    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" preserveAspectRatio="xMidYMid meet">' +
      '<defs><linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="#6fb4d8" stop-opacity=".17"/>' +
      '<stop offset="100%" stop-color="#6fb4d8" stop-opacity="0"/></linearGradient></defs>' +
      '<path d="' + area + '" fill="url(#' + gid + ')"/>' +
      '<path d="' + sparkPath(impPts) + '" fill="none" stroke="rgba(157,178,198,.75)" stroke-width="1.25" stroke-dasharray="3 3"/>' +
      '<path d="' + sparkPath(actPts) + '" fill="none" stroke="#6fb4d8" stroke-width="1.7" stroke-linejoin="round"/>';

    svg += '<line x1="' + x(yi).toFixed(1) + '" x2="' + x(yi).toFixed(1) + '" y1="' + pad.t + '" y2="' + (pad.t + ih) +
      '" stroke="rgba(180,210,235,.28)" stroke-width="1"/>';
    if (act[yi] != null) {
      svg += '<circle cx="' + x(yi).toFixed(1) + '" cy="' + y(act[yi]).toFixed(1) +
        '" r="3.1" fill="#0e1822" stroke="#6fb4d8" stroke-width="1.8"/>';
    }

    [0, 10, 20, N - 1].forEach(function (i) {
      var anchor = i === 0 ? 'start' : (i === N - 1 ? 'end' : 'middle');
      svg += '<text x="' + x(i).toFixed(1) + '" y="' + (H - 1) + '" text-anchor="' + anchor +
        '" font-size="9" fill="rgba(157,178,198,.8)">' + YEARS[i] + '</text>';
    });
    svg += '</svg>';
    el.innerHTML = svg;
  }

  /* ------------------------------------------------------------
     人口结构
     ------------------------------------------------------------ */
  function drawAge(el, iso, yi) {
    if (!el) return;
    var s = SER[iso];
    if (s.g14 == null || s.g65 == null) {
      el.innerHTML = '<div class="pc-cap" style="margin:0">该年无人口结构数据</div>';
      return;
    }
    var a = s.g14, b = s.g65, c = Math.max(0, 100 - a - b);
    var W = WORLD_AGE[yi] || { g14: 25, g65: 10 };
    var cols = ['#c3d8e2', '#7fa8bb', '#2b6b87'];
    /* 占比太小的段放不下字，直接留白，别把数字挤成一条线 */
    var lbl = function (v) { return v >= 7 ? v.toFixed(0) + '%' : ''; };
    el.innerHTML =
      '<div class="pc-age">' +
        '<div style="flex:' + a + ' 1 0;background:' + cols[0] + ';color:#2b5064">' + lbl(a) + '</div>' +
        '<div style="flex:' + c + ' 1 0;background:' + cols[1] + '">' + lbl(c) + '</div>' +
        '<div style="flex:' + b + ' 1 0;background:' + cols[2] + '">' + lbl(b) + '</div>' +
      '</div>' +
      '<div class="pc-age-legend">' +
        '<span><i style="background:' + cols[0] + '"></i>0–14 岁</span>' +
        '<span><i style="background:' + cols[1] + '"></i>15–64 岁</span>' +
        '<span><i style="background:' + cols[2] + '"></i>65 岁以上</span>' +
        '<span style="color:#93a0a9">全球 ' + W.g14.toFixed(0) + '／' +
          (100 - W.g14 - W.g65).toFixed(0) + '／' + W.g65.toFixed(0) + '</span>' +
      '</div>';
  }

  /* ------------------------------------------------------------
     全球位次
     ------------------------------------------------------------ */
  function drawRank(el, iso, yi, metric) {
    if (!el) return;
    var map = rankMap(metric, yi);
    var r = map.get(iso), total = map.count;
    if (!r) { el.innerHTML = '<div class="pc-cap" style="margin:0">该年无数据</div>'; return; }
    var p = total > 1 ? (r - 1) / (total - 1) : 0.5;
    var lbl = p < 0.13 ? 'left:0;transform:none'
      : p > 0.87 ? 'right:0;left:auto;transform:none'
      : 'left:' + (p * 100) + '%;transform:translateX(-50%)';
    el.innerHTML =
      '<div class="pc-rank">' +
        '<div class="you-l" style="' + lbl + '">第 ' + r + ' 位</div>' +
        '<div class="track"></div>' +
        '<div class="med" style="left:50%"></div>' +
        '<div class="you" style="left:' + (p * 100) + '%"></div>' +
        '<div class="ends"><span>1</span><span style="position:absolute;left:50%;transform:translateX(-50%)">中位</span><span>' + total + '</span></div>' +
      '</div>';
  }

  /* ------------------------------------------------------------
     邻国对照
     ------------------------------------------------------------ */
  function neighborsOf(iso, metric, yi) {
    var list = (NEI[iso] || []).filter(function (k) { return val(k, metric, yi) != null; });
    list.sort(function (a, b) { return val(b, metric, yi) - val(a, metric, yi); });
    list = list.slice(0, 3);
    var alt = false;
    if (list.length < 2) {
      alt = true;
      var reg = (IDX[iso] || {}).r, own = val(iso, metric, yi) || 1;
      list = Object.keys(SER).filter(function (k) {
        return k !== iso && IDX[k] && IDX[k].r === reg && val(k, metric, yi) != null;
      }).sort(function (a, b) {
        return Math.abs(Math.log((val(a, metric, yi) || 1) / own)) -
               Math.abs(Math.log((val(b, metric, yi) || 1) / own));
      }).slice(0, 3);
    }
    return { list: list, alt: alt };
  }

  function drawNeighbors(el, iso, yi, metric, go) {
    if (!el) return;
    var nb = neighborsOf(iso, metric, yi);
    var rows = [iso].concat(nb.list);
    var mx = 1;
    rows.forEach(function (k) { var v = val(k, metric, yi) || 0; if (v > mx) mx = v; });

    el.innerHTML = '<div class="pc-nb">' + rows.map(function (k) {
      var v = val(k, metric, yi), p = partsFn(metric, v);
      return '<div class="r' + (k === iso ? ' self' : '') + '" data-goto="' + k + '">' +
        '<span>' + IDX[k].zh + '</span>' +
        '<span class="bar"><span style="width:' + Math.max(2, (v || 0) / mx * 100) + '%"></span></span>' +
        '<span class="num">' + p.n + p.u + '</span></div>';
    }).join('') + '</div>' +
    (nb.alt ? '<div class="pc-cap">无陆地邻国 · 显示同区域相近经济体</div>' : '');

    Array.prototype.forEach.call(el.querySelectorAll('[data-goto]'), function (row) {
      row.addEventListener('click', function () {
        if (document.body.classList.contains('plan-free')) {
          toast('邻国跳转属于完整版');
          return;
        }
        var k = row.getAttribute('data-goto');
        if (k && k !== iso) location.hash = '#/c/' + k;
      });
    });
  }

  /* ------------------------------------------------------------
     完整指标表
     ------------------------------------------------------------ */
  function buildTable(el, iso) {
    if (!el) return;
    var s = SER[iso], cols = [0, 10, 20, N - 1];
    var row = function (label, fn) {
      return '<tr><td>' + label + '</td>' + cols.map(function (i) {
        return '<td>' + fn(i) + '</td>';
      }).join('') + '</tr>';
    };
    el.innerHTML = '<table><thead><tr><th>指标</th>' +
      cols.map(function (i) { return '<th>' + YEARS[i] + '</th>'; }).join('') +
      '</tr></thead><tbody>' +
      row('GDP', function (i) { return s.gdp[i] == null ? '—' : moneyFull(s.gdp[i]); }) +
      row('人均 GDP', function (i) { return s.gdppc[i] == null ? '—' : moneyFull(s.gdppc[i]); }) +
      row('人口', function (i) { return s.pop[i] == null ? '—' : popFull(s.pop[i]); }) +
      row('预期寿命', function (i) { return s.life[i] == null ? '—' : s.life[i].toFixed(1); }) +
      row('城市化率', function (i) { return i === N - 1 && s.urb != null ? s.urb.toFixed(0) + '%' : '—'; }) +
      row('GDP 增速', function (i) { return i === N - 1 && s.growth != null ? s.growth.toFixed(1) + '%' : '—'; }) +
      row('人均碳排', function (i) { return i === N - 1 && s.co2 != null ? s.co2.toFixed(1) + ' t' : '—'; }) +
      row('总和生育率', function (i) { return i === N - 1 && s.fert != null ? s.fert.toFixed(2) : '—'; }) +
      '</tbody></table>';
  }

  /* ------------------------------------------------------------
     卡片 DOM
     ------------------------------------------------------------ */
  var root, bodyEl, curIso = null, curYi = N - 2, curMetric = 'gdp', suppressed = null;

  function ensureRoot() {
    if (root) return root;
    root = document.createElement('aside');
    root.id = 'pcard';
    root.innerHTML =
      '<div class="pc-head">' +
        '<img class="flag" alt="">' +
        '<div class="pc-ttl"><div class="pc-nm"></div><div class="pc-meta"></div></div>' +
        '<button class="pc-cmp" title="把当前国家加入对比">对比</button>' +
        '<button class="pc-x" aria-label="关闭">✕</button>' +
      '</div>' +
      '<div class="pc-body"></div>' +
      '<div class="pc-actions"><button class="pc-snap">' +
        '<svg viewBox="0 0 24 24"><path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2.2l1.3-2h5l1.3 2h3.2A1.5 1.5 0 0 1 20 8.5v9A1.5 1.5 0 0 1 18.5 19h-13A1.5 1.5 0 0 1 4 17.5z"/>' +
        '<circle cx="12" cy="12.8" r="3.3"/></svg>' +
        '<span>生成分享名片</span><i>竖版 1080×1440</i></button></div>' +
      '<div class="pc-foot"><span class="pc-src"></span><span class="pc-reg"></span></div>';

    document.body.appendChild(root);
    bodyEl = root.querySelector('.pc-body');
    root.querySelector('.pc-x').addEventListener('click', function () {
      suppressed = curIso;
      hide();
    });
    /* 「＋ 对比」只是替用户点搭档那颗按钮（#cadd）：
       对比的选国 / 画图仍由他的逻辑负责，我们不复制一份 */
    /* 「对比」打开我们自己的对比盒子（把国家拖进去 → 生成对比图），
       不再借用搭档左下角那一套折线 */
    root.querySelector('.pc-cmp').addEventListener('click', function () {
      if (document.body.classList.contains('plan-free')) {
        toast('多国对比属于完整版');
        return;
      }
      if (window.__PCMP__ && curIso) { window.__PCMP__.open(curIso); return; }
      var add = document.getElementById('cadd');
      if (add) add.click();
    });
    root.querySelector('.pc-snap').addEventListener('click', function () {
      if (curIso) makeSnap(curIso, curYi);
    });
    return root;
  }

  function render(iso) {
    var m = IDX[iso], s = SER[iso], yi = curYi;
    if (!m || !s) { hide(); return; }
    ensureRoot();
    /* 拖时间轴时卡片会整块重绘，滚动位置得自己记住，否则每动一下就弹回顶部；
       换国家则应该回到顶部 */
    var keepScroll = (curIso === iso) ? bodyEl.scrollTop : 0;
    curIso = iso;

    var isNA = !!m.na;
    var gdp = s.gdp[yi], pc = s.gdppc[yi], pop = s.pop[yi];
    var gp = moneyParts(gdp), pp = popParts(pop);
    var cp = pc == null ? { n: '—', u: '' }
      : { n: pc >= 10000 ? Math.round(pc).toLocaleString('en-US') : String(Math.round(pc)), u: '' };
    var rG = rankMap('gdp', yi).get(iso), rTot = rankMap('gdp', yi).count;
    var rP = rankMap('pop', yi).get(iso);

    root.querySelector('.pc-nm').textContent = m.zh;
    var metaBits = m.na ? ['该地区无可用经济数据'] : [m.en, m.r, m.i].filter(Boolean);
    root.querySelector('.pc-meta').textContent = metaBits.join(' · ');
    var flagEl = root.querySelector('.flag');
    if (m.iso2 && FLAGS[iso]) { flagEl.src = FLAGS[iso]; flagEl.style.display = ''; }
    else flagEl.style.display = 'none';

    var stat = function (k, v, u, sub) {
      return '<div class="pc-stat"><div class="k">' + k + '</div>' +
        '<div class="v">' + v + '<u>' + (u || '') + '</u></div>' +
        '<div class="r">' + (sub || '') + '</div></div>';
    };
    var pcSub = '';
    if (pc && WLD.pc[yi]) {
      pcSub = pc / WLD.pc[yi] >= 1
        ? (pc / WLD.pc[yi]).toFixed(1) + '× 全球'
        : Math.round(pc / WLD.pc[yi] * 100) + '% 全球';
    }

    bodyEl.innerHTML = isNA
      ? '<div class="pc-insight" style="border-bottom:0"><span class="q">世界银行未提供该地区的可比数据。' +
        '地图上仍可看到它的位置——相邻国家的卡片会为它提供参照。</span></div>'
      : '<div class="pc-stats">' +
          stat('GDP', gp.n, gp.u, rG ? '全球第 ' + rG + ' / ' + rTot : '') +
          stat('人口', pp.n, pp.u, rP ? '全球第 ' + rP : '') +
          stat('人均 GDP', cp.n, cp.u, pcSub) +
        '</div>' +
        '<div class="pc-insight">' + insightHTML(iso, yi) + '</div>' +
        '<section class="pc-sec"><div class="pc-sec-h"><div class="pc-sec-t">GDP 走势</div>' +
          '<div class="pc-sec-n">虚线 = 按全球人均水平推算</div></div>' +
          '<div class="pc-sec-b" data-chart="trend"></div>' +
          '<div class="pc-cap"><i><em></em>实际 GDP</i><i class="dash"><em></em>世界平均水平</i></div></section>' +
        '<section class="pc-sec"><div class="pc-sec-h"><div class="pc-sec-t">人口结构</div>' +
          '<div class="pc-sec-n">' + (s.g14y || '') + '</div></div>' +
          '<div class="pc-sec-b" data-chart="age"></div></section>' +
        '<section class="pc-sec" data-pro="1"><div class="pc-sec-h"><div class="pc-sec-t">' +
          MET_NAME[curMetric] + ' · 全球位次<span class="lk">完整版</span></div>' +
          '<div class="pc-sec-n">' + YEARS[yi] + '</div></div>' +
          '<div class="pc-sec-b" data-chart="rank"></div></section>' +
        '<section class="pc-sec" data-pro="1"><div class="pc-sec-h"><div class="pc-sec-t">' +
          '邻国对照<span class="lk">完整版</span></div>' +
          '<div class="pc-sec-n">' + MET_NAME[curMetric] + '</div></div>' +
          '<div class="pc-sec-b" data-chart="nb"></div></section>' +
        '<div class="pc-more" data-pro="1"><button>完整指标表 ' +
          '<svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button>' +
          '<div class="tbl"></div></div>';

    root.querySelector('.pc-src').textContent = '世界银行 WDI · ' + YEARS[yi];
    root.querySelector('.pc-reg').textContent = m.r || '';

    if (!isNA) {
      drawTrend(bodyEl.querySelector('[data-chart="trend"]'), iso, yi);
      drawAge(bodyEl.querySelector('[data-chart="age"]'), iso, yi);
      drawRank(bodyEl.querySelector('[data-chart="rank"]'), iso, yi, curMetric);
      drawNeighbors(bodyEl.querySelector('[data-chart="nb"]'), iso, yi, curMetric, true);
      buildTable(bodyEl.querySelector('.tbl'), iso);
      var more = bodyEl.querySelector('.pc-more');
      more.querySelector('button').addEventListener('click', function () {
        if (document.body.classList.contains('plan-free')) {
          toast('完整指标表属于完整版');
          return;
        }
        more.classList.toggle('open');
      });
    }

    suppressed = null;
    root.classList.add('on');
    if (keepScroll) bodyEl.scrollTop = keepScroll;
  }

  function hide() {
    if (root) root.classList.remove('on');
    curIso = null;
  }

  /* ------------------------------------------------------------
     分享名片（Canvas 绘制，不依赖任何库）
     ------------------------------------------------------------ */
  var SNAP_W = 1080, SNAP_H = 1440;
  var FONT = '-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif';

  function wrapText(ctx, text, x, y, maxW, lh, maxLines) {
    /* 先切行、再画。原来是一边切一边画，行数超限时把「…」接到新起的那一行，
       结果图上多出一行孤零零的省略号（看起来像一个点）。 */
    var lines = [], line = '';
    for (var i = 0; i < text.length; i++) {
      var t = line + text[i];
      if (ctx.measureText(t).width > maxW && line) {
        lines.push(line);
        line = text[i];
      } else line = t;
    }
    if (line) lines.push(line);

    /* 标点不要单独占一行（句号被挤到下一行，看起来就是一个孤零零的点） */
    while (lines.length > 1 && /^[，。、；：·…\s]+$/.test(lines[lines.length - 1])) {
      lines[lines.length - 2] += lines.pop();
    }

    if (maxLines && lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      lines[maxLines - 1] = lines[maxLines - 1].replace(/[，、。；：\s]+$/, '') + '…';
    }
    for (var j = 0; j < lines.length; j++) ctx.fillText(lines[j], x, y + j * lh);
    return y + lines.length * lh;
  }

  function snapSentence(iso, yi) {
    var gdp = val(iso, 'gdp', yi), gW = WLD.gdp[yi];
    var pc = val(iso, 'gdppc', yi), pcW = WLD.pc[yi];
    var bits = [];
    if (gdp && gW) bits.push('GDP 占全球 ' + (gdp / gW * 100).toFixed(2) + '%');
    if (pc && pcW) {
      var k = pc / pcW;
      bits.push(k >= 1 ? '人均是全球均值的 ' + k.toFixed(1) + ' 倍'
        : '人均为全球均值的 ' + Math.round(k * 100) + '%');
    }
    var lf = val(iso, 'life', yi);
    if (lf != null && WLD.lp[yi]) bits.push('预期寿命 ' + lf.toFixed(1) + ' 岁');
    var r = rankMap('gdp', yi).get(iso);
    return (r ? '全球第 ' + r + ' 大经济体，' : '') + bits.join('，') + '。';
  }

  function makeSnap(iso, yi) {
    var m = IDX[iso], s = SER[iso];
    var cv = document.createElement('canvas');
    cv.width = SNAP_W; cv.height = SNAP_H;
    var ctx = cv.getContext('2d');

    var bg = ctx.createLinearGradient(0, 0, SNAP_W * .4, SNAP_H);
    bg.addColorStop(0, '#12212e'); bg.addColorStop(.55, '#0b1620'); bg.addColorStop(1, '#060a0f');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, SNAP_W, SNAP_H);

    var glow = ctx.createRadialGradient(SNAP_W * .5, 180, 40, SNAP_W * .5, 240, 760);
    glow.addColorStop(0, 'rgba(70,140,185,.30)'); glow.addColorStop(1, 'rgba(70,140,185,0)');
    ctx.fillStyle = glow; ctx.fillRect(0, 0, SNAP_W, 760);

    ctx.fillStyle = '#eaf3fa';
    ctx.font = '700 34px ' + FONT;
    ctx.letterSpacing = '10px';
    ctx.fillText('ORBIS', 72, 104);
    ctx.letterSpacing = '0px';
    ctx.fillStyle = 'rgba(198,216,232,.92)';
    ctx.font = '400 20px ' + FONT;
    ctx.fillText('从太空看地球 · 国家数据档案', 72, 136);

    ctx.textAlign = 'right';
    ctx.fillStyle = '#e8a34a';
    ctx.font = '600 20px ' + FONT;
    ctx.fillText(String(YEARS[yi]), SNAP_W - 72, 108);
    ctx.fillStyle = 'rgba(198,216,232,.85)';
    ctx.font = '400 17px ' + FONT;
    ctx.fillText('世界银行 WDI', SNAP_W - 72, 134);
    ctx.textAlign = 'left';

    ctx.strokeStyle = 'rgba(150,185,215,.18)';
    ctx.beginPath(); ctx.moveTo(72, 176); ctx.lineTo(SNAP_W - 72, 176); ctx.stroke();

    var img = FLAGS[iso] ? new Image() : null;
    var drawRest = function () {
      var y = 300;
      if (img && img.width) {
        ctx.save();
        ctx.beginPath();
        var r = 8, w = 96, h = 68, x0 = 72, y0 = y - 54;
        ctx.moveTo(x0 + r, y0);
        ctx.arcTo(x0 + w, y0, x0 + w, y0 + h, r);
        ctx.arcTo(x0 + w, y0 + h, x0, y0 + h, r);
        ctx.arcTo(x0, y0 + h, x0, y0, r);
        ctx.arcTo(x0, y0, x0 + w, y0, r);
        ctx.closePath();
        ctx.clip();
        ctx.drawImage(img, x0, y0, w, h);
        ctx.restore();
        ctx.strokeStyle = 'rgba(255,255,255,.2)';
        ctx.strokeRect(72, y - 54, w, h);
      }
      var nx = (img && img.width) ? 196 : 72;
      ctx.fillStyle = '#fff';
      ctx.font = '700 62px ' + FONT;
      ctx.fillText(m.zh, nx, y + 6);
      ctx.fillStyle = 'rgba(200,218,234,.92)';
      ctx.font = '400 22px ' + FONT;
      ctx.fillText([m.en, m.r, m.i].filter(Boolean).join(' · '), nx, y + 44);

      // 三个大数字
      y = 440;
      var gdp = val(iso, 'gdp', yi), pop = val(iso, 'pop', yi), pc = val(iso, 'gdppc', yi);
      var rG = rankMap('gdp', yi).get(iso), rTot = rankMap('gdp', yi).count;
      var cols = [
        { k: 'GDP', v: moneyFull(gdp), s: rG ? '全球第 ' + rG + ' / ' + rTot : '' },
        { k: '人口', v: popFull(pop), s: rankMap('pop', yi).get(iso) ? '全球第 ' + rankMap('pop', yi).get(iso) : '' },
        { k: '人均 GDP', v: pc == null ? '—' : '$' + Math.round(pc).toLocaleString('en-US'),
          s: (pc && WLD.pc[yi]) ? (pc / WLD.pc[yi]).toFixed(1) + '× 全球' : '' }
      ];
      var colW = (SNAP_W - 144) / 3;
      cols.forEach(function (c, i) {
        var x0 = 72 + i * colW;
        ctx.fillStyle = 'rgba(206,222,236,.95)';
        ctx.font = '500 21px ' + FONT;
        ctx.fillText(c.k, x0, y);
        ctx.fillStyle = '#fff';
        ctx.font = '700 44px ' + FONT;
        ctx.fillText(c.v, x0, y + 54);
        ctx.fillStyle = '#f2b76b';
        ctx.font = '500 21px ' + FONT;
        ctx.fillText(c.s, x0, y + 88);
      });

      // 洞察
      y = 600;
      ctx.fillStyle = '#f2f8fd';
      ctx.font = '400 30px ' + FONT;
      var endY = wrapText(ctx, snapSentence(iso, yi), 72, y, SNAP_W - 144, 40, 3);

      // 走势
      y = Math.max(endY + 50, 720);
      var w = SNAP_W - 144, h = 200;
      var mx = 0, pts = [];
      for (var i = 0; i < N; i++) {
        var g = val(iso, 'gdp', i);
        if (g != null && g > mx) mx = g;
      }
      for (i = 0; i < N; i++) {
        var gv = val(iso, 'gdp', i);
        pts.push(gv == null ? null : [72 + i / (N - 1) * w, y + h - gv / (mx * 1.1) * h]);
      }
      ctx.strokeStyle = 'rgba(150,185,215,.14)';
      ctx.beginPath(); ctx.moveTo(72, y + h); ctx.lineTo(72 + w, y + h); ctx.stroke();
      ctx.strokeStyle = '#6fb4d8';
      ctx.lineWidth = 3; ctx.lineJoin = 'round';
      ctx.beginPath();
      var pen = false;
      pts.forEach(function (p) {
        if (!p) { pen = false; return; }
        if (!pen) { ctx.moveTo(p[0], p[1]); pen = true; } else ctx.lineTo(p[0], p[1]);
      });
      ctx.stroke();
      ctx.lineWidth = 1;
      ctx.fillStyle = 'rgba(198,216,232,.88)';
      ctx.font = '400 20px ' + FONT;
      ctx.fillText(String(YEARS[0]), 72, y + h + 30);
      ctx.textAlign = 'right';
      ctx.fillText(String(YEARS[N - 1]), 72 + w, y + h + 30);
      ctx.textAlign = 'left';
      ctx.fillStyle = 'rgba(200,220,236,.9)';
      ctx.font = '400 21px ' + FONT;
      ctx.fillText('GDP 走势 · 实际值（现价美元）', 72, y - 18);

      // 人口结构
      y = y + h + 90;
      var g14 = s.g14, g65 = s.g65;
      if (g14 != null && g65 != null) {
        var mid = Math.max(0, 100 - g14 - g65);
        var segs = [
          { v: g14, c: '#c3d8e2', t: '#2b5064', l: '0–14 岁' },
          { v: mid, c: '#7fa8bb', t: '#fff', l: '15–64 岁' },
          { v: g65, c: '#2b6b87', t: '#fff', l: '65 岁以上' }
        ];
        ctx.fillStyle = 'rgba(200,220,236,.9)';
        ctx.font = '400 21px ' + FONT;
        ctx.fillText('人口结构', 72, y - 20);
        var sx = 72;
        segs.forEach(function (sg) {
          var sw = (SNAP_W - 144) * sg.v / 100 - 2;
          ctx.fillStyle = sg.c;
          ctx.fillRect(sx, y + 12, sw, 44);
          if (sg.v > 8) {
            ctx.fillStyle = sg.t;
            ctx.font = '700 22px ' + FONT;
            ctx.fillText(sg.v.toFixed(0) + '%', sx + 14, y + 41);
          }
          sx += sw + 2;
        });
        ctx.fillStyle = 'rgba(157,178,198,.62)';
        ctx.font = '400 16px ' + FONT;
        segs.forEach(function (sg, i2) {
          ctx.fillStyle = sg.c;
          ctx.fillRect(72 + i2 * 156, y + 84, 12, 12);
          ctx.fillStyle = 'rgba(206,222,236,.9)';
          ctx.font = '400 20px ' + FONT;
          ctx.fillText(sg.l, 72 + i2 * 156 + 20, y + 95);
        });
      }

      // 全球位次：卡片里最能说明"排第几"的一行，也顺带填掉下半部的空白
      var rmG = rankMap('gdp', yi), rmP = rankMap('gdppc', yi);
      var gRk = rmG.get(iso), pRk = rmP.get(iso);
      if (gRk || pRk) {
        var ry = Math.min(y + 132, SNAP_H - 232);
        ctx.fillStyle = 'rgba(206,222,236,.95)';
        ctx.font = '500 21px ' + FONT;
        ctx.fillText('全球位次', 72, ry);
        [{ k: 'GDP', v: gRk ? '第 ' + gRk + ' / ' + rmG.count : '—' },
         { k: '人均 GDP', v: pRk ? '第 ' + pRk + ' / ' + rmP.count : '—' }].forEach(function (c, i3) {
          var x3 = 72 + i3 * 300;
          ctx.fillStyle = 'rgba(200,220,236,.9)';
          ctx.font = '400 20px ' + FONT;
          ctx.fillText(c.k, x3, ry + 38);
          ctx.fillStyle = '#ffffff';
          ctx.font = '700 34px ' + FONT;
          ctx.fillText(c.v, x3, ry + 78);
        });
      }

      // 页脚
      ctx.strokeStyle = 'rgba(150,185,215,.16)';
      ctx.beginPath(); ctx.moveTo(72, SNAP_H - 128); ctx.lineTo(SNAP_W - 72, SNAP_H - 128); ctx.stroke();
      ctx.fillStyle = 'rgba(198,216,232,.85)';
      ctx.font = '400 20px ' + FONT;
      ctx.fillText('数据来源 · 世界银行 WDI', 72, SNAP_H - 86);
      ctx.textAlign = 'right';
      ctx.fillText('ORBIS · 从太空看地球', SNAP_W - 72, SNAP_H - 86);
      ctx.textAlign = 'left';

      openSnapModal(cv, m.zh + '-' + YEARS[yi]);
    };

    if (img) {
      img.onload = drawRest;
      img.onerror = function () { img = null; drawRest(); };
      img.src = FLAGS[iso];
    } else drawRest();
  }

  function openSnapModal(cv, name) {
    var box = document.getElementById('psnap');
    if (!box) {
      box = document.createElement('div');
      box.id = 'psnap';
      box.innerHTML = '<div class="box">' +
        '<img alt="分享名片">' +
        '<div class="row"><button class="pri">下载图片</button><button class="cls">关闭</button></div>' +
        '<div class="note">1080 × 1440 · 直接发微信 / 贴文档都能看清</div>' +
        '</div>';
      document.body.appendChild(box);
      box.addEventListener('click', function (e) {
        if (e.target === box || e.target.classList.contains('cls')) box.classList.remove('on');
      });
      window.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') box.classList.remove('on');
      });
    }
    var url = cv.toDataURL('image/png');
    box.querySelector('img').src = url;
    var dl = box.querySelector('.pri');
    dl.onclick = function () {
      var a = document.createElement('a');
      a.href = url;
      a.download = 'ORBIS-' + name + '.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    };
    box.classList.add('on');
  }

  /* ------------------------------------------------------------
     和搭档的界面同步：路由 / 年份 / 指标
     ------------------------------------------------------------ */
  function hashIso() {
    var m = /^#\/c\/([A-Za-z]{3})/.exec(location.hash || '');
    return m ? m[1].toUpperCase() : null;
  }

  function curYearIndex() {
    var el = document.getElementById('dyr');
    var y = el ? parseInt(String(el.textContent).replace(/[^\d]/g, ''), 10) : NaN;
    var i = YEARS.indexOf(y);
    return i < 0 ? N - 2 : i;
  }

  function curMetricNow() {
    var b = document.querySelector('#dchips button.on');
    var k = b && b.getAttribute('data-i');
    if (k === 'pc') return 'gdppc';
    if (k === 'le') return 'life';
    if (k === 'pop') return 'pop';
    return 'gdp';
  }

  function sync() {
    curYi = curYearIndex();
    curMetric = curMetricNow();
    var iso = hashIso();
    if (!iso) { hide(); return; }
    if (iso === suppressed) { hide(); return; }
    render(iso);
  }

  var rafT = 0;
  function syncLater() {
    cancelAnimationFrame(rafT);
    rafT = requestAnimationFrame(sync);
  }

  function boot() {
    ensureRoot();
    window.addEventListener('hashchange', function () { suppressed = null; syncLater(); });
    document.addEventListener('click', function (e) {
      if (!e.target.closest) return;
      if (e.target.closest('#dchips') || e.target.closest('#dplay')) syncLater();
      /* 手动关掉卡片后，再点球面 / 左侧面板就把它叫回来（同一个国家 hash 不会变） */
      if (suppressed && (e.target.id === 'globe' || e.target.closest('#country'))) suppressed = null;
    }, true);
    var dyr = document.getElementById('dyr');
    if (dyr) new MutationObserver(syncLater).observe(dyr, { childList: true, characterData: true, subtree: true });
    var dtl = document.getElementById('dtl');
    if (dtl) dtl.addEventListener('input', syncLater);
    var chips = document.getElementById('dchips');
    if (chips) new MutationObserver(syncLater).observe(chips, { attributes: true, subtree: true, attributeFilter: ['class'] });
    sync();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
