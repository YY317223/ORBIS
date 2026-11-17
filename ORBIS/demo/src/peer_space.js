/* ============================================================
   飞升 · 太阳系（独立场景，挂在搭档这版地球上）
   ------------------------------------------------------------
   为什么另起一个 WebGL 场景：
     搭档那颗球是他自己的渲染器，拿不到相机和场景；
     与其去改他的压缩代码，不如在它上面盖一层自己的 canvas，
     只在「飞升」时出现，退出就藏起来。两边互不干扰。

   素材：地球用 build/earth_tex.jpg（构建时内联成 data URI）；
        其余行星是程序化贴图，跟 Atlas 里同一套算法。
   ============================================================ */
(function () {
  'use strict';
  var T = window.THREE;
  if (!T) return;

  var DEG = Math.PI / 180;

  /* ---------- 星球数据 ---------- */
  var P = [
    { id: 'mercury', zh: '水星', en: 'Mercury', type: '类地行星 · 离太阳最近', note: '没有大气保温，向阳面 430 ℃、背阴面 −180 ℃。',
      orbit: 3.15, angle: 2.35, r: 0.20, kind: 'rock', seed: 11, pal: ['#9d9288', '#6f665e', '#c3b7a9'] },
    { id: 'venus', zh: '金星', en: 'Venus', type: '类地行星 · 最热的行星', note: '表面 460 ℃，气压是地球的 92 倍，硫酸云终年不散。',
      orbit: 4.45, angle: 5.55, r: 0.30, kind: 'cloud', seed: 23, pal: ['#e5c07a', '#d3a95f', '#f0d59b'] },
    { id: 'earth', zh: '地球', en: 'Earth', type: '类地行星 · 目前唯一有生命', note: '我们刚离开的地方。点它可以回去。',
      orbit: 5.95, angle: 1.02, r: 0.42 },
    { id: 'mars', zh: '火星', en: 'Mars', type: '类地行星 · 沙漠世界', note: '奥林匹斯山高 21.9 km，是太阳系最高的火山。',
      orbit: 7.45, angle: 3.55, r: 0.23, kind: 'rock', seed: 37, caps: true, pal: ['#b96a41', '#8e4b2c', '#d08d5f'] },
    { id: 'jupiter', zh: '木星', en: 'Jupiter', type: '气态巨行星 · 最大', note: '大红斑比地球还宽，已经刮了至少 190 年。',
      orbit: 9.95, angle: 4.95, r: 0.72, kind: 'band', seed: 41, spot: true, pal: ['#d9b791', '#c39b74', '#eddbc0', '#b98b64'] },
    { id: 'saturn', zh: '土星', en: 'Saturn', type: '气态巨行星 · 环最亮', note: '环主要由冰块组成，厚度平均不到 100 米。',
      orbit: 12.25, angle: 2.05, r: 0.60, kind: 'band', seed: 53, ring: true, pal: ['#e3cfa4', '#d3b989', '#f0e3c4', '#c6a877'] },
    { id: 'uranus', zh: '天王星', en: 'Uranus', type: '冰巨星 · 躺着自转', note: '自转轴倾斜 98°，几乎是躺着绕太阳滚。',
      orbit: 14.15, angle: 4.15, r: 0.42, kind: 'band', seed: 61, pal: ['#a9dde2', '#93cfd8', '#c2e9ec'] },
    { id: 'neptune', zh: '海王星', en: 'Neptune', type: '冰巨星 · 风最快', note: '风速可达每小时 2,100 公里，是太阳系最猛的风。',
      orbit: 15.80, angle: 0.32, r: 0.40, kind: 'band', seed: 73, pal: ['#5c81d6', '#4a6cc4', '#7b9ce4'] }
  ];

  /* ---------- 星球档案（Atlas 那一版：诞生 / 四项参数 / 探索程度 / 任务年表） ---------- */
  var BODY = {
    sun: {
      zh: '太阳', en: 'Sun', type: 'G2V 主序星', color: '#ffc970', born: 45.7,
      stats: [['直径', '139.2 万 km'], ['表面温度', '5,500 ℃'], ['质量占比', '99.86%'], ['自转周期', '25.4 天']],
      level: 3, levelName: '抵近环绕',
      active: 'SOHO、帕克太阳探测器、太阳轨道器、羲和号与夸父一号仍在工作；帕克最近一次距日 <b>610 万公里</b>。',
      missions: [
        ['1995', 'SOHO', '欧空局与 NASA 联合，连续观测太阳三十年'],
        ['2018', '帕克太阳探测器', '人类最快的人造物体，已冲入日冕'],
        ['2020', '太阳轨道器', '首次拍到太阳极区'],
        ['2021', '羲和号', '中国首颗太阳探测卫星'],
        ['2022', '夸父一号', '中国首颗综合性太阳观测卫星']
      ],
      note: '太阳没有固体表面，没有探测器能降落——「着陆」在这里无从谈起。'
    },
    mercury: {
      zh: '水星', en: 'Mercury', type: '类地行星 · 太阳系最小', color: '#a89d92', born: 45.6,
      stats: [['直径', '4,879 km'], ['距日', '5,790 万 km'], ['公转', '88 天'], ['卫星', '0']],
      level: 2, levelName: '环绕测绘',
      active: '贝皮科伦坡号正在接近，计划 <b>2026 年 11 月</b>进入水星轨道。',
      missions: [
        ['1974', '水手 10 号', '三次飞掠，人类第一次看清水星表面'],
        ['2011', '信使号', '首个环绕水星的探测器，2015 年撞向水星'],
        ['2018', '贝皮科伦坡号', '欧空局与日本联合，仍在途中']
      ],
      note: '水星没有大气保温，向阳面 430 ℃、背阴面 −180 ℃，是太阳系温差最大的行星。'
    },
    venus: {
      zh: '金星', en: 'Venus', type: '类地行星 · 最热的行星', color: '#e0bb78', born: 45.6,
      stats: [['直径', '12,104 km'], ['距日', '1.08 亿 km'], ['公转', '225 天'], ['卫星', '0']],
      level: 3, levelName: '着陆探测',
      active: '只有日本的<b>拂晓号</b>还在轨道上；金星表面没有任何工作中的探测器。',
      missions: [
        ['1970', '金星 7 号', '人类第一次在另一颗行星表面传回数据'],
        ['1975', '金星 9 号', '拍下第一批金星表面照片'],
        ['1982', '金星 13 号', '表面工作 127 分钟，钻取土壤样本'],
        ['1990', '麦哲伦号', '雷达穿透云层，测绘 98% 地表'],
        ['2015', '拂晓号', '日本探测器，至今仍在轨']
      ],
      note: '表面气压是地球的 92 倍，硫酸云终年不散。着陆器平均只能存活两小时。'
    },
    earth: {
      zh: '地球', en: 'Earth', type: '类地行星 · 唯一已知生命', color: '#4f93c4', born: 45.4,
      stats: [['直径', '12,742 km'], ['距日', '1.50 亿 km'], ['公转', '365.25 天'], ['卫星', '1']],
      level: 5, levelName: '载人驻留',
      active: '数千颗卫星在轨，国际空间站已连续载人 <b>25 年</b>。这是唯一被彻底测绘过的行星。',
      missions: [
        ['1957', '斯普特尼克 1 号', '人类第一颗人造卫星'],
        ['1961', '东方 1 号', '加加林成为第一个进入太空的人'],
        ['1998', '国际空间站', '连续载人至今，累计 20 多个国家参与'],
        ['—', '在轨卫星', '约 1.2 万颗，每天传回地表影像']
      ],
      note: '地球的每一寸陆地都有数据：这是这本图册存在的原因。'
    },
    mars: {
      zh: '火星', en: 'Mars', type: '类地行星 · 探索最密集', color: '#c07a4e', born: 45.1,
      stats: [['直径', '6,779 km'], ['距日', '2.28 亿 km'], ['公转', '687 天'], ['卫星', '2']],
      level: 4, levelName: '巡视探测',
      active: '<b>2 台火星车</b>在地面工作（好奇号、毅力号），<b>5 台轨道器</b>在环绕。',
      missions: [
        ['1971', '水手 9 号', '首个环绕火星的探测器'],
        ['1976', '海盗 1 号', '首次成功着陆并传回地表照片'],
        ['1997', '探路者号 / 旅居者号', '人类第一辆火星车'],
        ['2004', '勇气号 · 机遇号', '双车巡视，找到水蚀痕迹'],
        ['2012', '好奇号', '仍在工作，发现复杂有机分子'],
        ['2018', '洞察号', '首次记录到火星地震'],
        ['2021', '毅力号', '采集岩芯样本，等待取回'],
        ['2021', '机智号', '首架地外直升机，72 次飞行后停飞'],
        ['2021', '天问一号 / 祝融号', '中国首次火星着陆与巡视']
      ],
      note: '火星上共有 2 台工作中的火星车、5 台工作中的轨道器，是人类探索最密集的行星。'
    },
    jupiter: {
      zh: '木星', en: 'Jupiter', type: '气态巨行星 · 最大行星', color: '#d6b58c', born: 45.0,
      stats: [['直径', '139,820 km'], ['距日', '7.79 亿 km'], ['公转', '11.86 年'], ['卫星', '95']],
      level: 2, levelName: '环绕探测',
      active: '<b>朱诺号</b>仍在轨；JUICE 与欧罗巴快船正在途中，2030 年前后抵达。',
      missions: [
        ['1973', '先驱者 10 号', '首次飞掠木星'],
        ['1979', '旅行者 1 号 · 2 号', '发现木卫一上有活火山'],
        ['1995', '伽利略号', '首个环绕器，投放大气探测器'],
        ['2016', '朱诺号', '仍在轨，测绘内部结构与极区风暴'],
        ['2023', 'JUICE', '欧空局，2031 年抵达，转向木卫三'],
        ['2024', '欧罗巴快船', '2030 年抵达，调查木卫二冰下海洋']
      ],
      note: '大红斑是一场刮了至少 350 年的风暴，直径可以塞下整个地球。'
    },
    saturn: {
      zh: '土星', en: 'Saturn', type: '气态巨行星 · 环最壮观', color: '#e0c997', born: 45.0,
      stats: [['直径', '116,460 km'], ['距日', '14.34 亿 km'], ['公转', '29.45 年'], ['卫星', '274']],
      level: 3, levelName: '着陆卫星',
      active: '自 2017 年卡西尼号谢幕，<b>再无探测器造访</b>这个系统。',
      missions: [
        ['1979', '先驱者 11 号', '首次飞掠土星'],
        ['1980', '旅行者 1 号', '首次看清环的细节结构'],
        ['2004', '卡西尼号', '环绕 13 年，发现土卫二冰喷泉'],
        ['2005', '惠更斯号', '首次登陆土卫六，人类最远的一次着陆'],
        ['2017', '卡西尼号', '主动坠入土星大气，任务结束']
      ],
      note: '卡西尼号在 13 年里绕土星 294 圈，最后被有意送入土星大气烧毁，以免污染可能孕育生命的卫星。'
    },
    uranus: {
      zh: '天王星', en: 'Uranus', type: '冰巨星 · 躺着自转', color: '#a5dbe2', born: 45.0,
      stats: [['直径', '50,724 km'], ['距日', '28.71 亿 km'], ['公转', '84 年'], ['卫星', '28']],
      level: 1, levelName: '一次飞掠',
      active: '<b>1986 年之后，再无探测器造访</b>。它是太阳系里被了解得最少的行星。',
      missions: [
        ['1986', '旅行者 2 号', '迄今唯一一次造访，只停留了 6 小时']
      ],
      note: '自转轴倾斜 98°，几乎躺着绕太阳滚动。人类对它的全部认知，来自 6 小时的数据。'
    },
    neptune: {
      zh: '海王星', en: 'Neptune', type: '冰巨星 · 风最快', color: '#5b81d4', born: 45.0,
      stats: [['直径', '49,244 km'], ['距日', '44.95 亿 km'], ['公转', '164.8 年'], ['卫星', '16']],
      level: 1, levelName: '一次飞掠',
      active: '<b>1989 年之后，再无探测器造访</b>。',
      missions: [
        ['1989', '旅行者 2 号', '迄今唯一一次造访，发现大暗斑']
      ],
      note: '风速可达每小时 2,100 公里，是太阳系最猛烈的风。它绕太阳一圈要 165 年——从被发现到现在，才刚刚走完一圈。'
    }
  };

  var SUN_R = 1.06, SYS_R = 16.6;
  /* 公转速度：以地球「120 秒一圈」为基准，按距离的 1.15 次方递减。
     真实周期是 88 天 ↔ 165 年（差 680 倍），照搬的话外圈行星等于不动；
     压成 4 倍左右的速度差，看起来才像一个自己在转的星系。 */
  var ORBIT_BASE = Math.PI * 2 / 120;
  var EARTH_LOCAL = new T.Vector3(Math.cos(1.02) * 5.95, 0, Math.sin(1.02) * 5.95);

  /* ---------- DOM ---------- */
  var root, canvas, labelBox, cardEl, hintEl, renderer, scene, camera, earthMat = null;
  var solar, bodies = [], labels = {}, stars;
  var space = { on: false, moving: false, t: 0, dur: 2000, k: 0, sel: null };
  /* 方位角挑过：地球要落在「受光面」上，否则画面上是一颗全黑的地球。
   约束：相机方位角离地球方位角超过 ~79°，才看得到昼半球。 */
  var cam = { az: 2.92, el: 0.30, dist: 40, zoom: 1 };
  var raf = 0, last = 0;

  function build() {
    if (root) return;
    root = document.createElement('div');
    root.id = 'pspace';
    root.innerHTML =
      '<canvas id="pspacecv"></canvas>' +
      '<div id="pspacelabels"></div>' +
      '<div class="ps-top"><div class="k">Solar System</div><h2>太阳系</h2>' +
        '<div class="s">从地球往后退，退到能看见整条轨道</div></div>' +
      '<button class="ps-back" id="psBack">← 返回地球</button>' +
      '<div class="ps-hint" id="psHint">拖拽旋转 · 滚轮缩放 · 点行星看档案</div>' +
      '<aside class="ps-card" id="psCard"></aside>';
    document.body.appendChild(root);

    canvas = root.querySelector('#pspacecv');
    labelBox = root.querySelector('#pspacelabels');
    cardEl = root.querySelector('#psCard');
    hintEl = root.querySelector('#psHint');

    renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
    renderer.setClearColor(0x03060a, 1);
    scene = new T.Scene();
    camera = new T.PerspectiveCamera(38, 1, 0.05, 900);

    solar = new T.Group();
    scene.add(solar);
    solar.visible = false;

    buildStars();
    buildSun();
    buildPlanets();
    buildHits();
    bindUI();
  }

  /* ---------- 程序化贴图 ---------- */
  function rand32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function makeTex(p) {
    var W = 512, H = 256;
    var c = document.createElement('canvas'); c.width = W; c.height = H;
    var x = c.getContext('2d');
    var R = rand32(p.seed || 7);
    var pal = p.pal || ['#8a8580', '#6b6660', '#a9a49e'];
    x.fillStyle = pal[0]; x.fillRect(0, 0, W, H);

    if (p.kind === 'band' || p.kind === 'cloud') {
      var y = -6;
      while (y < H) {
        var bh = 4 + R() * 11;
        x.globalAlpha = 0.2 + R() * 0.5;
        x.fillStyle = pal[Math.floor(R() * pal.length)];
        var wob = 0.6 + R() * 1.5, ph = R() * 6.28;
        x.beginPath();
        for (var xx = 0; xx <= W; xx += 8) x.lineTo(xx, y + Math.sin(xx * 0.032 + ph) * wob);
        for (xx = W; xx >= 0; xx -= 8) x.lineTo(xx, y + bh + Math.sin(xx * 0.032 + ph) * wob);
        x.closePath(); x.fill();
        y += bh * 0.9;
      }
      x.globalAlpha = 1;
      if (p.spot) {
        x.save(); x.translate(W * 0.66, H * 0.63); x.scale(1, 0.52);
        var g = x.createRadialGradient(0, 0, 0, 0, 0, 17);
        g.addColorStop(0, 'rgba(190,86,58,.92)');
        g.addColorStop(0.6, 'rgba(196,112,80,.42)');
        g.addColorStop(1, 'rgba(196,112,80,0)');
        x.fillStyle = g; x.beginPath(); x.arc(0, 0, 17, 0, 6.283); x.fill();
        x.restore();
      }
    } else {
      for (var i = 0; i < 300; i++) {
        var rr = 6 + R() * 40, cx = R() * W, cy = R() * H;
        x.globalAlpha = 0.05 + R() * 0.2;
        x.fillStyle = pal[Math.floor(R() * pal.length)];
        x.beginPath();
        x.ellipse(cx, cy, rr, rr * (0.45 + R() * 0.7), R() * 3.14, 0, 6.283);
        x.fill();
      }
      x.globalAlpha = 1;
      if (p.caps) {
        x.fillStyle = 'rgba(238,236,230,.8)';
        x.beginPath(); x.ellipse(W * 0.5, H * 0.01, W * 0.5, H * 0.07, 0, 0, 6.283); x.fill();
        x.beginPath(); x.ellipse(W * 0.5, H * 0.99, W * 0.48, H * 0.055, 0, 0, 6.283); x.fill();
      }
    }
    var t = new T.CanvasTexture(c);
    t.wrapS = T.RepeatWrapping;
    return t;
  }

  var PLANE_VS = [
    'varying vec3 vWN; varying vec3 vWP; varying vec2 vUv;',
    'void main(){',
    '  vUv = uv;',
    '  vWN = normalize(mat3(modelMatrix) * normal);',
    '  vec4 wp = modelMatrix * vec4(position, 1.0);',
    '  vWP = wp.xyz;',
    '  gl_Position = projectionMatrix * viewMatrix * wp;',
    '}'
  ].join('\n');

  var PLANE_FS = [
    'uniform sampler2D uMap; uniform vec3 uSunPos; uniform float uOp; uniform float uAmb;',
    'varying vec3 vWN; varying vec3 vWP; varying vec2 vUv;',
    'void main(){',
    '  vec3 L = normalize(uSunPos - vWP);',
    '  float d = dot(normalize(vWN), L);',
    '  float lam = smoothstep(-0.22, 0.75, d);',
    '  vec3 base = texture2D(uMap, vUv).rgb;',
    '  vec3 col = base * (uAmb + (1.0 - uAmb) * lam);',
    '  gl_FragColor = vec4(col, uOp);',
    '}'
  ].join('\n');

  function planetMat(p, tex) {
    return new T.ShaderMaterial({
      uniforms: {
        uMap: { value: tex },
        uSunPos: { value: new T.Vector3(0, 0, 0) },
        uOp: { value: 0 },
        uAmb: { value: 0.10 }
      },
      transparent: true,
      vertexShader: PLANE_VS,
      fragmentShader: PLANE_FS
    });
  }

  /* ---------- 星空 ---------- */
  function buildStars() {
    var n = 2600, pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n);
    var R = rand32(9);
    for (var i = 0; i < n; i++) {
      var u = R() * 2 - 1, th = R() * Math.PI * 2, rad = 240 + R() * 320;
      var s = Math.sqrt(1 - u * u);
      pos[i * 3] = rad * s * Math.cos(th);
      pos[i * 3 + 1] = rad * u;
      pos[i * 3 + 2] = rad * s * Math.sin(th);
      var warm = R();
      col[i * 3] = 0.8 + warm * 0.2;
      col[i * 3 + 1] = 0.86 + warm * 0.12;
      col[i * 3 + 2] = 1.0;
      size[i] = 0.7 + R() * 2.2;
    }
    var g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(pos, 3));
    g.setAttribute('aColor', new T.BufferAttribute(col, 3));
    g.setAttribute('aSize', new T.BufferAttribute(size, 1));
    g.setAttribute('color', new T.BufferAttribute(col, 3));
    var m = new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, transparent: true, opacity: 0 });
    stars = new T.Points(g, m);
    scene.add(stars);
  }

  /* ---------- 太阳 ---------- */
  function buildSun() {
    var c = document.createElement('canvas'); c.width = c.height = 256;
    var x = c.getContext('2d');
    var g = x.createRadialGradient(128, 128, 0, 128, 128, 128);
    g.addColorStop(0, '#fff6df'); g.addColorStop(0.45, '#ffd489');
    g.addColorStop(0.78, '#ff9f45'); g.addColorStop(1, '#c95f18');
    x.fillStyle = g; x.fillRect(0, 0, 256, 256);
    var tex = new T.CanvasTexture(c);
    var mat = new T.ShaderMaterial({
      uniforms: { uMap: { value: tex }, uOp: { value: 0 } },
      transparent: true,
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform sampler2D uMap; uniform float uOp; varying vec2 vUv; void main(){ vec3 c = texture2D(uMap, vUv).rgb; gl_FragColor = vec4(c * 1.25, uOp); }'
    });
    var sun = new T.Mesh(new T.SphereGeometry(SUN_R, 48, 32), mat);
    solar.add(sun);

    /* 光晕：两层径向渐变 sprite */
    function halo(size, color, op) {
      var cv = document.createElement('canvas'); cv.width = cv.height = 128;
      var cx = cv.getContext('2d');
      var gg = cx.createRadialGradient(64, 64, 0, 64, 64, 64);
      gg.addColorStop(0, 'rgba(255,220,160,' + op + ')');
      gg.addColorStop(0.35, 'rgba(255,180,90,' + op * 0.45 + ')');
      gg.addColorStop(1, 'rgba(255,170,80,0)');
      cx.fillStyle = gg; cx.fillRect(0, 0, 128, 128);
      var sp = new T.Sprite(new T.SpriteMaterial({
        map: new T.CanvasTexture(cv), color: color, transparent: true,
        opacity: 0, blending: T.AdditiveBlending, depthWrite: false
      }));
      sp.scale.setScalar(size);
      solar.add(sp);
      return sp;
    }
    sun.userData.halos = [halo(SUN_R * 5.4, 0xffc074, 0.85), halo(SUN_R * 9.5, 0xff9a4e, 0.34)];
    bodies.push({ id: 'sun', zh: '太阳', en: 'Sun', type: 'G2V 主序星',
      note: '占太阳系 99.86% 的质量，表面 5,500 ℃，光到地球要 8 分 20 秒。',
      mesh: sun, mat: mat, r: SUN_R, label: 'sun' });
  }

  /* ---------- 行星 ---------- */
  function buildPlanets() {
    /* 轨道线 */
    P.forEach(function (p) {
      var pts = [];
      for (var i = 0; i <= 240; i++) {
        var a = i / 240 * Math.PI * 2;
        pts.push(new T.Vector3(Math.cos(a) * p.orbit, 0, Math.sin(a) * p.orbit));
      }
      var lg = new T.BufferGeometry().setFromPoints(pts);
      var lm = new T.LineBasicMaterial({
        color: 0x8fb6d8, transparent: true, opacity: 0, depthWrite: false,
        blending: T.AdditiveBlending
      });
      var line = new T.Line(lg, lm);
      line.userData.maxOp = 0.16;
      solar.add(line);
    });

    P.forEach(function (p) {
      var isEarth = p.id === 'earth';
      var tex = isEarth && window.__EARTH_TEX__
        ? new T.TextureLoader().load(window.__EARTH_TEX__)
        : makeTex(p);
      if (isEarth) tex.anisotropy = 4;
      var mat = planetMat(p, tex);
      if (isEarth) {
        earthMat = mat;
        gradeEarth(tex, mat);
        /* 地球页那颗球是「环境光很足」的画法：夜面不是黑的，而是暗蓝。
           这里把环境光提上来，否则叠化过去会有半张脸沉进黑暗里。 */
        mat.uniforms.uAmb.value = 0.55;
      }
      var mesh = new T.Mesh(new T.SphereGeometry(p.r, 44, 30), mat);
      mesh.position.set(Math.cos(p.angle) * p.orbit, 0, Math.sin(p.angle) * p.orbit);
      mesh.rotation.z = (p.id === 'uranus' ? 1.71 : 0.22);
      /* 地球页那颗球默认正对东亚；我们的贴图默认正对印度洋，
         先转 ~29° 把经度对上，叠化时才不会是「同一颗星球的另一面」。 */
      if (isEarth) mesh.rotation.y = -0.46;
      solar.add(mesh);

      var ringMesh = null;
      if (p.ring) {
        var rc = document.createElement('canvas'); rc.width = 256; rc.height = 8;
        var rx = rc.getContext('2d');
        var rg = rx.createLinearGradient(0, 0, 256, 0);
        rg.addColorStop(0, 'rgba(226,206,166,0)');
        rg.addColorStop(0.18, 'rgba(232,214,178,.75)');
        rg.addColorStop(0.42, 'rgba(200,176,132,.35)');
        rg.addColorStop(0.62, 'rgba(236,222,190,.8)');
        rg.addColorStop(1, 'rgba(210,190,150,0)');
        rx.fillStyle = rg; rx.fillRect(0, 0, 256, 8);
        var rtex = new T.CanvasTexture(rc);
        var rmat = new T.MeshBasicMaterial({
          map: rtex, transparent: true, opacity: 0, side: T.DoubleSide, depthWrite: false
        });
        var ring = new T.Mesh(new T.RingGeometry(p.r * 1.35, p.r * 2.15, 96), rmat);
        ring.rotation.x = Math.PI / 2 - 0.42;
        ring.position.copy(mesh.position);
        solar.add(ring);
        ring.userData.isRing = true;
        ringMesh = ring;
      }

      if (isEarth) addAtmosphere(mesh, p.r);

      bodies.push({
        id: p.id, zh: p.zh, en: p.en, type: p.type, note: p.note,
        mesh: mesh, mat: mat, r: p.r, angle: p.angle, orbit: p.orbit,
        ring: ringMesh,
        speed: ORBIT_BASE * Math.pow(5.95 / p.orbit, 1.15)
      });
    });
  }

  /* 地球贴图和地球页那颗球差得有点远（那边偏金、偏暖，还带一层大气），
     这里把同一张 Blue Marble 轻微降饱和 + 加暖 + 补对比，先对齐色调再说。 */
  function gradeEarth(tex, mat) {
    if (!window.__EARTH_TEX__) return;
    var img = new Image();
    img.onload = function () {
      try {
        var W = 1024, H = 512;
        var cv = document.createElement('canvas');
        cv.width = W; cv.height = H;
        var cx = cv.getContext('2d');
        cx.drawImage(img, 0, 0, W, H);
        /* 原始 Blue Marble 的海洋深到近黑 (6,24,60)，地球页那颗球是 (43,78,139)。
           单纯调亮度会把陆地先烧白，所以走 gamma 曲线把暗部整体抬起来，
           再补一点饱和度，别让颜色被抬灰。 */
        var id = cx.getImageData(0, 0, W, H), d = id.data;
        var G = 0.50, SAT = 1.18, K = 0.95;
        for (var i = 0; i < d.length; i += 4) {
          var r = 255 * K * Math.pow(d[i] / 255, G);
          var g = 255 * K * Math.pow(d[i + 1] / 255, G);
          var b = 255 * K * Math.pow(d[i + 2] / 255, G);
          var l = 0.299 * r + 0.587 * g + 0.114 * b;
          d[i]     = Math.max(0, Math.min(255, l + (r - l) * SAT));
          d[i + 1] = Math.max(0, Math.min(255, l + (g - l) * SAT));
          d[i + 2] = Math.max(0, Math.min(255, l + (b - l) * SAT));
        }
        cx.putImageData(id, 0, 0);
        var t = new T.CanvasTexture(cv);
        t.anisotropy = 4;
        mat.uniforms.uMap.value = t;
      } catch (e) {}
    };
    img.src = window.__EARTH_TEX__;
  }

  /* 大气层：贴在球体上的两枚 sprite，靠加色混合做出边缘的一圈蓝白光 */
  function addAtmosphere(mesh, r) {
    function halo(size, inner, alpha) {
      var cv = document.createElement('canvas'); cv.width = cv.height = 256;
      var cx = cv.getContext('2d');
      var g = cx.createRadialGradient(128, 128, 0, 128, 128, 128);
      g.addColorStop(0, 'rgba(150,200,255,0)');
      g.addColorStop(inner, 'rgba(160,205,255,0)');
      g.addColorStop(Math.min(0.98, inner + 0.045), 'rgba(175,215,255,' + alpha + ')');
      g.addColorStop(1, 'rgba(120,170,230,0)');
      cx.fillStyle = g; cx.fillRect(0, 0, 256, 256);
      var sp = new T.Sprite(new T.SpriteMaterial({
        map: new T.CanvasTexture(cv), transparent: true, opacity: 1,
        blending: T.AdditiveBlending, depthWrite: false
      }));
      sp.scale.setScalar(size);
      sp.userData.isGlow = true;
      mesh.add(sp);
      return sp;
    }
    /* 内圈贴着球面（0.5 半径处正好是球缘），外圈铺得远一点 */
    halo(r * 2.45, 0.44, 0.46);
    halo(r * 3.9, 0.40, 0.10);
  }

  /* ---------- 点击拾取用的透明球 ----------
     行星在远景里只有十几像素，直接点球体几乎点不中。
     每颗星球套一个更大的透明球（不写颜色、不写深度），只负责被射线打中。 */
  function buildHits() {
    bodies.forEach(function (b) {
      if (!b.mesh) return;
      var r = Math.max(b.r * 2.1, 0.42);
      var hit = new T.Mesh(
        new T.SphereGeometry(r, 16, 12),
        new T.MeshBasicMaterial({ colorWrite: false, depthWrite: false, transparent: true, opacity: 0 })
      );
      hit.position.copy(b.mesh.position);
      hit.userData.bodyId = b.id;
      solar.add(hit);
      b.hit = hit;
    });
  }

  /* ---------- 标签 ---------- */
  function buildLabels() {
    bodies.forEach(function (b) {
      var d = document.createElement('button');
      d.className = 'pslab' + (b.id === 'sun' ? ' sunlab' : '');
      d.dataset.id = b.id;
      d.innerHTML = '<i></i><span>' + b.zh + '</span>';
      d.addEventListener('click', function (e) { e.stopPropagation(); pick(b.id); });
      labelBox.appendChild(d);
      labels[b.id] = d;
    });
  }

  /* ---------- 相机 ---------- */
  function applyCam() {
    var d = cam.dist * cam.zoom;
    var cx = Math.cos(cam.el) * Math.cos(cam.az) * d;
    var cy = Math.sin(cam.el) * d;
    var cz = Math.cos(cam.el) * Math.sin(cam.az) * d;
    camera.position.set(cx, cy, cz);
    camera.lookAt(0, 0, 0);
  }

  /* ---------- 尺寸 ---------- */
  function resize() {
    if (!renderer) return;
    var w = window.innerWidth, h = window.innerHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  /* ---------- 飞升 / 回落 ---------- */
  function ascend(on) {
    if (space.on === on) return;
    build();
    if (labels.sun === undefined) buildLabels();
    resize();
    space.on = on;
    space.moving = true;
    space.t = 0;
    space.dur = on ? 3200 : 1700;
    space.from = space.k;
    space.to = on ? 1 : 0;
    solar.visible = true;
    root.classList.add('on');
    document.body.classList.add('pspace-on');
    starOpacity(0);
    if (on) {
      space.sel = null;
      openPlanet(null);
      loop(true);
    } else {
      cardEl.classList.remove('on');
    }
  }

  function starOpacity(v) {
    if (stars) stars.material.opacity = v;
  }

  function loop(start) {
    if (start) {
      last = performance.now();
      if (!raf) raf = requestAnimationFrame(tick);
    }
  }

  function tick(now) {
    raf = requestAnimationFrame(tick);
    var dt = Math.min(40, now - last) / 1000;
    last = now;

    /* 主时间轴 */
    if (space.moving) {
      space.t += (now - (space._last || now));
      space._last = now;
      var k = Math.min(1, space.t / space.dur);
      var e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      space.k = space.from + (space.to - space.from) * e;
      if (k >= 1) { space.moving = false; space._last = 0; }
    } else {
      space._last = 0;
    }

    var kk = space.k;
    /* 相机：起点必须是「贴着地球往下看」，终点才是系统全景。
       之前一上来就是 dist=13 的内太阳系，跟地球页那一帧完全对不上，
       淡入的 0.5 秒里画面直接换了一个世界 —— 这就是「突兀」的来源。

       现在：前 10% 停在近景（和地球页的构图接得上），
       之后用 easeInOut 把相机从「地球上方 1.9 个单位」拉到「半径 40 的远景」，
       视线目标同时从地心移到太阳。地球就是这样被甩到轨道上的。 */
    /* 前 30% 停在近景（约 1 秒），让观众看清「这是地球」，
       之后 2.2 秒才拉开 —— 时间上的「停一下」比距离曲线更能压住突兀感。 */
    var HOLD = 0.26;
    var p = Math.max(0, Math.min(1, (kk - HOLD) / (1 - HOLD)));
    /* smoothstep：起步和收尾都轻，中段匀速 —— 用 easeInOut 的话，
       前 40% 几乎不动、后 30% 一下冲到底，看着像「卡了一下再跳」 */
    var e = p * p * (3 - 2 * p);
    var holdRise = Math.min(1, kk / HOLD) * 0.26;           // 停住的时候镜头也在慢慢抬

    var earthBody = null;
    for (var bi = 0; bi < bodies.length; bi++) if (bodies[bi].id === 'earth') { earthBody = bodies[bi]; break; }
    var earthNow = earthBody ? earthBody.mesh.position.clone() : EARTH_LOCAL.clone();
    var sunDir = earthNow.clone().normalize();             // 太阳 → 地球（用当前位置）
    var nearPos = earthNow.clone()
      .addScaledVector(sunDir, -1.28)                       // 站在太阳这一侧：看到的是昼半球
      .add(new T.Vector3(0, 0.45 + holdRise, 0));           // 只抬高一点，别把镜头翻到夜面去
    var farPos = new T.Vector3(
      Math.cos(cam.el) * Math.cos(cam.az) * cam.dist * cam.zoom,
      Math.sin(cam.el) * cam.dist * cam.zoom,
      Math.cos(cam.el) * Math.sin(cam.az) * cam.dist * cam.zoom
    );
    var nearLook = earthNow.clone();
    var farLook = new T.Vector3(0, 0, 0);

    if (e <= 0) {
      camera.position.copy(nearPos);
      camera.lookAt(nearLook);
    } else {
      camera.position.lerpVectors(nearPos, farPos, e);
      var look = nearLook.clone().lerp(farLook, e);
      camera.lookAt(look);
    }

    /* 透明度：星星随上升淡入，星球一直是实心的——
       半透明的太阳会把背后的光晕透出来，颜色发绿，很难看。
       整个覆盖层自己的 CSS 淡入已经够了。 */
    starOpacity(0.20 + 0.70 * Math.max(0, (kk - 0.18) / 0.82));
    bodies.forEach(function (b) {
      if (b.mat) b.mat.uniforms.uOp.value = 1;
      if (b.mesh && b.mesh.userData.halos) {
        b.mesh.userData.halos.forEach(function (h) { h.material.opacity = 1; });
      }
    });
    solar.children.forEach(function (o) {
      if (o.userData && o.userData.maxOp != null) {
        var ot = Math.max(0, Math.min(1, (kk - 0.26) / 0.34));
        o.material.opacity = o.userData.maxOp * ot;
      }
      if (o.userData && o.userData.isRing) o.material.opacity = 0.85;
    });

    /* 地球用「随相机」的光照：地球页那颗球几乎没有晨昏线，是一张均匀受光的画。
       让它跟着太阳打光，叠化过去会有半张脸陷进黑暗，怎么调色都对不上。 */
    if (earthMat) earthMat.uniforms.uSunPos.value.copy(camera.position);

    /* 公转 + 自转 */
    bodies.forEach(function (b) {
      if (!b.mesh || b.id === 'sun') return;
      b.angle += (b.speed || 0) * dt;
      b.mesh.position.set(Math.cos(b.angle) * b.orbit, 0, Math.sin(b.angle) * b.orbit);
      if (b.hit) b.hit.position.copy(b.mesh.position);
      if (b.ring) b.ring.position.copy(b.mesh.position);   // 环跟着走，朝向不变
      /* 起飞头一秒地球先别自转：叠化时两颗球要停在同一个经度上 */
      var spin = (b.id === 'earth' && space.on && space.k < 0.30) ? 0 : dt;
      b.mesh.rotation.y += spin * (0.16 + b.r * 0.3);
    });

    /* 投影标签 */
    var w = window.innerWidth, h = window.innerHeight;
    bodies.forEach(function (b) {
      var el = labels[b.id];
      if (!el) return;
      var v = b.mesh.position.clone();
      v.project(camera);
      var behind = v.z > 1;
      var x = (v.x * 0.5 + 0.5) * w, y = (-v.y * 0.5 + 0.5) * h;
      var vis = !behind && x > -60 && x < w + 60 && y > -30 && y < h + 30 && kk > 0.34;
      el.style.opacity = vis ? String(Math.min(1, (kk - 0.34) * 4)) : '0';
      el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
    });

    renderer.render(scene, camera);

    if (!space.on && !space.moving && space.k <= 0.001) {
      cancelAnimationFrame(raf); raf = 0;
      solar.visible = false;
      root.classList.remove('on');
      document.body.classList.remove('pspace-on');
      cardEl.classList.remove('on');
    }
  }

  /* ---------- 交互 ---------- */
  function bindUI() {
    root.querySelector('#psBack').addEventListener('click', function () { ascend(false); });

    var down = null, moved = 0;
    canvas.addEventListener('pointerdown', function (e) {
      down = { x: e.clientX, y: e.clientY, az: cam.az, el: cam.el };
      moved = 0;
      try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
    });
    canvas.addEventListener('pointermove', function (e) {
      if (!down) return;
      var dx = e.clientX - down.x, dy = e.clientY - down.y;
      moved = Math.max(moved, Math.abs(dx) + Math.abs(dy));
      cam.az = down.az - dx * 0.005;
      cam.el = Math.max(-0.9, Math.min(0.95, down.el + dy * 0.004));
    });
    canvas.addEventListener('pointerup', function (e) {
      if (down && moved < 6) raycast(e.clientX, e.clientY);
      down = null;
    });
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      cam.zoom = Math.max(0.45, Math.min(2.4, cam.zoom * (e.deltaY > 0 ? 1.08 : 0.93)));
    }, { passive: false });

    window.addEventListener('resize', resize);
    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && space.on) ascend(false);
    });
  }

  function raycast(cx, cy) {
    var rect = canvas.getBoundingClientRect();
    var ndc = new T.Vector2(((cx - rect.left) / rect.width) * 2 - 1, -((cy - rect.top) / rect.height) * 2 + 1);
    var ray = new T.Raycaster();
    ray.setFromCamera(ndc, camera);
    var meshes = bodies.filter(function (b) { return b.hit; }).map(function (b) { return b.hit; });
    var hits = ray.intersectObjects(meshes, false);
    /* 点空白处 = 收起卡片 */
    if (!hits.length) { openPlanet(null); return; }
    var hit = bodies.filter(function (b) { return b.hit === hits[0].object; })[0];
    if (hit) openPlanet(hit.id);
  }

  function pick(id) { openPlanet(id); }

  /* ---------- 星球档案卡（按 Atlas 那一版：诞生 / 参数 / 探索程度 / 任务年表） ---------- */
  function shade(hex, k) {
    var c = hex.replace('#', '');
    if (c.length === 3) c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
    var r = parseInt(c.substr(0, 2), 16), g = parseInt(c.substr(2, 2), 16), b = parseInt(c.substr(4, 2), 16);
    var f = function (v) { return Math.max(0, Math.min(255, Math.round(v * (1 + k)))); };
    return 'rgb(' + f(r) + ',' + f(g) + ',' + f(b) + ')';
  }
  function fmtLate(late) {
    return (Math.round(late / 100) * 100).toLocaleString('en-US') + ' 万年';
  }

  function openPlanet(id) {
    if (!id) {
      space.sel = null;
      cardEl.classList.remove('on');
      bodies.forEach(function (b) { if (labels[b.id]) labels[b.id].classList.remove('on'); });
      return;
    }
    var d = BODY[id];
    if (!d) return;
    space.sel = id;
    var late = (45.67 - d.born) * 10000;

    var dots = [1, 2, 3, 4, 5].map(function (i) {
      return '<i class="' + (i <= d.level ? 'on' : '') + '"></i>';
    }).join('');
    var ms = d.missions.map(function (m) {
      var now = /^(—|至今)/.test(m[0]);
      return '<li class="' + (now ? 'now' : '') + '"><em>' + m[0] + '</em>' +
        '<div><b>' + m[1] + '</b><span>' + m[2] + '</span></div></li>';
    }).join('');

    cardEl.innerHTML =
      '<div class="pc-head">' +
        '<span class="pc-dot" style="background:radial-gradient(circle at 34% 30%,' + d.color + ',' + shade(d.color, -0.45) + ');' +
          'box-shadow:0 0 16px ' + d.color + '66, inset 0 0 8px rgba(0,0,0,.35)"></span>' +
        '<div class="pc-ttl"><h2>' + d.zh + '</h2><p>' + d.en + ' · ' + d.type + '</p></div>' +
        '<button class="pc-x" aria-label="关闭">✕</button>' +
      '</div>' +
      '<div class="pc-born">' +
        '<div class="k">诞生</div>' +
        '<div class="v">' + d.born.toFixed(1) + '<u>亿年前</u></div>' +
        '<div class="n">' + (late < 300
          ? '几乎与太阳系同时成形'
          : '太阳系形成于 45.7 亿年前，它比太阳系晚了 <b>' + fmtLate(late) + '</b>') + '</div>' +
      '</div>' +
      '<div class="pc-stats">' + d.stats.map(function (x) {
        return '<div><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div></div>';
      }).join('') + '</div>' +
      '<div class="pc-sec">' +
        '<div class="h"><span>人类探索程度</span><b>' + d.level + ' / 5 · ' + d.levelName + '</b></div>' +
        '<div class="pc-lv"><div class="pc-dots">' + dots + '</div><span>' + d.levelName + '</span></div>' +
        '<div class="pc-scale"><span>未探测</span><span>飞掠</span><span>环绕</span><span>着陆</span>' +
          '<span>巡视</span><span>载人</span></div>' +
      '</div>' +
      '<div class="pc-sec">' +
        '<div class="h"><span>任务年表</span><b>' + d.missions.length + ' 项</b></div>' +
        '<ul class="pc-ms">' + ms + '</ul>' +
      '</div>' +
      '<div class="pc-foot">' + d.active + '<br><br>' + d.note + '</div>' +
      (id === 'earth' ? '<button class="pc-home" id="psHome2">回到地球 ↑</button>' : '');

    cardEl.classList.add('on');
    cardEl.scrollTop = 0;
    cardEl.querySelector('.pc-x').addEventListener('click', function () { openPlanet(null); });
    var home = cardEl.querySelector('#psHome2');
    if (home) home.addEventListener('click', function () { ascend(false); });
    bodies.forEach(function (b) {
      if (labels[b.id]) labels[b.id].classList.toggle('on', b.id === id);
    });
  }
  /* openPlanet(null) = 关掉 */
  var _openPlanet = openPlanet;

  /* ---------- 入口 ---------- */
  function mountEntry() {
    var zoom = document.getElementById('zoom');
    if (!zoom || document.getElementById('psEntry')) return;
    var b = document.createElement('button');
    b.id = 'psEntry';
    b.className = 'pol';
    b.title = '飞升到太阳系';
    b.textContent = '飞升';
    var cmp = document.getElementById('pcmpEntry');
    if (cmp && cmp.nextSibling) zoom.insertBefore(b, cmp.nextSibling);
    else zoom.insertBefore(b, zoom.firstChild);
    b.addEventListener('click', function () { ascend(true); });
  }
  function boot() {
    mountEntry();
    /* 空闲时先把场景建好：第一次点「飞升」如果要现建 WebGL 上下文 + 解码贴图，
       会有两三百毫秒的卡顿，那一下本身就是「突兀」的一部分。 */
    setTimeout(function () {
      try { build(); } catch (e) {}
    }, 1500);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  /* 预热：地球贴图是 data URI，先让浏览器解码好，第一次点「飞升」就不必等 */
  if (window.__EARTH_TEX__) { var im = new Image(); im.src = window.__EARTH_TEX__; }

  window.__PSPACE__ = {
    ascend: ascend,
    isOn: function () { return space.on; },
    k: function () { return space.k; },
    /* 调试用：把过渡定格在某个进度，方便逐帧检查构图 */
    seek: function (v) { space.k = v; space.moving = false; }
  };
})();
