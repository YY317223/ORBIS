/* 一级界面右侧工具条：指南 / 对比
   国家面板左侧：新增「快照」（竖版 1080×1440 分享卡）
   ------------------------------------------------------------
   原页面是压缩代码，这里只做程序化触发，不改它一行：
     · 指南 → 点隐藏的 #guideBtn（原页面用它打开 #guide 抽屉）
     · 对比 → 点 #cmpadd（打开「添加国家到对比」选择面板）
     · 快照 → 点国家档案卡里的 .pc-snap（卡片本身已隐藏，只借用它的出图能力）
   侧栏档案卡已撤掉，避免和左侧面板信息重复。 */
(function () {
  function $(s) { return document.querySelector(s); }

  /* 工具条按钮统一按「两字标签」的样式做 */
  function mkBtn(id, label, title) {
    var b = document.createElement('button');
    b.id = id;
    b.className = 'pol';
    b.title = title;
    b.textContent = label;
    return b;
  }

  function toast(msg) {
    var el = document.querySelector('.pshell-toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'pshell-toast';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add('on');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.classList.remove('on'); }, 2000);
  }

  function mountToolbar() {
    var zoom = $('#zoom');
    if (!zoom || document.getElementById('uzGuide')) return;

    var guide = mkBtn('uzGuide', '指南', '完整功能使用指南');
    var cmp = mkBtn('uzCmp', '对比', '把国家加入对比（最多 4 个）');

    var sep = document.createElement('div');
    sep.className = 'sep';
    zoom.insertBefore(sep, zoom.firstChild);
    zoom.insertBefore(cmp, sep);
    zoom.insertBefore(guide, cmp);

    guide.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var b = document.getElementById('guideBtn');   /* 只是隐藏，仍可程序化点 */
      if (b) b.click();
    });

    cmp.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var add = document.getElementById('cmpadd') || document.getElementById('clist-add');
      if (add) add.click();
    });
  }

  /* 快照：卡片骨架一直在 DOM 里（已隐藏），所以不能只看按钮存在，
     还要确认当前确实在某国路由上、卡片有内容。 */
  function snapBtn() {
    var card = document.getElementById('pcard');
    if (!card || !card.classList.contains('on')) return null;
    if (!/^#\/c\/[A-Za-z]{3}/.test(location.hash || '')) return null;
    return card.querySelector('.pc-snap');
  }

  function doSnap() {
    var b = snapBtn();
    if (b) {
      b.click();
      /* 弹窗是第一次出图时才创建的，晚一拍再补提示 */
      setTimeout(hintNote, 260);
      return;
    }
    toast('先选一个国家，再生成快照');
  }

  function hintNote() {
    var n = document.querySelector('#psnap .note');
    if (n && n.textContent.indexOf('点图') < 0) n.textContent += ' · 点图看原尺寸';
  }

  /* 国家面板的操作行：链接 / 存为图 之后补一个「快照」 */
  function mountSnap() {
    var acts = document.getElementById('cacts');
    if (!acts || document.getElementById('csnap')) return;
    var b = document.createElement('button');
    b.id = 'csnap';
    b.title = '把这国导出成竖版分享卡（1080 × 1440，可直接发微信）';
    b.innerHTML = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" ' +
      'stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="2.5" y="1.8" width="11" height="12.4" rx="1.8"/>' +
      '<circle cx="8" cy="5.6" r="1.5"/><path d="M3.4 12.4l3-3.1 2.2 2.1 2-1.8 2 2"/></svg>' +
      '<span>快照</span>';
    acts.appendChild(b);
    b.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      doSnap();
    });
  }

  function mount() {
    mountToolbar();
    mountSnap();
    mountZoom();
  }

  /* 预览被窗口高度压到一半宽，字会糊；点图开一个原尺寸窗口 */
  function mountZoom() {
    document.addEventListener('click', function (e) {
      var im = e.target.closest && e.target.closest('#psnap img');
      if (!im || !im.src) return;
      e.preventDefault();
      fetch(im.src).then(function (r) { return r.blob(); }).then(function (b) {
        var url = URL.createObjectURL(b);
        var w = window.open(url, '_blank');
        if (!w) { toast('浏览器拦了新窗口，允许弹窗后重试'); return; }
        setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
      }).catch(function () { toast('打不开原图，直接点「下载图片」吧'); });
    });
  }

  window.__uzSnap = doSnap;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
