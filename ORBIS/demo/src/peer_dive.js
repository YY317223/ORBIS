/* ============================================================
   俯冲转场
   ------------------------------------------------------------
   搭档这一版的「点国家」是：地球糊一下（.dive 的 blur+scale1.06），
   然后国家页淡进来 —— 看着像淡入，不像飞下去。

   这一层不动他的逻辑，只补两段 CSS 动画：
     进国家：把地球画布以「点击点」为原点放大到 2.15 倍、轻微模糊，
             国家页在他自己的 .5s 淡入里盖上来 —— 视觉上就是一头扎进去。
     回地球：反过来，地球从放大状态收回 1 倍。
   只改 #globe 的 transform / filter，不碰 WebGL 内部，也不拦任何点击。
   ============================================================ */
(function () {
  'use strict';

  var glide = null;          /* 最近一次在地球上按下的位置 */
  var token = 0;
  /* 系统里开了「减少动效」就不做俯冲；调试时可用 ?dive=1 强行打开 */
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce && !/[?&]dive=1/.test(location.search)) return;

  function globeEl() { return document.getElementById('globe'); }

  document.addEventListener('pointerdown', function (e) {
    if (e.target && e.target.id === 'globe') glide = { x: e.clientX, y: e.clientY };
  }, true);

  function origin(g) {
    var x = glide ? glide.x : window.innerWidth / 2;
    var y = glide ? glide.y : window.innerHeight * 0.52;
    g.style.setProperty('--pdx', x + 'px');
    g.style.setProperty('--pdy', y + 'px');
  }

  function diveIn() {
    var g = globeEl();
    if (!g) return;
    var my = ++token;
    origin(g);
    g.classList.remove('pdive-out');
    /* 先回到 1 倍并关掉过渡，强制一次回流，保证从「原始取景」开始放大 */
    g.style.transition = 'none';
    g.classList.remove('pdive-in');
    void g.offsetWidth;
    g.style.transition = '';
    g.classList.add('pdive-in');
    /* 国家页自己也「落地」一下：从 1.085 收到 1，跟地球的放大接上 */
    document.body.classList.remove('pdive-land');
    void document.body.offsetWidth;
    document.body.classList.add('pdive-land');
    /* 国家页淡入 0.5s，动画跑完就把类摘掉，免得影响后面的拖动 */
    setTimeout(function () {
      if (my !== token) return;
      g.classList.remove('pdive-in');
      document.body.classList.remove('pdive-land');
    }, 1040);
  }

  function diveOut() {
    var g = globeEl();
    if (!g) return;
    var my = ++token;
    origin(g);
    g.classList.remove('pdive-in');
    /* 从放大态「定格」一下，再收回 1 倍 */
    g.style.transition = 'none';
    g.classList.add('pdive-hold');
    void g.offsetWidth;
    g.classList.remove('pdive-hold');
    g.style.transition = '';
    g.classList.add('pdive-out');
    setTimeout(function () {
      if (my !== token) return;
      g.classList.remove('pdive-out');
    }, 900);
  }

  var last = location.hash;
  window.addEventListener('hashchange', function () {
    var to = location.hash, from = last;
    last = to;
    var toC = /^#\/c\/[A-Za-z]{3}/.test(to);
    var fromC = /^#\/c\/[A-Za-z]{3}/.test(from);
    if (toC && !fromC) diveIn();
    else if (fromC && !toC) diveOut();
  });
})();
