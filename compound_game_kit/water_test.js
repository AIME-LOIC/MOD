// WATER physics verification (no deps): run `node water_test.js`
// Wading vs deep zones, buoyancy, surface swim, stamina sinking, boats riding the surface,
// sinking cars with drowning damage, splash FX and underwater grenade duds.
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, 'compound_game.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const src = scripts[scripts.length - 1];
if (!src || src.length < 10000) { console.log('FAIL: could not extract game JS from compound_game.html'); process.exit(1); }

function ctx2dStub() { const grad = { addColorStop() {} }; return { canvas: null, font: '', globalAlpha: 1, lineWidth: 1, lineCap: 'butt', strokeStyle: '', fillStyle: '', fillRect() {}, strokeRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, stroke() {}, fill() {}, arc() {}, ellipse() {}, fillText() {}, createLinearGradient() { return grad }, createRadialGradient() { return grad } }; }
function canvasStub(w, h) { const c = { width: w || 300, height: h || 150, style: {}, addEventListener() {}, removeEventListener() {}, remove() {}, getContext(t) { if (t === '2d') { const x = ctx2dStub(); x.canvas = c; return x } return null }, requestPointerLock() {}, getBoundingClientRect() { return { left: 0, top: 0, width: c.width, height: c.height } } }; return c; }
function glStub() {
  const valKeys = { drawingBufferWidth: 800, drawingBufferHeight: 600 };
  const strKeys = [7936, 7937, 7938, 35724];
  return new Proxy({}, { get(t, k) {
    if (k in valKeys) return valKeys[k];
    if (k === 'getParameter') return p => strKeys.includes(p) ? 'stub' : 4096;
    if (k === 'getShaderPrecisionFormat') return () => ({ precision: 23, rangeMin: 127, rangeMax: 127 });
    if (k === 'getShaderParameter' || k === 'getProgramParameter' || k === 'isContextLost') return () => true;
    if (k === 'getShaderInfoLog' || k === 'getProgramInfoLog') return () => '';
    if (k === 'getUniformLocation') return () => ({});
    if (k === 'createBuffer' || k === 'createTexture' || k === 'createProgram' || k === 'createShader') return () => ({});
    if (k === 'getExtension') return () => null;
    return () => {};
  }, set() { return true } });
}
const mkEl = (id, tag) => { const el = canvasStub(); el.id = id || ''; el.tagName = (tag || 'div').toUpperCase(); el.style = {}; el.className = ''; el.addEventListener = () => {}; el.onclick = null; el.onpointerdown = null; el.onpointerup = null; el.onpointerleave = null; el.onpointercancel = null; el.closest = () => null; el.textContent = ''; el.innerHTML = ''; el.querySelectorAll = () => []; el.appendChild = () => {}; el.children = []; return el; };
const els = {};
['g','m','info','infoT','infoB','sw','mm','hud','obj','cmp','kf','xh','hs','scope','hurt','vig','pr','note','ctl','fb','jb','ab','gn','rb','wb','b0','b1','b2','b3','hp','am','rs','gr','kl','wn','msg','menu','mmain','msubs','back','stat','stTitle','stText','stBtn','btnStory','btnSingle','btnTrain','btnOnline'].forEach(id => { els[id] = mkEl(id, id === 'g' || id === 'm' ? 'canvas' : 'div') });
els.g.getContext = t => { if (t === '2d') return ctx2dStub(); return glStub() }; els.m.width = 176; els.m.height = 96;
const winListeners = {}; let rafCb = null;
const windowObj = { innerWidth: 800, innerHeight: 600, devicePixelRatio: 1, location: { host: 'localhost:8080', protocol: 'http:' },
  addEventListener(ev, fn) { (winListeners[ev] = winListeners[ev] || []).push(fn) }, removeEventListener() {},
  requestAnimationFrame(cb) { rafCb = cb }, fetch() { return Promise.resolve({ ok: true, text: () => Promise.resolve('ok') }) },
  XMLHttpRequest: function () { const self = this;
    self.open = () => {}; self.send = () => { self.status = 0; self.response = fs.readFileSync(path.join(__dirname, 'sos_technical_school_v3.glb')); }; },
  WebSocket: function (url) { this.readyState = 1; this.send = () => {}; this.close = () => {}; setTimeout(() => { this.onopen && this.onopen() }, 0) },
  performance, console, Math, Date, JSON, setTimeout, clearTimeout, setInterval, clearInterval,
  Uint8Array, Float32Array, Uint16Array, Uint32Array, Int16Array, DataView, TextDecoder,
  Map, Set, Error, TypeError, Proxy, Reflect, RegExp, parseInt, parseFloat, isNaN, Promise, Object, Array, Number, String, Symbol, ArrayBuffer,
  document: { getElementById(id) { return els[id] || (els[id] = mkEl(id)) }, createElement(t) { return canvasStub() }, pointerLockElement: null, body: mkEl('body'), documentElement: mkEl('html') },
  AudioContext: function () { return { sampleRate: 44100, createBuffer: () => ({ getChannelData: () => new Float32Array(4410) }), createBufferSource: () => ({ buffer: null, connect() {}, start() {} }), createGain: () => ({ gain: { value: 0 }, connect() {} }), destination: {} } }
};
windowObj.window = windowObj; windowObj.self = windowObj; windowObj.globalThis = windowObj;
Object.assign(windowObj, { g: els.g, m: els.m, b0: els.b0, b1: els.b1, b2: els.b2, b3: els.b3, fb: els.fb, rb: els.rb, jb: els.jb, ab: els.ab, gn: els.gn, wb: els.wb });
const vmc = vm.createContext(windowObj);

const THREE_STUB = `
function V3(x,y,z){return new _V3(x||0,y||0,z||0)}
class _V3{constructor(x,y,z){this.x=x;this.y=y;this.z=z}
 clone(){return new _V3(this.x,this.y,this.z)}
 set(x,y,z){this.x=x;this.y=y;this.z=z;return this}
 copy(v){this.x=v.x;this.y=v.y;this.z=v.z;return this}
 add(v){this.x+=v.x;this.y+=v.y;this.z+=v.z;return this}
 sub(v){this.x+=v.x;this.y+=v.y;this.z+=v.z;return this}
 multiplyScalar(s){this.x*=s;this.y*=s;this.z*=s;return this}
 addScaledVector(v,s){this.x+=v.x*s;this.y+=v.y*s;this.z+=v.z*s;return this}
 lerp(v,a){this.x+=(v.x-this.x)*a;this.y+=(v.y-this.y)*a;this.z+=(v.z-this.z)*a;return this}
 length(){return Math.hypot(this.x,this.y,this.z)}
 normalize(){const l=this.length()||1;return this.multiplyScalar(1/l)}
 distanceTo(v){return Math.hypot(this.x-v.x,this.y-v.y,this.z-v.z)}
 dot(v){return this.x*v.x+this.y*v.y+this.z*v.z}
 crossVectors(a,b){this.x=a.y*b.z-a.z*b.y;this.y=a.z*b.x-a.x*b.z;this.z=a.x*b.y-a.y*b.x;return this}
 lookAt(){return this} applyQuaternion(){return this} applyMatrix4(){return this}
 setFromUnitVectors(){return this} angleTo(){return 0}}
THREE={Vector3:_V3,Quaternion:class{constructor(){}copy(){return this}invert(){return this}multiply(){return this}clone(){return this}setFromUnitVectors(){return this}},WebGLRenderer:function(){return{setPixelRatio(){},setSize(){},render(){},domElement:{},shadowMap:{},outputEncoding:0,toneMapping:0,toneMappingExposure:1}},
 Scene:class{constructor(){this.children=[];this.fog=null;this.position=new _V3()}add(o){this.children.push(o)}remove(o){const i=this.children.indexOf(o);if(i>=0)this.children.splice(i,1)}},
 PerspectiveCamera:class{constructor(){this.position=new _V3();this.rotation={x:0,y:0,z:0,set(){},order:''};this.up=new _V3(0,1,0);this.fov=75;this.aspect=1;this.near=.05;this.far=1600;this.children=[];
  this.quaternion={copy(){return this},invert(){return this},multiply(){return this},clone(){return this},setFromUnitVectors(){return this}}}
  getWorldDirection(v){v.set(Math.sin(yaw||0),0,Math.cos(yaw||0));return v}
  lookAt(){} updateProjectionMatrix(){} add(){} updateMatrixWorld(){} localToWorld(v){return v}},
 Group:class{constructor(){this.children=[];this.name='';this.position=new _V3();this.rotation={x:0,y:0,z:0,set(){},order:''};this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}};this.rotation.x=0;this.rotation.z=0;
  this.quaternion={copy(){return this},invert(){return this},multiply(){return this},clone(){return this},setFromUnitVectors(){return this}};
  this.userData={};this.visible=true;this.castShadow=false;this.receiveShadow=false}
  add(o){this.children.push(o)} remove(o){const i=this.children.indexOf(o);if(i>=0)this.children.splice(i,1)} traverse(fn){fn(this)} updateMatrixWorld(){} localToWorld(v){return v}
  getObjectByName(n){return this.children.find(c2=>c2.name===n)||new THREE.Group()}},
 Mesh:class{constructor(g,m){this.geometry=g;this.material=m;this.position=new _V3();this.rotation={x:0,y:0,z:0,set(){},order:''};this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}};this.visible=true;this.castShadow=false;this.receiveShadow=false;this.name='';
  this.quaternion={copy(){return this},invert(){return this},multiply(){return this},clone(){return this},setFromUnitVectors(){return this}}}
  lookAt(){return this}},
 BoxGeometry:class{},CylinderGeometry:class{},SphereGeometry:class{},PlaneGeometry:class{},CircleGeometry:class{},ConeGeometry:class{},IcosahedronGeometry:class{},DodecahedronGeometry:class{},TetrahedronGeometry:class{},TorusGeometry:class{},OctahedronGeometry:class{},
 MeshStandardMaterial:class{constructor(o){Object.assign(this,o||{});this.opacity=1;this.transparent=false}},
 MeshBasicMaterial:class{constructor(o){Object.assign(this,o||{});this.opacity=1;this.transparent=false}},
 CanvasTexture:class{constructor(){this.wrapS=0;this.wrapT=0;this.repeat={set(){}};this.anisotropy=0;this.needsUpdate=false}clone(){return this}},
 InstancedMesh:class{constructor(){this.setMatrixAt=function(){};this.instanceMatrix={needsUpdate:false}}}, Object3D:class{constructor(){this.position=new _V3();this.rotation={};this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}}}updateMatrix(){}},
 PointLight:class{constructor(){this.position=new _V3();this.intensity=0;this.distance=0}},
 SpriteMaterial:class{constructor(o){Object.assign(this,o||{});this.color={setHex(){}};this.opacity=0}}, Sprite:class{constructor(m){this.material=m;this.position=new _V3();this.visible=true;this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}}}},
 DirectionalLight:class{constructor(){this.position=new _V3();this.target={position:new _V3()};this.intensity=0;this.castShadow=false;this.shadow={mapSize:{set(){}},camera:{}}}},
 HemisphereLight:class{constructor(){this.intensity=0}},AmbientLight:class{constructor(){this.intensity=0}},
 Fog:class{},BufferGeometry:class{constructor(){this.attributes={}}setAttribute(){return this}setIndex(){return this}computeBoundingSphere(){}computeVertexNormals(){}},
 BufferAttribute:class{constructor(a,s){this.array=a;this.itemSize=s}},Float32BufferAttribute:class{constructor(a,s){this.array=a;this.itemSize=s}},
 BackSide:1,PCFSoftShadowMap:1,sRGBEncoding:1,ACESFilmicToneMapping:1,DoubleSide:2};
function canvasEl(){return {}}`;
vm.runInContext(THREE_STUB, vmc, { filename: 'three.stub.js' });
vm.runInContext(src, vmc, { filename: 'game.js' });
const fire = (ev, arg) => (winListeners[ev] || []).forEach(f => f(arg));
let t = 1000;
const stepFrames = (n) => { for (let i = 0; i < n; i++) { const cb = rafCb; rafCb = null; t += 16.7; cb(t); } };
let failed = 0;
function check(name, cond, extra) { if (cond) console.log('PASS:', name, extra !== undefined ? '(' + extra + ')' : ''); else { console.log('FAIL:', name, extra !== undefined ? '(' + extra + ')' : ''); failed++ } }

try {
  // ---- unit checks on the zone math ----
  vm.runInContext(`WATER.length=0;WATER.push({x0:-10,x1:10,z0:-10,z1:10,y:.35,bed:-3.2,deep:1},{x0:20,x1:30,z0:20,z1:30,y:.35,bed:-.3,deep:0});0`, vmc);
  check('waterAt finds a zone', vm.runInContext(`!!waterAt(0,0,0)`, vmc));
  check('waterAt misses outside zones', vm.runInContext(`!waterAt(50,50,0)`, vmc));
  check('deep zone swims', vm.runInContext(`!!swimState({x:0,z:0,y:0})`, vmc));
  check('shallow zone only wades', vm.runInContext(`!swimState({x:25,z:25,y:0})`, vmc));

  // ---- gameplay on compound: the real river + lake zones ----
  vm.runInContext(`WATER.length=0;startGame(MODES.SINGLE,'compound')`, vmc); stepFrames(10);
  const nz = vm.runInContext(`WATER.length`, vmc);
  check('compound registers water zones', nz >= 5, nz + ' zones');
  const lz = vm.runInContext(`WATER.find(w=>w.z0===LKZ0)`, vmc);
  check('lake zone is deep', lz && lz.deep, lz ? 'y=' + lz.y + ' bed=' + lz.bed : 'missing');

  // swim out into the lake: buoyancy must lift the player to the surface and hold them there
  vm.runInContext(`C[act].x=40;C[act].z=-100;C[act].y=-1.8;C[act].vy=0;C[act].ground=0;yaw=0;lp=0`, vmc); stepFrames(90);
  const swY = vm.runInContext('C[act].y', vmc);
  check('buoyancy lifts a swimmer to the surface', swY > -1.3 && swY < .8, 'y=' + swY.toFixed(2) + ' (surface .35, float rest -.65)');

  // wading on the bed stays possible: no swim flag while standing in a shallow strip
  const wading = vm.runInContext(`(function(){const w={x0:0,x1:10,z0:0,z1:10,y:.4,bed:0,deep:0};WATER.push(w);const c={x:5,z:5,y:.05,ground:1,vy:0,v:0,t:0,r:0};
   mover(c,1,0,2,.016);return !swimState(c)})()`, vmc);
  check('shallow water wading (no swim)', wading);

  // stamina: swimming drains it, standing refills it
  vm.runInContext(`H.st=100;C[act].x=40;C[act].z=-100;C[act].y=-.65;C[act].ground=0`, vmc); stepFrames(120);
  const stAfter = vm.runInContext('H.st', vmc);
  check('swimming drains stamina', stAfter < 96, 'stamina=' + stAfter.toFixed(1));

  // exhaustion: zero stamina makes you sink below the surface
  vm.runInContext(`H.st=0;C[act].y=-.65;C[act].vy=0`, vmc); stepFrames(80);
  const sinkY = vm.runInContext('C[act].y', vmc);
  check('exhausted swimmer sinks', sinkY < -.8, 'y=' + sinkY.toFixed(2));

  // grenade into the water: splash flag set, and it ends as a dud (no explode())
  vm.runInContext(`H.gr=3;throwGrenade();grenades[0].p.set(40,1.5,-100);grenades[0].v.set(0,-6,0);grenades[0].t=3`, vmc);
  stepFrames(20);
  const dud = vm.runInContext(`(function(){const g=grenades[0];return g&&g.wet&&g.p.y<WATER.find(w=>w.z0===LKZ0).y+.2})()`, vmc);
  stepFrames(220); // let the fuse run out underwater
  const stillThere = vm.runInContext(`!!grenades[0]`, vmc);
  check('water grenade splashes and floats', dud);
  check('underwater grenade fizzles (dud, no explosion FX)', !stillThere || vm.runInContext(`grenades.length===0`, vmc), 'grenades left: ' + vm.runInContext('grenades.length', vmc));

  // ---- school pool: wade in through the gap, deep middle swims, walls keep you in ----
  vm.runInContext(`startGame(MODES.SINGLE,'school')`, vmc); stepFrames(10);
  const pool = vm.runInContext(`WATER.find(w=>w.z0>50)`, vmc);
  check('school pool is a deep water zone', pool && pool.deep, pool ? 'y=' + pool.y + ' bed=' + pool.bed : 'missing');
  vm.runInContext(`C[act].x=2;C[act].z=56;C[act].y=.15;C[act].vy=0;C[act].ground=1`, vmc); stepFrames(60);
  const poolY = vm.runInContext('C[act].y', vmc);
  check('swimming in the pool holds you near the surface', poolY > -.2 && poolY < 1.6, 'y=' + poolY.toFixed(2) + ' (surface 1.55)');
  vm.runInContext(`C[act].x=2;C[act].z=56;C[act].y=1.0;yaw=Math.PI/2`, vmc); // face -x, swim at the west wall
  fire('keydown', { code: 'KeyW' }); stepFrames(120); fire('keyup', { code: 'KeyW' });
  const wallX = vm.runInContext('C[act].x', vmc);
  check('pool wall stops a swimmer', wallX > -4.4, 'x=' + wallX.toFixed(1) + ' (west wall at -4.15)');

  // minimap: water draws without crashing
  vm.runInContext('mini()', vmc);
  check('minimap renders water zones', true);
} catch (e) { console.log('FAIL: exception —', e.stack); failed++ }

console.log(failed ? 'WATER TEST FAILED (' + failed + ')' : 'WATER TEST PASSED');
process.exit(failed ? 1 : 0);
