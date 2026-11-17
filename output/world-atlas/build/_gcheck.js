
(function(){
"use strict";
var D=window.ATLAS_DATA, CS=D.countries, YEARS=D.meta.years;
var LASTY=YEARS[YEARS.length-1], YI=YEARS.length-1;
var clamp=function(v,a,b){return Math.max(a,Math.min(b,v));};
var $=function(s){return document.querySelector(s);};
var esc=function(s){return String(s==null?'':s).replace(/[&<>"]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m];});};
var RAD=Math.PI/180;

/* ============================================================ 0. 大洲
   lon/lat 既作投影锚点，也作球面上的标签落点；box 用连续经度（可超 180）
   手写视窗，比按 bbox 自动取景稳定：跨洲国家（如俄罗斯）不会把整洲拉扁。 */
var CONT={
  AS:{n:'亚洲',e:'Asia',c:'#CE8C43',lon:95,lat:40,box:[26,152,-12,78]},
  EU:{n:'欧洲',e:'Europe',c:'#7F7AD2',lon:18,lat:53,box:[-26,62,33,72]},
  AF:{n:'非洲',e:'Africa',c:'#90BE5D',lon:20,lat:5,box:[-20,53,-36,38]},
  NA:{n:'北美洲',e:'North America',c:'#2FA08F',lon:-100,lat:43,box:[-172,-50,4,76]},
  SA:{n:'南美洲',e:'South America',c:'#B05FB0',lon:-60,lat:-13,box:[-84,-32,-56,14]},
  OC:{n:'大洋洲',e:'Oceania',c:'#CE7290',lon:148,lat:-24,box:[110,193,-50,2]},
  AN:{n:'南极圈',e:'Antarctic',c:'#6E7A88',lon:0,lat:-70,box:[-180,180,-90,-55]}
};
var CORDER=['AS','EU','AF','NA','SA','OC'];
var MEMBER={};
CS.forEach(function(c,i){ if(c.off) return; var k=c.cn||'AS'; (MEMBER[k]=MEMBER[k]||[]).push(i); });
Object.keys(MEMBER).forEach(function(k){
  MEMBER[k].sort(function(a,b){ return (CS[b].ar||0)-(CS[a].ar||0); });
});

/* ============================================================ 1. 经纬度几何
   ll 中每个环是 [x0,y0,dx,dy,...]，x=(lon+180)*100，y=(90-lat)*100，单位 0.01°。
   解码后统一换算成 0.1° 单位：x∈[0,3600]，y∈[0,1800]（保留小数，故精度仍是 0.01°）。
   经度已连续化，可超出两端。 */
var RINGS=[], CBOX=[];
CS.forEach(function(c){
  var rs=[], x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  (c.ll||[]).forEach(function(a){
    var n=a.length>>1; if(n<3) return;
    var arr=new Float32Array(n*2), x=a[0]/10, y=a[1]/10;
    arr[0]=x; arr[1]=y;
    for(var i=2,j=2;i<a.length;i+=2,j+=2){ x+=a[i]/10; y+=a[i+1]/10; arr[j]=x; arr[j+1]=y; }
    for(var k=0;k<arr.length;k+=2){
      var vx=arr[k], vy=arr[k+1];
      if(vx<x0)x0=vx; if(vx>x1)x1=vx;
      if(vy<y0)y0=vy; if(vy>y1)y1=vy;
    }
    rs.push(arr);
  });
  RINGS.push(rs); CBOX.push([x0,y0,x1,y1]);
});
var lonOf=function(u){ return u/10-180; };
function repsFor(b){ var r=[0]; if(b[0]<60) r.push(3600); if(b[2]>3540) r.push(-3600); return r; }
var latOf=function(v){ return 90-v/10; };

/* ============================================================ 2. 国家拾取（等经纬贴图）
   与地表贴图同一 UV 约定：u=(lon+180)/360，v=(90-lat)/180。 */
var PW=2048, PH=1024;
var pcv=document.createElement('canvas'); pcv.width=PW; pcv.height=PH;
var pctx=pcv.getContext('2d',{willReadFrequently:true});
pctx.setTransform(1,0,0,1,0,0); pctx.clearRect(0,0,PW,PH);
pctx.setTransform(PW/3600,0,0,PH/1800,0,0);
CS.forEach(function(c,i){
  if(c.off || !RINGS[i].length) return;
  var id=i+1, b=CBOX[i], reps=repsFor(b);
  pctx.fillStyle='rgb('+(id&255)+','+((id>>8)&255)+',255)';
  reps.forEach(function(sh){
    var p=new Path2D();
    RINGS[i].forEach(function(a){
      p.moveTo(a[0]+sh,a[1]);
      for(var k=2;k<a.length;k+=2) p.lineTo(a[k]+sh,a[k+1]);
      p.closePath();
    });
    pctx.fill(p,'evenodd');
  });
});
var PICKDATA=null;
try{ PICKDATA=pctx.getImageData(0,0,PW,PH).data; }catch(e){}
function pickAt(lon,lat){
  if(!PICKDATA) return null;
  var x=Math.round(((lon+180)/360)*PW), y=Math.round(((90-lat)/180)*PH);
  if(x<0||y<0||x>=PW||y>=PH) return null;
  var o=(y*PW+x)*4, d=PICKDATA;
  if(d[o+3]<128||d[o+2]<128) return null;
  var id=d[o]|(d[o+1]<<8);
  return CS[id-1]||null;
}

/* ============================================================ 3. 洲别配色
   球面与洲视图都按大洲取色；洲视图里同一洲的国家用同色系不同明度区分。 */
function hex2rgb(h){ h=h.replace('#',''); return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]; }
function mixHex(a,b,t){ var A=hex2rgb(a), B=hex2rgb(b);
  return 'rgb('+Math.round(A[0]+(B[0]-A[0])*t)+','+Math.round(A[1]+(B[1]-A[1])*t)+','+Math.round(A[2]+(B[2]-A[2])*t)+')'; }
/* 六级明度差：洲内相邻国家拉开明显色阶（下探 0.46、上提 0.30），
   周期取 6 与常见邻国数错开， alphabetical 顺序在空间上近似随机，拼贴感更强 */
var SHADE=[[0.40,'#08111c'],[0.20,'#08111c'],[0,'#08111c'],[0.16,'#f2e8da'],[0.30,'#f2e8da'],[0.30,'#08111c']];
var FILL=[];

/* ---- 数据染色：把 2000–2023 的 WDI 序列映射到一条色带 ----
   色带宽 → 窄端都避开海洋蓝，低值深靛、高值暖橙，与站点配色同族。 */
var RAMP=[[0,'#16304F'],[0.22,'#1E6079'],[0.45,'#2E9A8A'],[0.66,'#9DBA58'],[0.84,'#E8AE3E'],[1,'#E8673F']];
function rampAt(t){
  t=clamp(t,0,1);
  for(var i=1;i<RAMP.length;i++){
    if(t<=RAMP[i][0]){
      var a=RAMP[i-1], b=RAMP[i];
      return mixHex(a[1],b[1],(t-a[0])/((b[0]-a[0])||1));
    }
  }
  return RAMP[RAMP.length-1][1];
}
/* 量级型指标（GDP / 人口 / 人均）必须走对数：否则 200 倍差距会把中小国家全压成一色 */
var IND={
  cont:{n:'大洲',u:''},
  pc:{n:'人均 GDP',u:'美元',log:[2.0,5.16],fmt:fC},
  gdp:{n:'GDP',u:'美元',log:[8,13.56],fmt:fG},
  pop:{n:'人口',u:'人',log:[4,9.26],fmt:fP},
  le:{n:'预期寿命',u:'岁',lin:[47,86],fmt:function(v){ return (v==null||isNaN(v))?'—':v.toFixed(1); }}
};
var DS={ind:'cont',yi:YI,play:false,cmp:[],dir:'top',step:0};
function CI(){ return DS.ind==='cont'?'pc':DS.ind; }
function valOf(c,k,yi){ var a=c&&c[k]; return (a&&a.length)?a[yi==null?DS.yi:yi]:null; }
function tOf(v,k){
  var I=IND[k||DS.ind];
  if(!I||!v) return null;
  if(I.log) return v<=0?null:(Math.log10(v)-I.log[0])/(I.log[1]-I.log[0]);
  if(I.lin) return (v-I.lin[0])/(I.lin[1]-I.lin[0]);
  return null;
}
function computeFills(){
  CS.forEach(function(c,i){
    var K=CONT[c.cn||'AS']||CONT.AS, S=SHADE[i%SHADE.length];
    if(c.off){ FILL[i]='rgba(58,70,86,.55)'; return; }
    if(DS.ind==='cont'){ FILL[i]= S[0]? mixHex(K.c,S[1],S[0]) : K.c; return; }
    var t=tOf(valOf(c,DS.ind));
    FILL[i]= t==null ? 'rgba(52,64,80,.72)' : rampAt(t);
  });
}
computeFills();

/* ============================================================ 4. 洲别贴图（叠在地表之上）
   拆成两层：填充层随年份/指标重绘，边界层只画一次。
   这样拖时间轴时只付出一层的绘制成本。 */
var P2W=3072, P2H=1536;
var polCv=Object.assign(document.createElement('canvas'),{width:P2W,height:P2H});
var pg=polCv.getContext('2d');
var edgeCv=Object.assign(document.createElement('canvas'),{width:P2W,height:P2H});
var eg=edgeCv.getContext('2d');
var POLP=[];

function buildPolPaths(){
  POLP=CS.map(function(c,i){
    if(!RINGS[i].length) return null;
    var p=new Path2D();
    RINGS[i].forEach(function(a){
      p.moveTo(a[0],a[1]);
      for(var k=2;k<a.length;k+=2) p.lineTo(a[k],a[k+1]);
      p.closePath();
    });
    return p;
  });
}
function paintFills(){
  var data=DS.ind!=='cont';
  pg.setTransform(1,0,0,1,0,0); pg.clearRect(0,0,P2W,P2H);
  pg.setTransform(P2W/3600,0,0,P2H/1800,0,0);
  for(var i=0;i<CS.length;i++){
    var p=POLP[i]; if(!p) continue;
    var c=CS[i], reps=repsFor(CBOX[i]);
    pg.globalAlpha = c.off?0.26:(data?0.93:0.62);
    pg.fillStyle = c.off ? '#5A6472' : (data ? FILL[i] : (CONT[c.cn||'AS']||CONT.AS).c);
    for(var r=0;r<reps.length;r++){ pg.save(); pg.translate(reps[r],0); pg.fill(p,'evenodd'); pg.restore(); }
  }
  pg.globalAlpha=1;
}
function paintEdges(){
  eg.setTransform(1,0,0,1,0,0); eg.clearRect(0,0,P2W,P2H);
  eg.setTransform(P2W/3600,0,0,P2H/1800,0,0);
  for(var i=0;i<CS.length;i++){
    var p=POLP[i]; if(!p) continue;
    var reps=repsFor(CBOX[i]);
    for(var r=0;r<reps.length;r++){
      eg.save(); eg.translate(reps[r],0);
      eg.lineJoin='round'; eg.lineCap='round';
      eg.strokeStyle='rgba(4,10,18,.40)'; eg.lineWidth=3.6; eg.stroke(p);
      eg.strokeStyle='rgba(232,242,255,.50)'; eg.lineWidth=1.5; eg.stroke(p);
      eg.restore();
    }
  }
}
function drawPolitical(){ buildPolPaths(); paintFills(); paintEdges(); }

/* ============================================================ 5. 格式化 */
function fG(v){ if(v==null)return '—'; if(v>=1e12)return (v/1e12).toFixed(1)+'万亿'; if(v>=1e8)return (v/1e8).toFixed(0)+'亿'; return (v/1e6).toFixed(0)+'百万'; }
function fP(v){ if(v==null)return '—'; if(v>=1e8)return (v/1e8).toFixed(2)+'亿'; if(v>=1e4)return (v/1e4).toFixed(0)+'万'; return String(Math.round(v)); }
function fC(v){ if(v==null)return '—'; return v>=10000?(v/10000).toFixed(2)+'万':Math.round(v).toLocaleString('zh-CN'); }

/* ============================================================ 6. Three.js 场景 */
var canvas=$('#globe');
var renderer;
try{
  renderer=new THREE.WebGLRenderer({canvas:canvas,antialias:true,alpha:false,powerPreference:'high-performance'});
}catch(err){
  $('#fallback').classList.add('on'); $('#loader').classList.add('gone'); return;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
renderer.setSize(window.innerWidth,window.innerHeight);
renderer.setClearColor(0x02040a,1);
if(THREE.sRGBEncoding){ renderer.outputEncoding=THREE.sRGBEncoding; }

var scene=new THREE.Scene();
var camera=new THREE.PerspectiveCamera(42,window.innerWidth/window.innerHeight,0.01,4000);

function stars(count,size,color,opacity){
  var g=new THREE.BufferGeometry(), pos=new Float32Array(count*3);
  for(var i=0;i<count;i++){
    var r=80+Math.random()*320, th=Math.random()*Math.PI*2, ph=Math.acos(2*Math.random()-1);
    pos[i*3]=r*Math.sin(ph)*Math.cos(th); pos[i*3+1]=r*Math.cos(ph); pos[i*3+2]=r*Math.sin(ph)*Math.sin(th);
  }
  g.setAttribute('position',new THREE.BufferAttribute(pos,3));
  var m=new THREE.PointsMaterial({color:color,size:size,sizeAttenuation:true,transparent:true,opacity:opacity,depthWrite:false});
  return new THREE.Points(g,m);
}
scene.add(stars(5200,0.55,0xffffff,0.9));
scene.add(stars(900,1.15,0x9fc4ff,0.55));

var manager=new THREE.LoadingManager();
var tloader=new THREE.TextureLoader(manager);
function tex(url,srgb){ var t=tloader.load(url); t.anisotropy=renderer.capabilities.getMaxAnisotropy(); if(srgb&&THREE.sRGBEncoding)t.encoding=THREE.sRGBEncoding; return t; }
var dayTex=tex('__TEX_DAY__',true);
var normTex=tex('__TEX_NORMAL__',false);
var specTex=tex('__TEX_SPEC__',false);
var cloudTex=tex('__TEX_CLOUDS__',true);

var earthMat=new THREE.MeshPhongMaterial({
  map:dayTex, normalMap:normTex, normalScale:new THREE.Vector2(0.85,0.85),
  specularMap:specTex, specular:new THREE.Color(0x2b4d6e), shininess:15
});
var earth=new THREE.Mesh(new THREE.SphereGeometry(1,128,72), earthMat);
scene.add(earth);

var clouds=new THREE.Mesh(new THREE.SphereGeometry(1.006,96,54),
  new THREE.MeshLambertMaterial({map:cloudTex,transparent:true,opacity:0.82,depthWrite:false}));
scene.add(clouds);

/* 洲别图层：位于云层之上，保证边界不被云遮住 */
drawPolitical();
var polTex=new THREE.CanvasTexture(polCv);
if(THREE.sRGBEncoding) polTex.encoding=THREE.sRGBEncoding;
polTex.anisotropy=renderer.capabilities.getMaxAnisotropy();
var polMesh=new THREE.Mesh(new THREE.SphereGeometry(1.009,128,72),
  new THREE.MeshLambertMaterial({map:polTex,transparent:true,depthWrite:false,opacity:1}));
polMesh.renderOrder=2; scene.add(polMesh);

/* 边界层：与填充层同尺寸，只在上层画细线，任何染色模式下边界都清晰 */
var edgeTex=new THREE.CanvasTexture(edgeCv);
if(THREE.sRGBEncoding) edgeTex.encoding=THREE.sRGBEncoding;
edgeTex.anisotropy=renderer.capabilities.getMaxAnisotropy();
var edgeMesh=new THREE.Mesh(new THREE.SphereGeometry(1.0096,128,72),
  new THREE.MeshLambertMaterial({map:edgeTex,transparent:true,depthWrite:false,opacity:1}));
edgeMesh.renderOrder=3; scene.add(edgeMesh);

/* 悬停描边：整洲轮廓，矢量线条，任何缩放下都清晰 */
var hovGeo=new THREE.BufferGeometry();
var hovLine=new THREE.LineSegments(hovGeo,new THREE.LineBasicMaterial({color:0xFFE6C6,transparent:true,opacity:0.95,depthWrite:false}));
hovLine.renderOrder=4; scene.add(hovLine);
var HOVPOS={};
function outlineFor(key){
  if(HOVPOS[key]) return HOVPOS[key];
  var pos=[], R=1.004;
  (MEMBER[key]||[]).forEach(function(idx){
    RINGS[idx].forEach(function(a){
      for(var k=0;k+3<a.length;k+=2){
        var lo1=lonOf(a[k]), la1=latOf(a[k+1]), lo2=lonOf(a[k+2]), la2=latOf(a[k+3]);
        if(Math.abs(lo1-lo2)>100) continue;
        var c1=Math.cos(la1*RAD), c2=Math.cos(la2*RAD);
        pos.push(R*c1*Math.cos(lo1*RAD), R*Math.sin(la1*RAD), -R*c1*Math.sin(lo1*RAD),
                 R*c2*Math.cos(lo2*RAD), R*Math.sin(la2*RAD), -R*c2*Math.sin(lo2*RAD));
      }
    });
  });
  var arr=new Float32Array(pos); HOVPOS[key]=arr; return arr;
}
function setHoverContinent(key){
  if(!key){ hovGeo.setAttribute('position',new THREE.BufferAttribute(new Float32Array(0),3)); return; }
  var arr=outlineFor(key);
  hovGeo.setAttribute('position',new THREE.BufferAttribute(arr,3));
  hovGeo.computeBoundingSphere();
}

/* 大气辉光 */
function glowSprite(){
  var S=1024, cv=document.createElement('canvas'); cv.width=cv.height=S;
  var g=cv.getContext('2d');
  var grd=g.createRadialGradient(S/2,S/2,S*0.18, S/2,S/2,S*0.50);
  grd.addColorStop(0.00,'rgba(70,140,255,0)');
  grd.addColorStop(0.52,'rgba(96,168,255,0.50)');
  grd.addColorStop(0.72,'rgba(58,118,232,0.18)');
  grd.addColorStop(1.00,'rgba(28,66,164,0)');
  g.fillStyle=grd; g.beginPath(); g.arc(S/2,S/2,S/2,0,Math.PI*2); g.fill();
  var t=new THREE.CanvasTexture(cv); if(THREE.sRGBEncoding) t.encoding=THREE.sRGBEncoding;
  var m=new THREE.SpriteMaterial({map:t,transparent:true,depthWrite:false,depthTest:true,blending:THREE.AdditiveBlending,opacity:0.9});
  var sp=new THREE.Sprite(m); sp.scale.set(3.05,3.05,1); return sp;
}
scene.add(glowSprite());

var sun=new THREE.DirectionalLight(0xfff3e2,1.5); scene.add(sun);
var fill=new THREE.DirectionalLight(0x1f3f6e,0.22); fill.position.set(-4.5,-1.2,-3.2); scene.add(fill);
scene.add(new THREE.AmbientLight(0x2a3c55,0.4));

/* ============================================================ 7. 相机 / 交互 */
var START={lon:104,lat:24,r:3.3};
var state={theta:START.lon*Math.PI/180,phi:(90-START.lat)*Math.PI/180,r:5.6,vT:0,vP:0,last:0,anim:null,autoOn:true,pol:true};
var raycaster=new THREE.Raycaster();
var ndc=new THREE.Vector2();

function updateCamera(){
  var sp=Math.sin(state.phi), cp=Math.cos(state.phi);
  camera.position.set(state.r*sp*Math.cos(state.theta), state.r*cp, -state.r*sp*Math.sin(state.theta));
  camera.lookAt(0,0,0);
  var cd=camera.position.clone().normalize(), ca=Math.cos(0.55), sa=Math.sin(0.55);
  sun.position.set(cd.x*ca - cd.z*sa, cd.y+0.2, cd.x*sa + cd.z*ca).normalize().multiplyScalar(10);
}
function llToVec(lat,lon){
  var la=lat*RAD, lo=lon*RAD;
  return new THREE.Vector3(Math.cos(la)*Math.cos(lo), Math.sin(la), -Math.cos(la)*Math.sin(lo));
}
function pickCountry(x,y){
  ndc.x=(x/window.innerWidth)*2-1; ndc.y=-(y/window.innerHeight)*2+1;
  raycaster.setFromCamera(ndc,camera);
  var h=raycaster.intersectObject(earth,false);
  if(!h.length) return null;
  var p=h[0].point;
  var lat=Math.asin(clamp(p.y,-1,1))*180/Math.PI;
  var lon=Math.atan2(-p.z,p.x)*180/Math.PI;
  return pickAt(lon,lat);
}

var pointers=new Map(), drag=null, pinch=null;
function pdist(){ var a=Array.from(pointers.values()); return Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y); }
canvas.addEventListener('pointerdown',function(e){
  if(e.pointerType==='mouse' && e.button!==0) return;
  pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  try{ canvas.setPointerCapture(e.pointerId); }catch(_){}
  state.last=performance.now(); state.anim=null; state.vT=0; state.vP=0;
  if(pointers.size===2){ pinch={d0:pdist()||1,r0:state.r}; drag=null; }
  else if(pointers.size===1){ drag={x:e.clientX,y:e.clientY,moved:false}; }
  hideHover();
});
canvas.addEventListener('pointermove',function(e){
  if(pointers.has(e.pointerId)) pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(pointers.size>=2 && pinch){
    var d=pdist()||1; state.r=clamp(pinch.r0*pinch.d0/d,1.6,7); state.last=performance.now(); return;
  }
  if(drag){
    var dx=e.clientX-drag.x, dy=e.clientY-drag.y;
    if(Math.abs(dx)+Math.abs(dy)>4) drag.moved=true;
    state.theta-=dx*0.0048;
    state.phi=clamp(state.phi-dy*0.0048,0.14,Math.PI-0.14);
    state.vT=-dx*0.0048; state.vP=-dy*0.0048;
    drag.x=e.clientX; drag.y=e.clientY; state.last=performance.now();
    return;
  }
  hoverPick(e.clientX,e.clientY);
});
function endPointer(e){
  if(pointers.has(e.pointerId)) pointers.delete(e.pointerId);
  try{ canvas.releasePointerCapture(e.pointerId); }catch(_){}
  if(pointers.size<2) pinch=null;
  if(pointers.size===0){
    if(drag && !drag.moved){
      var hit=pickCountry(drag.x,drag.y);
      if(hit) openContinent(hit.cn||'AS',drag.x,drag.y);
    }
    drag=null; state.last=performance.now();
  }
}
canvas.addEventListener('pointerup',endPointer);
canvas.addEventListener('pointercancel',endPointer);
canvas.addEventListener('wheel',function(e){
  e.preventDefault(); state.last=performance.now(); state.anim=null; state.vT=0; state.vP=0;
  state.r=clamp(state.r*Math.exp(e.deltaY*0.0011),1.6,7);
},{passive:false});
canvas.addEventListener('dblclick',goHome);

$('#zin').onclick=function(){ state.r=clamp(state.r/1.32,1.6,7); state.last=performance.now(); };
$('#zout').onclick=function(){ state.r=clamp(state.r*1.32,1.6,7); state.last=performance.now(); };
$('#auto').onclick=function(e){
  e.stopPropagation();
  state.autoOn=!state.autoOn;
  $('#auto').classList.toggle('on',state.autoOn);
  state.last=performance.now();
};
function setPolVis(){
  // 数据染色时政区层必须常显，否则切到「卫星」就看不到颜色了
  var show=state.pol || DS.ind!=='cont';
  polMesh.visible=show; edgeMesh.visible=show;
  $('#cregion').style.opacity=state.pol?'1':'.35';
}
$('#pol').onclick=function(e){
  e.stopPropagation();
  state.pol=!state.pol;
  $('#pol').classList.toggle('on',state.pol);
  $('#pol').textContent=state.pol?'洲别':'卫星';
  setPolVis();
  updateCx();
};
$('#zreset').onclick=goHome;
function goHome(){
  if(CV.open){ closeOverlay(); return; }
  setHoverContinent(null); hideHover();
  var th=START.lon*RAD, ph=(90-START.lat)*RAD;
  while(th-state.theta>Math.PI) th-=2*Math.PI;
  while(th-state.theta<-Math.PI) th+=2*Math.PI;
  state.anim={t0:performance.now(),dur:1100,from:{theta:state.theta,phi:state.phi,r:state.r},to:{theta:th,phi:ph,r:START.r}};
  state.last=performance.now(); state.vT=0; state.vP=0;
}
function flyTo(lon,lat,r,dur){
  var th=lon*RAD, ph=(90-lat)*RAD;
  while(th-state.theta>Math.PI) th-=2*Math.PI;
  while(th-state.theta<-Math.PI) th+=2*Math.PI;
  state.anim={t0:performance.now(),dur:dur||900,from:{theta:state.theta,phi:state.phi,r:state.r},to:{theta:th,phi:ph,r:r||1.95}};
  state.vT=0; state.vP=0; state.last=performance.now();
}

/* ============================================================ 8. 球面上的大洲标签 */
var CX={};
(function(){
  var box=$('#cx');
  CORDER.forEach(function(k){
    var K=CONT[k], el=document.createElement('div');
    el.className='cx';
    el.innerHTML='<i style="background:'+K.c+';color:'+K.c+'"></i>'+K.n+'<em>'+((MEMBER[k]||[]).length)+' 国</em>';
    box.appendChild(el); CX[k]=el;
  });
  // 左侧大洲索引
  var rows=$('#cregion-rows');
  CORDER.forEach(function(k){
    var K=CONT[k], b=document.createElement('button');
    b.innerHTML='<i style="background:'+K.c+';color:'+K.c+'"></i>'+K.n+'<em>'+((MEMBER[k]||[]).length)+'</em>';
    b.onmouseenter=function(){ if(state.pol) setHoverContinent(k); };
    b.onmouseleave=function(){ setHoverContinent(null); };
    b.onclick=function(e){ e.stopPropagation(); openContinent(k,window.innerWidth/2,window.innerHeight/2); };
    rows.appendChild(b);
  });
})();

var _v=new THREE.Vector3();
function updateCx(){
  var show=!CV.open && state.pol;
  var camDir=_v.copy(camera.position).normalize();
  var scale=clamp(2.4/state.r,0.86,1.45);
  CORDER.forEach(function(k){
    var K=CONT[k], el=CX[k];
    if(!show){ el.style.opacity=0; return; }
    var pt=llToVec(K.lat,K.lon).multiplyScalar(1.02);
    var facing=pt.clone().normalize().dot(camDir);
    if(facing<0.12){ el.style.opacity=0; return; }
    var pr=pt.project(camera);
    if(pr.z>1){ el.style.opacity=0; return; }
    var sx=(pr.x*0.5+0.5)*window.innerWidth, sy=(-pr.y*0.5+0.5)*window.innerHeight;
    if(sx<-120||sx>window.innerWidth+120||sy<-80||sy>window.innerHeight+80){ el.style.opacity=0; return; }
    el.style.transform='translate('+sx.toFixed(1)+'px,'+sy.toFixed(1)+'px) translate(-50%,-50%) scale('+scale.toFixed(3)+')';
    el.style.opacity=clamp((facing-0.12)/0.2,0,1).toFixed(2);
  });
}

/* ============================================================ 9. 悬停（球面显示大洲） */
var hoverRaf=0, hoverKey=null;
function hoverPick(x,y){
  if(CV.open) return;
  if(hoverRaf) return;
  hoverRaf=requestAnimationFrame(function(){
    hoverRaf=0;
    var c=pickCountry(x,y), k=c?(c.cn||'AS'):null;
    if(k!==hoverKey){
      hoverKey=k;
      if(k){ showHover(k,x,y); setHoverContinent(k); } else { hideHover(); setHoverContinent(null); }
      canvas.style.cursor=k?'pointer':'grab';
    }
    else if(k){ moveHover(x,y); }
  });
}
function showHover(k,x,y){
  var h=$('#hover'), K=CONT[k], n=(MEMBER[k]||[]).length;
  h.innerHTML='<i class="cd" style="background:'+K.c+';box-shadow:0 0 8px '+K.c+'"></i>'+K.n+
              '<em>'+K.e+' · '+n+' 国</em><u>点击查看国家 →</u>';
  h.classList.add('on'); moveHover(x,y);
}
function moveHover(x,y){ var h=$('#hover'); h.style.left=x+'px'; h.style.top=y+'px'; }
function hideHover(){ hoverKey=null; $('#hover').classList.remove('on'); }

/* ============================================================ 10. 视图（洲 / 国）
   局部等距投影：x=(lon-lon0)·cos(lat0)，y=-(lat-lat0)，单位「度（已校正）」。
   矢量重绘（不是贴图放大），所以任意缩放都清晰。 */
var LBL=[];
var CV={open:false,mode:'k',key:null,c:null,zoom:1,px:0,py:0,k:1,ox:0,oy:0,w:0,h:0,dpr:1,
  cos0:1,flon:0,flat:0,pr:[],cities:[],drag:null,raf:0,hov:null};
var NAV={prev:'globe'};
var ccanvas=$('#cmap'), cctx=ccanvas.getContext('2d');

function projRings(focus){
  var cos0=Math.cos(focus.clat*RAD);
  CV.cos0=cos0; CV.flon=focus.clon; CV.flat=focus.clat;
  var out=[];
  CS.forEach(function(cc,i){
    var rings=[], x0=1e9,y0=1e9,x1=-1e9,y1=-1e9, items=[];
    RINGS[i].forEach(function(a){
      var lo0=lonOf(a[0]);
      var shift=-360*Math.round((lo0-focus.clon)/360);
      var arr=new Float32Array(a.length);
      var rx0=1e9,ry0=1e9,rx1=-1e9,ry1=-1e9;
      for(var k=0;k<a.length;k+=2){
        var x=(lonOf(a[k])+shift-focus.clon)*cos0;
        var y=-(latOf(a[k+1])-focus.clat);
        arr[k]=x; arr[k+1]=y;
        if(x<rx0)rx0=x; if(x>rx1)rx1=x;
        if(y<ry0)ry0=y; if(y>ry1)ry1=y;
      }
      rings.push(arr);
      items.push({bb:[rx0,ry0,rx1,ry1],a:(rx1-rx0)*(ry1-ry0)});
    });
    // 取景范围：以最大陆块为锚，过滤掉远处的飞地/远洋小岛
    var main=items[0]||{bb:[0,0,0,0],a:0};
    items.forEach(function(it){ if(it.a>main.a) main=it; });
    var mcx=(main.bb[0]+main.bb[2])/2, mcy=(main.bb[1]+main.bb[3])/2;
    var scale=Math.max(main.bb[2]-main.bb[0], main.bb[3]-main.bb[1], 1e-4);
    items.forEach(function(it){
      var cx=(it.bb[0]+it.bb[2])/2, cy=(it.bb[1]+it.bb[3])/2;
      var d=Math.sqrt((cx-mcx)*(cx-mcx)+(cy-mcy)*(cy-mcy));
      if(d>scale*1.05 && it.a<main.a*0.9) return;
      if(it.bb[0]<x0)x0=it.bb[0]; if(it.bb[2]>x1)x1=it.bb[2];
      if(it.bb[1]<y0)y0=it.bb[1]; if(it.bb[3]>y1)y1=it.bb[3];
    });
    out.push({i:i,c:cc,rings:rings,bb:[x0,y0,x1,y1]});
  });
  return out;
}

function viewMargins(){
  if(CV.w<980) return {l:56,r:56,t:118,b:96};
  return {l:Math.min(348,CV.w*0.25), r:214+70, t:126, b:112};
}
function frameRect(bb,l,r,t,b){
  var bw=Math.max(bb[2]-bb[0],1e-6), bh=Math.max(bb[3]-bb[1],1e-6);
  var aw=Math.max(CV.w-l-r,80), ah=Math.max(CV.h-t-b,80);
  CV.k=Math.min(aw/bw, ah/bh);
  CV.ox=l+aw/2-(bb[0]+bb[2])/2*CV.k;
  CV.oy=t+ah/2-(bb[1]+bb[3])/2*CV.k;
}

/* ---- 进入洲 ---- */
function openContinent(key,sx,sy){
  var K=CONT[key]; if(!K) return;
  var wasOpen=CV.open;
  if(wasOpen && CV.mode==='c') NAV.prev='globe';
  CV.mode='k'; CV.key=key; CV.c=null; CV.cities=[]; CV.hov=null;
  CV.open=true;                      // 先置位，drawView 才肯画
  CV.zoom=1; CV.px=0; CV.py=0;
  CV.pr=projRings({clon:K.lon,clat:K.lat});
  sizeViewCanvas();
  var cos0=CV.cos0;
  var bb=[(K.box[0]-K.lon)*cos0, -(K.box[3]-K.lat), (K.box[1]-K.lon)*cos0, -(K.box[2]-K.lat)];
  var m=viewMargins();
  frameRect(bb,m.l,m.r,m.t,m.b);
  NAV.prev='globe';
  fillHudContinent(key);
  drawView();
  flyTo(K.lon,K.lat,1.85,950);
  showOverlay(wasOpen,sx,sy);
}

/* ---- 进入国家 ---- */
function openCountry(c,sx,sy){
  if(!c) return;
  var wasOpen=CV.open;
  NAV.prev=(wasOpen && CV.mode==='k' && (c.cn||'AS')===CV.key)?CV.key:'globe';
  CV.mode='c'; CV.c=c; CV.key=c.cn||'AS'; CV.hov=null;
  CV.open=true;
  CV.zoom=1; CV.px=0; CV.py=0;
  CV.pr=projRings(c);
  sizeViewCanvas();
  var me=CV.pr[CS.indexOf(c)], bb=me.bb;
  var l=CV.w*0.15, r=CV.w*0.15, t=CV.h*0.13, b=CV.h*0.13;
  frameRect(bb,l,r,t,b);
  CV.k=Math.min(CV.k,900);
  CV.ox=CV.w/2-(bb[0]+bb[2])/2*CV.k;
  CV.oy=CV.h/2-(bb[1]+bb[3])/2*CV.k;
  CV.cities=(c.city||[]).map(function(ct){
    var dl=ct.lo-c.clon;
    while(dl>180) dl-=360; while(dl<-180) dl+=360;
    return {n:ct.n,e:ct.e,p:ct.p,cap:ct.c,x:dl*CV.cos0,y:-(ct.la-c.clat)};
  });
  fillHudCountry(c);
  drawView();
  flyTo(c.clon,c.clat,1.95,900);
  showOverlay(wasOpen,sx,sy);
}

function showOverlay(wasOpen,sx,sy){
  var el=$('#country');
  $('#globe').classList.add('dive');
  $('#hint').classList.add('gone');
  $('#dock').classList.add('hide');
  $('#rank').classList.add('hide');
  $('#cmp').classList.add('ov');
  if(!wasOpen){
    el.style.transition='none';
    el.style.transformOrigin=(sx!=null?sx:window.innerWidth/2)+'px '+(sy!=null?sy:window.innerHeight/2)+'px';
    el.style.transform='scale(.06)'; el.style.opacity='0';
    el.classList.add('on');
    CV.open=true;
    requestAnimationFrame(function(){
      el.style.transition='transform .6s cubic-bezier(.16,.86,.24,1),opacity .36s ease-out';
      el.style.transform='scale(1)'; el.style.opacity='1';
    });
    requestAnimationFrame(showCanvasIn);
  }else{
    CV.open=true;
    showCanvasIn();
  }
}
function showCanvasIn(){
  var cv=$('#cmap');
  cv.style.transition='none'; cv.style.opacity='0'; cv.style.transform='scale(1.05)';
  requestAnimationFrame(function(){
    cv.style.transition='opacity .26s ease-out,transform .46s cubic-bezier(.2,.9,.25,1)';
    cv.style.opacity='1'; cv.style.transform='scale(1)';
  });
}
function closeOverlay(cb){
  if(!CV.open) return;
  CV.open=false;
  var el=$('#country');
  el.style.transition='transform .42s cubic-bezier(.5,0,.75,.2),opacity .34s ease-in';
  el.style.transform='scale(.12)'; el.style.opacity='0';
  $('#globe').classList.remove('dive');
  $('#dock').classList.remove('hide');
  $('#rank').classList.remove('hide');
  $('#cmp').classList.remove('ov');
  setTimeout(function(){
    el.classList.remove('on'); el.style.transform='scale(1)';
    $('#cmap').style.opacity=''; $('#cmap').style.transform='';
    if(cb) cb();
  },450);
}
/* 返回上一级：国 → 洲 → 地球 */
function back(){
  if(!CV.open) return;
  if(CV.mode==='c' && CONT[NAV.prev]) openContinent(NAV.prev);
  else closeOverlay();
}
$('#cback').onclick=function(){ back(); };

function sizeViewCanvas(){
  var w=window.innerWidth, h=window.innerHeight, dpr=Math.min(window.devicePixelRatio||1,2);
  CV.w=w; CV.h=h; CV.dpr=dpr;
  ccanvas.width=Math.round(w*dpr); ccanvas.height=Math.round(h*dpr);
  ccanvas.style.width=w+'px'; ccanvas.style.height=h+'px';
}

/* ============================================================ 11. HUD */
function crumbHTML(parts){
  return parts.map(function(p,i){
    if(i===parts.length-1) return '<b class="cur">'+esc(p[0])+'</b>';
    return '<b data-go="'+p[1]+'">'+esc(p[0])+'</b>';
  }).join('<s>/</s>');
}
function bindCrumb(){
  Array.prototype.forEach.call($('#crumb').querySelectorAll('b[data-go]'),function(b){
    b.onclick=function(e){
      e.stopPropagation();
      var go=b.dataset.go;
      if(go==='globe') closeOverlay();
      else openContinent(go);
    };
  });
}
function contTotals(key){
  var m=MEMBER[key]||[], n=0, pop=0, gdp=0, yi=DS.yi;
  m.forEach(function(i){
    var c=CS[i]; if(c.off) return;
    n++;
    if(c.pop&&c.pop[yi]) pop+=c.pop[yi];
    if(c.gdp&&c.gdp[yi]) gdp+=c.gdp[yi];
  });
  return {n:n,pop:pop||null,gdp:gdp||null,pc:(pop&&gdp)?gdp/pop:null};
}
function setStats(cells){
  $('#cstats').innerHTML=cells.map(function(r){
    return '<div><div class="k">'+r[0]+'</div><div class="v">'+r[1]+(r[2]?'<small>'+r[2]+'</small>':'')+'</div></div>';
  }).join('');
}

function fillHudContinent(key){
  var K=CONT[key], t=contTotals(key), data=DS.ind!=='cont';
  $('#crumb').innerHTML=crumbHTML([['地球','globe'],[K.n,'']]);
  bindCrumb();
  $('#cback').querySelector('span').textContent='返回地球';
  $('#cname').textContent=K.n;
  $('#cen').textContent=K.e+' · '+t.n+' 个国家';
  $('#czone').textContent='';
  $('#cflag').style.display='none';
  var sw=$('#csw'); sw.style.display=''; sw.style.background=K.c;
  setStats([['国家',t.n,'个'],['人口',fP(t.pop),''],['GDP',fG(t.gdp),'美元'],['人均',fC(t.pc),'美元']]);

  if(data){
    var I=IND[DS.ind];
    var lo=I.log?Math.pow(10,I.log[0]):I.lin[0], hi=I.log?Math.pow(10,I.log[1]):I.lin[1];
    $('#clegend').innerHTML='<span><i style="background:'+rampAt(0.05)+';box-shadow:none"></i>'+esc(I.n)+' 低</span>'+
      '<span><i style="background:'+rampAt(0.5)+';box-shadow:none"></i>中</span>'+
      '<span><i style="background:'+rampAt(0.95)+';box-shadow:none"></i>高</span>'+
      '<span style="color:#7C8CA0">'+fmtVal(DS.ind,lo)+' → '+fmtVal(DS.ind,hi)+' '+esc(I.u)+' · '+YEARS[DS.yi]+'</span>';
  }else{
    $('#clegend').innerHTML='<span><i style="background:'+K.c+';box-shadow:0 0 8px '+K.c+'"></i>本洲国家</span>'+
      '<span><i class="dim"></i>其他洲（仅作参照）</span>';
  }
  $('#chelp').innerHTML='<b>滚轮</b>缩放 · <b>拖拽</b>平移 · 点<b>国家</b>看城市 · <b>ESC</b> 返回';
  $('#ccities').style.display='none';
  $('#cscale').classList.add('on');

  var yi=DS.yi;
  var rows=(MEMBER[key]||[]).slice().sort(function(a,b){
    if(data) return (valOf(CS[b],DS.ind)||0)-(valOf(CS[a],DS.ind)||0);
    return (CS[b].gdp?CS[b].gdp[yi]||0:0)-(CS[a].gdp?CS[a].gdp[yi]||0:0) || CS[a].n.localeCompare(CS[b].n,'zh');
  });
  $('#clist-n').textContent=rows.length+' 国';
  $('#clist-rows').innerHTML=rows.map(function(i){
    var c=CS[i], v=data?valOf(c,DS.ind):(c.gdp?c.gdp[yi]:null);
    return '<button data-i="'+i+'">'+(c.fi?'<img src="'+c.fi+'" alt="">':'')+
      '<span>'+esc(c.n)+'</span><em>'+(data?fmtVal(DS.ind,v):(v?fG(v):'—'))+'</em></button>';
  }).join('');
  $('#clist-rows').querySelectorAll('button').forEach(function(b){
    b.onclick=function(e){ e.stopPropagation(); openCountry(CS[+b.dataset.i]); };
  });
  $('#clist').classList.add('on');
}

function fillHudCountry(c){
  var yi=DS.yi;
  var g=c.gdp?c.gdp[yi]:null, p=c.pop?c.pop[yi]:null, pc=c.pc?c.pc[yi]:null, le=c.le?c.le[yi]:null;
  var K=CONT[c.cn||'AS']||CONT.AS;
  $('#crumb').innerHTML=crumbHTML([['地球','globe'],[K.n,c.cn||'AS'],[c.n,'']]);
  bindCrumb();
  $('#cback').querySelector('span').textContent=(CONT[NAV.prev]?'返回'+CONT[NAV.prev].n:'返回地球');
  $('#cname').textContent=c.n;
  $('#cen').textContent=c.en;
  $('#czone').textContent=(CONT[c.cn]?CONT[c.cn].n+' · ':'')+(c.reg||'')+(c.inc&&c.inc!=='—'?' · '+c.inc:'')+' · '+YEARS[yi]+' 年';
  var fl=$('#cflag');
  if(c.fi){ fl.src=c.fi; fl.style.display=''; } else { fl.style.display='none'; }
  $('#csw').style.display='none';
  setStats([['GDP',g==null?'—':fG(g),g==null?'':'美元'],
            ['人口',p==null?'—':fP(p),''],
            ['人均 GDP',pc==null?'—':fC(pc),pc==null?'':'美元'],
            ['预期寿命',le==null?'—':le.toFixed(1),le==null?'':'岁'],
            ['城市',String((c.city||[]).length),'个']]);
  var added=DS.cmp.indexOf(c)>=0;
  $('#cadd').classList.toggle('on',added);
  $('#cadd').innerHTML= added?'✓ 已加入对比':'<span>＋</span>加入对比';

  $('#clegend').innerHTML='<span><i class="cap"></i>首都</span><span><i></i>城市（点越大人口越多）</span>';
  $('#chelp').innerHTML='<b>滚轮</b>缩放 · <b>拖拽</b>平移 · 点<b>邻国</b>切换 · <b>ESC</b> 返回';
  $('#clist').classList.remove('on');

  var list=(CV.cities||[]).slice().sort(function(a,b){ return (b.cap-a.cap)||(b.p-a.p); }).slice(0,12);
  var bar=$('#ccities');
  if(list.length){
    bar.style.display='';
    bar.innerHTML='<b>城市 '+CV.cities.length+'</b>'+list.map(function(ct,i){
      return '<button data-ci="'+i+'">'+(ct.cap?'<i class="cap"></i>':'')+esc(ct.n)+
             (ct.p?'<em>'+fP(ct.p)+'</em>':'')+'</button>';
    }).join('');
    bar.querySelectorAll('button').forEach(function(btn){
      btn.onclick=function(e){
        e.stopPropagation();
        var ct=list[+btn.dataset.ci]; if(!ct) return;
        flyToCity(ct);
      };
    });
  }else{
    bar.style.display='none'; bar.innerHTML='';
  }
}

/* ============================================================ 12. 绘制 */
function drawView(){ if(!CV.open) return; if(CV.mode==='k') drawContinentView(); else drawCountryView(); }
function drawSea(g,w,h){
  var bg=g.createLinearGradient(0,0,w,h);
  bg.addColorStop(0,'#071019'); bg.addColorStop(.55,'#081320'); bg.addColorStop(1,'#050a12');
  g.fillStyle=bg; g.fillRect(0,0,w,h);
}
function drawGrid(g,k,ox,oy,step){
  var w=CV.w,h=CV.h;
  g.save(); g.beginPath(); g.rect(0,0,w,h); g.clip();
  g.strokeStyle='rgba(96,132,178,.13)'; g.lineWidth=1;
  var lat0=Math.round(CV.flat/step)*step;
  for(var d=-6;d<=6;d++){
    var la=lat0+d*step; if(la<-85||la>85) continue;
    var y=oy-(la-CV.flat)*k;
    if(y>-1&&y<h+1){ g.beginPath(); g.moveTo(0,y); g.lineTo(w,y); g.stroke(); }
  }
  var lon0=Math.round(CV.flon/step)*step;
  for(var d2=-18;d2<=18;d2++){
    var lo=lon0+d2*step;
    var x=ox+((lo-CV.flon)*CV.cos0)*k;
    if(x>-1&&x<w+1){ g.beginPath(); g.moveTo(x,0); g.lineTo(x,h); g.stroke(); }
  }
  g.restore();
}
function pathOf(g,rings,ox,oy,k){
  rings.forEach(function(a){
    g.moveTo(ox+a[0]*k, oy+a[1]*k);
    for(var i=2;i<a.length;i+=2) g.lineTo(ox+a[i]*k, oy+a[i+1]*k);
    g.closePath();
  });
}

/* ---- 洲视图：全部成员国同色系区分 + 中文国名 + 右侧清单 ---- */
function drawContinentView(){
  var g=cctx,w=CV.w,h=CV.h,dpr=CV.dpr,k=CV.k*CV.zoom,ox=CV.ox+CV.px,oy=CV.oy+CV.py;
  g.setTransform(dpr,0,0,dpr,0,0);
  g.save();
  drawSea(g,w,h);
  drawGrid(g,k,ox,oy,10);

  var mem={}; (MEMBER[CV.key]||[]).forEach(function(i){ mem[i]=1; });

  // 其他洲：极暗，只留地理参照
  g.save();
  g.beginPath(); g.rect(0,0,w,h); g.clip();
  CV.pr.forEach(function(o){
    if(mem[o.i]) return;
    var bb=o.bb;
    if(bb[2]*k+ox<-40||bb[0]*k+ox>w+40||bb[3]*k+oy<-40||bb[1]*k+oy>h+40) return;
    g.beginPath(); pathOf(g,o.rings,ox,oy,k);
    g.fillStyle='rgba(30,41,56,.62)';
    g.fill('evenodd');
    g.strokeStyle='rgba(110,140,180,.14)'; g.lineWidth=1; g.stroke();
  });
  // 本洲国家：同色系不同明度，边界清晰
  CV.pr.forEach(function(o){
    if(!mem[o.i]) return;
    var bb=o.bb;
    if(bb[2]*k+ox<-40||bb[0]*k+ox>w+40||bb[3]*k+oy<-40||bb[1]*k+oy>h+40) return;
    g.beginPath(); pathOf(g,o.rings,ox,oy,k);
    g.fillStyle=FILL[o.i];
    g.fill('evenodd');
    g.strokeStyle='rgba(6,12,20,.72)'; g.lineWidth=1.1; g.lineJoin='round'; g.stroke();
    if(CV.hov===o.i){
      g.save();
      g.shadowColor='rgba(255,214,170,.85)'; g.shadowBlur=12;
      g.strokeStyle='rgba(255,228,190,.95)'; g.lineWidth=1.8; g.stroke();
      g.restore();
    }
  });
  g.restore();

  // 国名：面积大的先放，放不下就不放（宁可少，不要糊）。
  // 极小国（比荷卢、高加索这类）不硬塞进国土：画定位点 + 引线，标签挪到境外空白处。
  var items=[];
  CV.pr.forEach(function(o){
    if(!mem[o.i]) return;
    var c=o.c;
    var x=((c.clon-CV.flon)*CV.cos0)*k+ox;
    var y=-(c.clat-CV.flat)*k+oy;
    var wp=(o.bb[2]-o.bb[0])*k, hp=(o.bb[3]-o.bb[1])*k;
    if(wp<34||hp<12) return;
    var tiny=(wp<52||hp<17);
    if(x<30||x>w-30||y<50||y>h-40){
      // 质心在屏幕外（如欧洲视图里的俄罗斯）：用可见部分的中心标注
      var ix0=Math.max(o.bb[0]*k+ox,30), ix1=Math.min(o.bb[2]*k+ox,w-30);
      var iy0=Math.max(o.bb[1]*k+oy,50), iy1=Math.min(o.bb[3]*k+oy,h-40);
      if(ix1-ix0<46||iy1-iy0<20) return;
      x=(ix0+ix1)/2; y=(iy0+iy1)/2; tiny=false;
    }
    items.push({x:x,y:y,t:c.n,a:(c.ar||0),tiny:tiny});
  });
  items.sort(function(a,b){ return (b.a-a.a)||(b.tiny?0:-1); });
  g.save();
  g.font='600 12px "PingFang SC","Microsoft YaHei",sans-serif';
  g.textBaseline='middle'; g.textAlign='left';
  var placed=[]; LBL.length=0;
  var hits=function(box){
    if(box[0]<10||box[2]>w-10||box[1]<8||box[3]>h-8) return true;
    for(var j=0;j<placed.length;j++){
      var q=placed[j];
      if(box[0]<q[2]&&box[2]>q[0]&&box[1]<q[3]&&box[3]>q[1]) return true;
    }
    return false;
  };
  var paint=function(txt,tx,ty,align){
    g.textAlign=align;
    g.lineWidth=3.4; g.strokeStyle='rgba(4,9,16,.92)'; g.strokeText(txt,tx,ty);
    g.fillStyle='#F4EEE4'; g.fillText(txt,tx,ty);
  };
  items.forEach(function(it){
    var tw=g.measureText(it.t).width, th=15;
    var tx,ty;
    if(it.tiny){
      // 极小国：定位点 + 引线，8 方向 × 3 档半径找空白
      var DIRS=[[1,0],[0,-1],[0,1],[-1,0],[0.7,-0.7],[0.7,0.7],[-0.7,-0.7],[-0.7,0.7]];
      var ok=false;
      for(var r=0;r<3&&!ok;r++){
        var rad=[18,30,44][r];
        for(var d=0;d<DIRS.length&&!ok;d++){
          var ux=DIRS[d][0], uy=DIRS[d][1];
          var lx=it.x+ux*rad+(ux>0?5:ux<0?-5-tw:0), ly=it.y+uy*rad+(uy? (uy<0?-th/2-2:th/2+2) :0);
          var box=[ux<0? lx-tw-3 : lx-3, ly-th/2-1, ux<0? lx+3 : lx+tw+3, ly+th/2+1];
          if(!hits(box)){
            g.save();
            g.beginPath(); g.moveTo(it.x+ux*5,it.y+uy*5);
            g.lineTo(lx-ux*3, ly-uy*(uy?th/2+2:0));
            g.strokeStyle='rgba(244,238,228,.55)'; g.lineWidth=1; g.stroke();
            g.beginPath(); g.arc(it.x,it.y,2.4,0,6.2832);
            g.fillStyle='#F4EEE4'; g.fill();
            g.strokeStyle='rgba(4,9,16,.9)'; g.lineWidth=1.2; g.stroke();
            g.restore();
            paint(it.t,lx,ly, ux<0?'right':'left');
            placed.push(box);
            LBL.push({n:it.t,x:lx,y:ly});
            ok=true;
          }
        }
      }
      if(!ok){
        var fb=[it.x-tw/2-3,it.y-th/2-1,it.x+tw/2+3,it.y+th/2+1];
        paint(it.t,it.x-tw/2,it.y,'left');
        placed.push(fb); LBL.push({n:it.t,x:it.x-tw/2,y:it.y});
      }
      return;
    }
    var cands=[[it.x-tw/2,it.y],[it.x+6,it.y],[it.x-6-tw,it.y],
               [it.x-tw/2,it.y-16],[it.x-tw/2,it.y+16],
               [it.x+4,it.y-13],[it.x+4,it.y+13],[it.x-4-tw,it.y-13],[it.x-4-tw,it.y+13]];
    for(var i=0;i<cands.length;i++){
      tx=cands[i][0]; ty=cands[i][1];
      if(hits([tx-3,ty-th/2-1,tx+tw+3,ty+th/2+1])) continue;
      placed.push([tx-3,ty-th/2-1,tx+tw+3,ty+th/2+1]);
      paint(it.t,tx,ty,'left');
      LBL.push({n:it.t,x:tx,y:ty});
      break;
    }
  });
  g.restore();
  g.restore();
  updateScaleBar(k);
}

/* ---- 国家视图：本国橙色浮雕 + 邻国压暗 + 城市点 ---- */
function drawCountryView(){
  var g=cctx,w=CV.w,h=CV.h,dpr=CV.dpr,k=CV.k*CV.zoom,ox=CV.ox+CV.px,oy=CV.oy+CV.py;
  g.setTransform(dpr,0,0,dpr,0,0);
  g.save();
  drawSea(g,w,h);
  drawGrid(g,k,ox,oy,10);
  g.save();
  g.beginPath(); g.rect(0,0,w,h); g.clip();

  // 邻国（先画，本国后画压在上面）
  var meIdx=CS.indexOf(CV.c);
  CV.pr.forEach(function(o){
    if(o.i===meIdx) return;
    var bb=o.bb;
    if(bb[2]*k+ox<-40||bb[0]*k+ox>w+40||bb[3]*k+oy<-40||bb[1]*k+oy>h+40) return;
    g.beginPath(); pathOf(g,o.rings,ox,oy,k);
    // 邻国只作定位参照：放大越深越淡
    var nf=clamp(0.62-(k-30)/620,0.22,0.62);
    g.fillStyle=o.c.off?'rgba(58,70,86,'+(nf*0.66).toFixed(3)+')':'rgba(46,62,84,'+nf.toFixed(3)+')';
    g.fill('evenodd');
    g.strokeStyle='rgba(120,150,190,'+(nf*0.42).toFixed(3)+')'; g.lineWidth=1; g.stroke();
  });

  // 本国
  var me=CV.pr[meIdx];
  g.beginPath(); pathOf(g,me.rings,ox,oy,k);
  var cx0=(me.bb[0]+me.bb[2])/2*k+ox, cy0=(me.bb[1]+me.bb[3])/2*k+oy;
  var rr=Math.max((me.bb[2]-me.bb[0])*k,(me.bb[3]-me.bb[1])*k)*0.62;
  var land=g.createRadialGradient(cx0,cy0,0,cx0,cy0,Math.max(rr,60));
  land.addColorStop(0,'rgba(246,186,126,.38)');
  land.addColorStop(.62,'rgba(240,168,104,.26)');
  land.addColorStop(1,'rgba(226,150,88,.19)');
  g.fillStyle=land; g.fill('evenodd');
  g.save();
  g.shadowColor='rgba(240,168,104,.85)'; g.shadowBlur=16;
  g.strokeStyle='#F3AE6C'; g.lineWidth=2.2; g.lineJoin='round'; g.stroke();
  g.restore();
  g.restore();

  // 邻国国名（帮助定位）
  g.save();
  g.beginPath(); g.rect(0,0,w,h); g.clip();
  g.font='500 11px "PingFang SC","Microsoft YaHei",sans-serif';
  g.textAlign='center'; g.fillStyle='rgba(190,208,230,.5)';
  CV.pr.forEach(function(o){
    if(o.i===meIdx||o.c.off) return;
    var bb=o.bb;
    if(bb[2]*k+ox<-20||bb[0]*k+ox>w+20||bb[3]*k+oy<-20||bb[1]*k+oy>h+20) return;
    if((bb[2]-bb[0])*k<54||(bb[3]-bb[1])*k<26) return;
    g.fillText(o.c.n, ox+(bb[0]+bb[2])/2*k, oy+(bb[1]+bb[3])/2*k);
  });
  g.restore();
  g.restore();

  drawCities(g,k,ox,oy);
  updateScaleBar(k);
}

function drawCities(g,k,ox,oy){
  var w=CV.w,h=CV.h;
  var list=CV.cities.filter(function(ct){
    var x=ox+ct.x*k, y=oy+ct.y*k;
    return x>-60&&x<w+60&&y>-40&&y<h+40;
  }).sort(function(a,b){ return (b.cap-a.cap)||(b.p-a.p); });
  function rOf(ct){ return ct.cap?4.8:clamp(2+Math.log10(1+ct.p/1e5)*1.9,2.2,5.6); }
  g.save();
  list.forEach(function(ct){
    var x=ox+ct.x*k, y=oy+ct.y*k, r=rOf(ct);
    if(ct.cap){
      g.beginPath(); g.arc(x,y,r+3.4,0,Math.PI*2); g.fillStyle='rgba(240,168,104,.20)'; g.fill();
      g.beginPath(); g.arc(x,y,r,0,Math.PI*2); g.fillStyle='#fff'; g.fill();
      g.lineWidth=1.6; g.strokeStyle='rgba(240,168,104,.95)'; g.stroke();
    }else{
      g.beginPath(); g.arc(x,y,r,0,Math.PI*2); g.fillStyle='rgba(255,214,170,.95)'; g.fill();
      g.lineWidth=1; g.strokeStyle='rgba(30,22,14,.65)'; g.stroke();
    }
  });
  // 标签：右、左、上、下依次尝试，都放不下就不标
  g.font='600 12px "PingFang SC","Microsoft YaHei",sans-serif';
  g.textBaseline='middle'; g.textAlign='left';
  var placed=[];
  list.forEach(function(ct){
    var x=ox+ct.x*k, y=oy+ct.y*k, r=rOf(ct);
    var nearMin=ct.cap?13:19, crowd=false;
    for(var qq=0;qq<list.length;qq++){
      if(list[qq]===ct) break;
      var ax=ox+list[qq].x*k, ay=oy+list[qq].y*k;
      var dx=ax-x, dy=ay-y;
      if(dx*dx+dy*dy < nearMin*nearMin){ crowd=true; break; }
    }
    if(crowd) return;
    var tw=g.measureText(ct.n).width, th=15;
    var cands=[[x+r+7,y],[x-r-7-tw,y],[x+r+7,y-17],[x+r+7,y+17],[x-r-7-tw,y-17]];
    for(var i=0;i<cands.length;i++){
      var tx=cands[i][0], ty=cands[i][1];
      var box=[tx-3,ty-th/2-1,tx+tw+3,ty+th/2+1];
      if(box[0]<8||box[2]>w-8||box[1]<8||box[3]>h-8) continue;
      var bad=false, j;
      for(j=0;j<placed.length;j++){
        var q=placed[j];
        if(box[0]<q[2]&&box[2]>q[0]&&box[1]<q[3]&&box[3]>q[1]){ bad=true; break; }
      }
      if(!bad){
        for(j=0;j<list.length;j++){
          if(list[j]===ct) continue;
          var px2=ox+list[j].x*k, py2=oy+list[j].y*k;
          if(px2+6>box[0]&&px2-6<box[2]&&py2+6>box[1]&&py2-6<box[3]){ bad=true; break; }
        }
      }
      if(bad) continue;
      placed.push(box);
      g.lineWidth=3.4; g.strokeStyle='rgba(4,9,16,.92)'; g.strokeText(ct.n,tx,ty);
      g.fillStyle=ct.cap?'#FFFFFF':'#F2E6D6';
      g.fillText(ct.n,tx,ty);
      break;
    }
  });
  g.restore();
}

function updateScaleBar(k){
  var kmPerPx=111.32/k;
  var target=kmPerPx*110;
  var pow=Math.pow(10,Math.floor(Math.log10(target)));
  var mult=target/pow>=5?5:(target/pow>=2?2:1);
  var km=mult*pow, pxw=km/kmPerPx;
  var el=$('#cscale');
  el.classList.add('on');
  el.style.setProperty('--w',pxw.toFixed(0)+'px');
  el.querySelector('em').textContent=(km>=1000?(km/1000)+' 千公里':km+' 公里');
}

/* ============================================================ 13. 视图交互 */
function flyToCity(ct){
  if(!CV.c) return;
  var k0=CV.k*CV.zoom;
  var k1=Math.min(k0*2.1, CV.k*12);
  CV.zoom=k1/CV.k;
  CV.px=CV.w/2-CV.ox-ct.x*k1;
  CV.py=CV.h*0.46-CV.oy-ct.y*k1;
  scheduleDraw();
  pulseAt(ct);
}
function pulseAt(ct){
  var el=$('#cpulse'); if(!el) return;
  var k=CV.k*CV.zoom, x=CV.ox+CV.px+ct.x*k, y=CV.oy+CV.py+ct.y*k;
  el.style.left=x+'px'; el.style.top=y+'px';
  el.classList.remove('go'); void el.offsetWidth; el.classList.add('go');
}
function cZoomAt(cx,cy,factor){
  var k0=CV.k*CV.zoom, k1=clamp(k0*factor, CV.k*0.38, CV.k*18);
  var real=k1/k0;
  CV.px=cx-(cx-(CV.ox+CV.px))*real-CV.ox;
  CV.py=cy-(cy-(CV.oy+CV.py))*real-CV.oy;
  CV.zoom=k1/CV.k;
  scheduleDraw();
}
function scheduleDraw(){
  if(CV.raf) return;
  CV.raf=requestAnimationFrame(function(){ CV.raf=0; drawView(); });
}
ccanvas.addEventListener('wheel',function(e){
  if(!CV.open) return;
  e.preventDefault();
  cZoomAt(e.clientX,e.clientY,Math.exp(-e.deltaY*0.0016));
},{passive:false});
ccanvas.addEventListener('pointerdown',function(e){
  if(e.pointerType==='mouse'&&e.button!==0) return;
  CV.drag={x:e.clientX,y:e.clientY,moved:false};
  try{ ccanvas.setPointerCapture(e.pointerId); }catch(_){}
});
ccanvas.addEventListener('pointermove',function(e){
  if(CV.drag){
    var dx=e.clientX-CV.drag.x, dy=e.clientY-CV.drag.y;
    if(Math.abs(dx)+Math.abs(dy)>3) CV.drag.moved=true;
    CV.px+=dx; CV.py+=dy;
    CV.drag.x=e.clientX; CV.drag.y=e.clientY;
    scheduleDraw();
    return;
  }
  if(CV.mode==='k') hoverCountry(e.clientX,e.clientY);
});
function cEnd(e){
  if(!CV.drag) return;
  var d=CV.drag; CV.drag=null;
  try{ ccanvas.releasePointerCapture(e.pointerId); }catch(_){}
  if(d.moved) return;
  var hit=countryAt(d.x,d.y);
  if(!hit) return;
  if(CV.mode==='k'){
    if((hit.cn||'AS')!==CV.key) return;      // 其他洲只作参照，不参与下钻
    openCountry(hit,d.x,d.y); return;
  }
  if(hit!==CV.c){
    if(hit.off) return;
    openCountry(hit,d.x,d.y);
  }
}
ccanvas.addEventListener('pointerup',cEnd);
ccanvas.addEventListener('pointercancel',function(){ CV.drag=null; });
ccanvas.addEventListener('dblclick',function(){ back(); });

function countryAt(sx,sy){
  var k=CV.k*CV.zoom, ox=CV.ox+CV.px, oy=CV.oy+CV.py;
  var wx=(sx-ox)/k, wy=(sy-oy)/k;
  for(var idx=0;idx<CV.pr.length;idx++){
    var o=CV.pr[idx], bb=o.bb;
    if(wx<bb[0]||wx>bb[2]||wy<bb[1]||wy>bb[3]) continue;
    var inside=false;
    for(var r=0;r<o.rings.length;r++){
      var a=o.rings[r], n=a.length>>1;
      for(var i=0,j=n-1;i<n;j=i++){
        var xi=a[i*2], yi=a[i*2+1], xj=a[j*2], yj=a[j*2+1];
        if((yi>wy)!==(yj>wy) && wx < (xj-xi)*(wy-yi)/(yj-yi)+xi) inside=!inside;
      }
    }
    if(inside) return o.c;
  }
  return null;
}
function hoverCountry(x,y){
  var hit=countryAt(x,y);
  var key=(hit && (hit.cn||'AS')===CV.key)?hit:null;
  var idx=key?CS.indexOf(key):-1;
  if(idx!==CV.hov){
    CV.hov=idx;
    ccanvas.style.cursor=key?'pointer':'grab';
    scheduleDraw();
  }
  var h=$('#hover');
  if(key){
    var yi=DS.yi, u;
    if(DS.ind!=='cont'){
      u=IND[DS.ind].n+' '+fmtVal(DS.ind,valOf(key,DS.ind))+' '+IND[DS.ind].u+' · ';
    }else{
      var g=key.gdp?key.gdp[yi]:null, p=key.pop?key.pop[yi]:null;
      u=(g?('GDP '+fG(g)):'')+(p?' · '+fP(p)+'人':'')+' · ';
    }
    h.innerHTML=esc(key.n)+'<em>'+esc(key.en)+'</em><u>'+u+'点击查看城市 →</u>';
    h.classList.add('on'); h.style.left=x+'px'; h.style.top=y+'px';
  }else h.classList.remove('on');
}

/* ============================================================ 14. 搜索 */
var q=$('#q'), sugg=$('#sugg'), sugList=[];
q.addEventListener('input',function(){
  var t=q.value.trim().toLowerCase();
  if(!t){ sugg.classList.remove('on'); sugList=[]; return; }
  sugList=CS.filter(function(c){ return !c.off && (c.n.indexOf(t)>=0 || (c.en||'').toLowerCase().indexOf(t)>=0 || (c.iso3||'').toLowerCase().indexOf(t)>=0); }).slice(0,6);
  sugg.innerHTML=sugList.length? sugList.map(function(c){
    return '<div class="sg" data-i="'+CS.indexOf(c)+'">'+(c.fi?'<img src="'+c.fi+'" alt="">':'')+'<span>'+esc(c.n)+'</span><em>'+esc(c.en)+'</em></div>';
  }).join('') : '<div class="sg empty">没有匹配的国家</div>';
  sugg.classList.add('on');
});
q.addEventListener('keydown',function(e){
  if(e.key==='Enter' && sugList.length){ choose(sugList[0]); }
  if(e.key==='Escape'){ sugg.classList.remove('on'); q.blur(); }
});
sugg.addEventListener('click',function(e){
  var el=e.target.closest('.sg'); if(!el || el.dataset.i==null) return;
  choose(CS[+el.dataset.i]);
});
function choose(c){ if(!c) return; q.value=''; sugg.classList.remove('on'); q.blur(); openCountry(c); }

document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){
    if(CV.open) back();
    else { hideHover(); setHoverContinent(null); }
  }
});

/* ============================================================ 15. 尺寸 */
function resize(){
  var w=window.innerWidth, h=window.innerHeight;
  renderer.setSize(w,h); camera.aspect=w/h; camera.updateProjectionMatrix();
  if(cmpEl.classList.contains('on')) drawCmpChart();
  if(CV.open){
    sizeViewCanvas();
    if(CV.mode==='k'){
      var K=CONT[CV.key], cos0=CV.cos0;
      var bb=[(K.box[0]-K.lon)*cos0, -(K.box[3]-K.lat), (K.box[1]-K.lon)*cos0, -(K.box[2]-K.lat)];
      var m=viewMargins(); frameRect(bb,m.l,m.r,m.t,m.b);
    }
    drawView();
  }
}
window.addEventListener('resize',resize);

/* ============================================================ 16. 主循环 */
var lastT=performance.now();
function animate(now){
  requestAnimationFrame(animate);
  var dt=Math.min((now-lastT)/1000,0.05); lastT=now;

  if(state.anim){
    var a=state.anim, p=clamp((now-a.t0)/a.dur,0,1);
    var e=p<0.5? 4*p*p*p : 1-Math.pow(-2*p+2,3)/2;
    state.theta=a.from.theta+(a.to.theta-a.from.theta)*e;
    state.phi=a.from.phi+(a.to.phi-a.from.phi)*e;
    state.r=a.from.r+(a.to.r-a.from.r)*e;
    if(p>=1) state.anim=null;
  } else if(!drag && pointers.size===0){
    if(Math.abs(state.vT)>1e-4 || Math.abs(state.vP)>1e-4){
      state.theta+=state.vT; state.phi=clamp(state.phi+state.vP,0.14,Math.PI-0.14);
      state.vT*=0.93; state.vP*=0.93;
    } else if(state.autoOn && !CV.open && now-state.last>4200){
      state.theta+=dt*0.045;
    }
  }
  state.phi=clamp(state.phi,0.14,Math.PI-0.14);
  updateCamera();
  tickPlay(now);
  clouds.rotation.y+=dt*0.006;
  clouds.material.opacity=0.12+clamp((state.r-1.35)/(2.4-1.35),0,1)*0.7;
  updateCx();
  if(!CV.open) renderer.render(scene,camera);
}

updateCamera();
requestAnimationFrame(animate);
state.anim={t0:performance.now(),dur:1900,from:{theta:state.theta,phi:state.phi,r:5.6},to:{theta:state.theta,phi:state.phi,r:START.r}};

var loadHidden=false;
function hideLoader(){ if(loadHidden) return; loadHidden=true; $('#loader').classList.add('gone'); }
manager.onLoad=hideLoader;
setTimeout(hideLoader,4000);
setTimeout(function(){ if(!loadHidden) hideLoader(); },900);
setTimeout(function(){ $('#hint').classList.add('gone'); },9000);

/* ============================================================ 17. 数据台：染色 / 时间轴 / 排行榜 / 对比 */
var dockEl=$('#dock'), dchips=$('#dchips'), dtl=$('#dtl'), dyr=$('#dyr'), dleg=$('#dleg');
var rankEl=$('#rank'), rrows=$('#rrows'), cmpEl=$('#cmp');

function fmtVal(k,v){ var I=IND[k]; return (v==null||!I||!I.fmt)?'—':I.fmt(v); }
function repaintPol(){ paintFills(); polTex.needsUpdate=true; }

function syncDock(){
  var data=DS.ind!=='cont', I=IND[DS.ind];
  dyr.textContent=YEARS[DS.yi];
  dtl.max=String(YMAX); dtl.value=String(DS.yi);
  Array.prototype.forEach.call(dchips.children,function(b){ b.classList.toggle('on',b.dataset.i===DS.ind); });
  $('#dts').classList.toggle('off',!data);
  dleg.classList.toggle('off',!data);
  if(data){
    var g=[]; for(var i=0;i<=10;i++) g.push(rampAt(i/10)+' '+(i*10)+'%');
    $('#dg').style.background='linear-gradient(90deg,'+g.join(',')+')';
    var lo=I.log?Math.pow(10,I.log[0]):I.lin[0], hi=I.log?Math.pow(10,I.log[1]):I.lin[1];
    $('#dlo').textContent=I.fmt(lo);
    $('#dhi').textContent=I.fmt(hi);
    $('#dun').textContent=I.u;
  }
}

var yrRaf=0, yrPend=YI;
function setYear(i){
  i=clamp(Math.round(i),0,YMAX);
  DS.yi=i;
  syncDock();
  if(DS.ind!=='cont'){ computeFills(); repaintPol(); }
  buildRank(); renderCmp();
  if(CV.open){ drawView(); refreshHud(); }
  else hoverRefresh();
}
/* 拖时间轴时每帧最多算一次，避免一次拖动触发几十次重绘 */
function queueYear(i){
  yrPend=clamp(Math.round(i),0,YMAX);
  dyr.textContent=YEARS[yrPend];
  if(yrRaf) return;
  yrRaf=requestAnimationFrame(function(){ yrRaf=0; setYear(yrPend); });
}
function refreshHud(){
  if(!CV.open) return;
  if(CV.mode==='k') fillHudContinent(CV.key);
  else if(CV.c) fillHudCountry(CV.c);
}
function hoverRefresh(){ if(hoverKey) hideHover(); }

function setInd(k){
  if(!IND[k]||k===DS.ind) return;
  DS.ind=k;
  stopPlay();
  computeFills(); repaintPol(); setPolVis();
  syncDock(); buildRank(); renderCmp();
  if(CV.open){ drawView(); refreshHud(); }
  updateCx();
}
function stopPlay(){
  DS.play=false;
  $('#dplay').classList.remove('on'); $('#dplay').textContent='▶';
}
function togglePlay(){
  if(DS.ind==='cont'){ setInd('pc'); }
  DS.play=!DS.play;
  $('#dplay').classList.toggle('on',DS.play);
  $('#dplay').textContent=DS.play?'❚❚':'▶';
  if(DS.play && DS.yi>=YMAX) setYear(0);
  DS.step=performance.now();
}
function tickPlay(now){
  if(!DS.play || now-DS.step<300) return;
  DS.step=now;
  setYear(DS.yi>=YMAX?0:DS.yi+1);
}

/* ---- 排行榜：全世界的最高 / 最低，点条目直接进入该国 ---- */
function buildRank(){
  if(DS.ind==='cont'){ rankEl.classList.remove('on'); return; }
  rankEl.classList.add('on');
  $('#rmeta').textContent=IND[DS.ind].n+' · '+YEARS[DS.yi];
  var arr=CS.filter(function(c){ return !c.off && valOf(c,DS.ind)!=null; })
            .sort(function(a,b){ return valOf(b,DS.ind)-valOf(a,DS.ind); });
  var n=arr.length, start=DS.dir==='top'?0:Math.max(0,n-12);
  rrows.innerHTML=arr.slice(start,start+12).map(function(c,i){
    return '<button data-i="'+CS.indexOf(c)+'"><s>'+(start+i+1)+'</s>'+
      (c.fi?'<img src="'+c.fi+'" alt="">':'')+'<span>'+esc(c.n)+'</span>'+
      '<em>'+fmtVal(DS.ind,valOf(c,DS.ind))+'</em></button>';
  }).join('');
  Array.prototype.forEach.call(rrows.children,function(b){
    b.onclick=function(e){
      e.stopPropagation();
      hideHover();
      openCountry(CS[+b.dataset.i]);
    };
  });
}

/* ---- 国家对比：最多 4 国，共用一套坐标（量级指标走对数） ---- */
var CMPC=['#F0A868','#7FB2FF','#8FE0B0','#E58FD0'];
var YMAX=YEARS.length-1;

function addCompare(c){
  if(!c||c.off) return;
  var i=DS.cmp.indexOf(c);
  if(i>=0) DS.cmp.splice(i,1);
  else { if(DS.cmp.length>=4) DS.cmp.shift(); DS.cmp.push(c); }
  renderCmp(); refreshHud();
}
function renderCmp(){
  var k=CI();
  if(!DS.cmp.length){ cmpEl.classList.remove('on'); return; }
  cmpEl.classList.add('on');
  $('#cmpk').textContent=IND[k].n+' · 2000–2023';
  $('#cmprows').innerHTML=DS.cmp.map(function(c,i){
    var v=valOf(c,k), v0=valOf(c,k,0), delta='';
    if(v!=null&&v0){
      if(IND[k].log){ var r=v/v0; if(r>=1.05||r<=0.95) delta='×'+r.toFixed(1); }
      else delta=(v-v0>=0?'+':'')+(v-v0).toFixed(1);
    }
    return '<span class="cr"><i style="background:'+CMPC[i]+'"></i>'+esc(c.n)+
      '<em>'+fmtVal(k,v)+'</em>'+(delta?'<s>'+delta+'</s>':'')+
      '<button data-x="'+i+'" title="移除">✕</button></span>';
  }).join('');
  Array.prototype.forEach.call($('#cmprows').querySelectorAll('button'),function(b){
    b.onclick=function(e){
      e.stopPropagation();
      DS.cmp.splice(+b.dataset.x,1); renderCmp(); refreshHud();
    };
  });
  drawCmpChart();
  $('#cmpfn').innerHTML=cmpText();
}
function shortNum(v){
  var a=Math.abs(v);
  if(a>=1e12) return (v/1e12).toFixed(1)+'T';
  if(a>=1e9) return (v/1e9).toFixed(0)+'B';
  if(a>=1e6) return (v/1e6).toFixed(0)+'M';
  if(a>=1e4) return (v/1e4).toFixed(0)+'万';
  if(a>=1000) return (v/1000).toFixed(0)+'k';
  if(a>=10) return String(Math.round(v));
  return v.toFixed(1);
}
function drawCmpChart(){
  var cv=$('#cmpcv'); if(!cv||!cv.clientWidth) return;
  var k=CI(), dpr=Math.min(window.devicePixelRatio||1,2);
  var w=cv.clientWidth, h=98;
  cv.width=Math.round(w*dpr); cv.height=Math.round(h*dpr);
  var g=cv.getContext('2d');
  g.setTransform(dpr,0,0,dpr,0,0); g.clearRect(0,0,w,h);
  var lg=!!IND[k].log, mn=Infinity, mx=-Infinity;
  DS.cmp.forEach(function(c){ (c[k]||[]).forEach(function(v){ if(v>0){ if(v<mn)mn=v; if(v>mx)mx=v; } }); });
  if(!isFinite(mn)){ mn=1; mx=10; }
  var F=lg?function(v){ return Math.log10(v); }:function(v){ return v; };
  var y0=F(mn), y1=F(mx); if(y1-y0<1e-9) y1=y0+1;
  var pad=(y1-y0)*0.14; y0-=pad; y1+=pad;
  var L=40, R=8, T=8, B=15;
  var X=function(i){ return L+(w-L-R)*i/YMAX; };
  var Y=function(v){ return h-B-(F(v)-y0)/(y1-y0)*(h-T-B); };
  g.strokeStyle='rgba(120,160,220,.16)'; g.lineWidth=1;
  [0,0.5,1].forEach(function(t){
    var y=h-B-t*(h-T-B);
    g.beginPath(); g.moveTo(L,y); g.lineTo(w-R,y); g.stroke();
    var v=lg?Math.pow(10,y0+(y1-y0)*t):y0+(y1-y0)*t;
    g.fillStyle='rgba(140,160,190,.65)';
    g.font='9px -apple-system,"PingFang SC","Microsoft YaHei",sans-serif';
    g.textAlign='right'; g.textBaseline='middle';
    g.fillText(shortNum(v),L-5,y);
  });
  g.textAlign='center'; g.textBaseline='top'; g.fillStyle='rgba(140,160,190,.6)';
  g.fillText('2000',L+12,h-B+3);
  g.fillText('2023',w-R-12,h-B+3);
  if(DS.yi<YMAX){
    var xv=X(DS.yi);
    g.strokeStyle='rgba(240,168,104,.45)'; g.setLineDash([3,3]);
    g.beginPath(); g.moveTo(xv,T); g.lineTo(xv,h-B); g.stroke(); g.setLineDash([]);
  }
  DS.cmp.forEach(function(c,i){
    var arr=c[k]||[], started=false;
    g.beginPath(); g.strokeStyle=CMPC[i]; g.lineWidth=1.9; g.lineJoin='round';
    for(var j=0;j<arr.length;j++){
      var v=arr[j];
      if(!(v>0)){ started=false; continue; }
      var x=X(j), y=Y(v);
      if(!started){ g.moveTo(x,y); started=true; } else g.lineTo(x,y);
    }
    g.stroke();
    var last=arr[DS.yi];
    if(last>0){
      g.beginPath(); g.arc(X(DS.yi),Y(last),3,0,6.2832);
      g.fillStyle=CMPC[i]; g.fill();
      g.strokeStyle='rgba(4,9,16,.85)'; g.lineWidth=1.2; g.stroke();
    }
  });
}
function cmpText(){
  var k=CI(), a=DS.cmp[0], va=valOf(a,k), U=esc(IND[k].u||'');
  if(DS.cmp.length<2){
    return '<span style="color:#7C8CA0">再加入一个国家即可对比（最多 4 个）；点位是所选年份</span>';
  }
  var b=DS.cmp[1], vb=valOf(b,k);
  if(va==null||vb==null) return '';
  var s='<b>'+esc(a.n)+'</b> '+fmtVal(k,va)+' '+U+'，';
  if(IND[k].log){
    s+= vb>0 ? ('是 <b>'+esc(b.n)+'</b>（'+fmtVal(k,vb)+'）的 <b>'+(va/vb).toFixed(1)+' 倍</b>')
            : ('与 <b>'+esc(b.n)+'</b> 相比缺少可比数据');
  }else{
    s+=(va>=vb?'高':'低')+'于 <b>'+esc(b.n)+'</b> '+Math.abs(va-vb).toFixed(1)+' '+U;
  }
  var v0=valOf(a,k,0);
  if(v0){
    if(IND[k].log) s+='；'+esc(a.n)+' 从 2000 年至今增至 <b>'+(va/v0).toFixed(1)+' 倍</b>';
    else s+='；24 年间 '+(va-v0>=0?'+':'')+(va-v0).toFixed(1)+' '+U;
  }
  return s+'。';
}

/* ---- 事件 ---- */
dchips.addEventListener('click',function(e){
  var b=e.target.closest?e.target.closest('button'):null;
  if(!b) return;
  setInd(b.dataset.i);
});
dtl.addEventListener('input',function(){ queueYear(+dtl.value); });
$('#dplay').onclick=function(e){ e.stopPropagation(); togglePlay(); };
$('#cmpx').onclick=function(e){ e.stopPropagation(); DS.cmp=[]; renderCmp(); refreshHud(); };
$('#cadd').onclick=function(e){ e.stopPropagation(); if(CV.c) addCompare(CV.c); };
Array.prototype.forEach.call(rankEl.querySelectorAll('.seg button'),function(b){
  b.onclick=function(e){
    e.stopPropagation();
    DS.dir=b.dataset.d;
    Array.prototype.forEach.call(rankEl.querySelectorAll('.seg button'),function(x){
      x.classList.toggle('on',x===b);
    });
    buildRank();
  };
});

syncDock();
buildRank();

/* 供自动化校验使用 */
window.__globe={
  continent:function(k,sx,sy){ openContinent(k,sx,sy); },
  country:function(n,sx,sy){ var c=CS.filter(function(x){return x.n===n;})[0]; if(c) openCountry(c,sx,sy); },
  select:function(n,sx,sy){ this.country(n,sx,sy); },
  open:function(n){ this.country(n); },
  close:function(){ back(); },
  back:function(){ back(); },
  faceTo:function(lon,lat,r){ flyTo(lon,lat,r||2.0,300); },
  screenOf:function(lat,lon){
    var pt=llToVec(lat,lon).project(camera);
    return [(pt.x*0.5+0.5)*window.innerWidth,(-pt.y*0.5+0.5)*window.innerHeight];
  },
  viewScreen:function(lat,lon){
    var k=CV.k*CV.zoom, ox=CV.ox+CV.px, oy=CV.oy+CV.py;
    var dl=lon-CV.flon; while(dl>180)dl-=360; while(dl<-180)dl+=360;
    return [ox+dl*CV.cos0*k, oy-(lat-CV.flat)*k];
  },
  zoomBy:function(f){ cZoomAt(CV.w/2,CV.h/2,f); },
  panBy:function(dx,dy){ CV.px+=dx; CV.py+=dy; scheduleDraw(); },
  cities:function(){ return CV.cities.length; },
  labels:function(){ return LBL; },
  setInd:function(k){ setInd(k); },
  setYear:function(y){
    if(typeof y==='number' && y<2000) setYear(y);
    else { var i=YEARS.indexOf(y); if(i>=0) setYear(i); }
  },
  play:function(on){ if(on!==DS.play) togglePlay(); },
  ind:function(){ return DS.ind; },
  year:function(){ return YEARS[DS.yi]; },
  compare:function(n){ var c=CS.filter(function(x){return x.n===n;})[0]; if(c) addCompare(c); return DS.cmp.map(function(x){return x.n;}); },
  cmpClear:function(){ DS.cmp=[]; renderCmp(); },
  rank:function(){ return Array.prototype.map.call(rrows.children,function(b){ return b.textContent; }); },
  info:function(){
    return {mode:CV.mode, key:CV.key, open:CV.open, c:CV.c&&CV.c.n, prev:NAV.prev,
      r:+state.r.toFixed(3), k:+(CV.k*CV.zoom).toFixed(2), cities:CV.cities.length,
      pol:state.pol, list:document.querySelector('#clist').classList.contains('on'),
      crumb:(document.querySelector('#crumb').textContent||''),
      ind:DS.ind, year:YEARS[DS.yi], rankOn:rankEl.classList.contains('on'),
      rankRows:rrows.children.length, cmp:DS.cmp.map(function(x){return x.n;}),
      cmpOn:cmpEl.classList.contains('on'),
      fallback:document.querySelector('#fallback').classList.contains('on')};
  }
};

})();
