/* ===== 登录页地球：真实贴图 + 柔和侧光（替代原来的线框 HUD 地球） ===== */
(function initAgGlobe(){
  var cv = document.getElementById('agGlobe');
  if (!cv || !window.THREE) return;

  var T = window.THREE;
  var renderer, scene, camera, earth, spin = 0, running = true, ready = false;

  function sizeOf(){
    var w = cv.clientWidth || 600;
    var h = cv.clientHeight || 600;
    return { w: w, h: h };
  }

  function setup(){
    var s = sizeOf();
    renderer = new T.WebGLRenderer({ canvas: cv, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(s.w, s.h, false);
    if (T.sRGBEncoding) renderer.outputEncoding = T.sRGBEncoding;

    scene = new T.Scene();
    camera = new T.PerspectiveCamera(30, s.w / s.h, 0.1, 100);
    camera.position.set(0, 0, 4.9);

    var tex = new T.Texture(document.getElementById('agEarthTex'));
    tex.needsUpdate = true;
    if (T.sRGBEncoding) tex.encoding = T.sRGBEncoding;
    tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());

    var mat = new T.MeshPhongMaterial({ map: tex, shininess: 9, specular: 0x1b2a38 });
    earth = new T.Mesh(new T.SphereGeometry(1, 96, 64), mat);
    earth.rotation.z = 0.41;          /* 23.4° 地轴倾角 */
    earth.rotation.y = 2.62;          /* 默认朝向：欧洲—非洲—亚洲 */
    scene.add(earth);

    /* 大气：背面球壳 + 加色，只在边缘发蓝光 */
    var atmo = new T.Mesh(
      new T.SphereGeometry(1.022, 64, 48),
      new T.ShaderMaterial({
        vertexShader: 'varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: 'varying vec3 vN; void main(){ float f = pow(1.0 - abs(vN.z), 2.3); float rim = smoothstep(0.0, 1.0, f); gl_FragColor = vec4(0.50, 0.70, 0.95, rim * 0.30); }',
        blending: T.AdditiveBlending, transparent: true, side: T.BackSide, depthWrite: false
      })
    );
    earth.add(atmo);

    scene.add(new T.AmbientLight(0xffffff, 0.34));
    var key = new T.DirectionalLight(0xfff3e2, 1.05);
    key.position.set(-1.15, 0.95, 1.9);
    scene.add(key);
    var fill = new T.DirectionalLight(0x88aacc, 0.25);
    fill.position.set(1.4, -0.6, -1.2);
    scene.add(fill);

    ready = true;
    window.addEventListener('resize', onResize);
  }

  function onResize(){
    if (!ready) return;
    var s = sizeOf();
    camera.aspect = s.w / s.h;
    camera.updateProjectionMatrix();
    renderer.setSize(s.w, s.h, false);
  }

  var last = 0;
  function draw(now){
    if (!running) return;
    requestAnimationFrame(draw);
    var dt = Math.min(50, now - (last || now));
    last = now;
    earth.rotation.y += dt * 0.000035;    /* 极慢自转：看得见在动，但不抢注意力 */
    renderer.render(scene, camera);
  }

  function boot(){
    try { setup(); } catch (e) { return; }
    requestAnimationFrame(draw);
  }

  var img = document.getElementById('agEarthTex');
  if (!img) return;
  if (img.complete) boot(); else img.addEventListener('load', boot);

  /* 进入主界面后停止绘制 */
  var obs = setInterval(function () {
    var g = document.getElementById('authgate');
    if (!g || g.classList.contains('gone')) { running = false; clearInterval(obs); }
  }, 700);
})();
