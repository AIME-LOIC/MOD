// KILLHOUSE arena + pistol/knife verification (no deps): run `node arena_test.js`
const fs = require('fs');
const vm = require('vm');
const path = require('path');

// --- load game source straight out of compound_game.html ---
const html = fs.readFileSync(path.join(__dirname, 'compound_game.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const src = scripts[scripts.length - 1];
if (!src || src.length < 10000) { console.log('FAIL: could not extract game JS from compound_game.html'); process.exit(1); }

// --- stubs (same approach as physics_test.js) ---
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
  WebSocket: function (url) { this.readyState = 1; this.send = () => {}; this.close = () => {}; setTimeout(() => { this.onopen && this.onopen() }, 0) },
  performance, console, Math, Date, JSON, setTimeout, clearTimeout, setInterval, clearInterval,
  Uint8Array, Float32Array, Map, Set, Error, TypeError, Proxy, Reflect, RegExp, parseInt, parseFloat, isNaN, Promise, Object, Array, Number, String, Symbol, ArrayBuffer,
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
 sub(v){this.x-=v.x;this.y-=v.y;this.z-=v.z;return this}
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
 Group:class{constructor(){this.children=[];this.name='';this.position=new _V3();this.rotation={x:0,y:0,z:0,set(){},order:''};this.scale={x:1,y:1,z:1,set(){},setScalar(){}};
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
 Fog:class{},BufferGeometry:class{constructor(){this.attributes={}}setAttribute(){return this}setIndex(){return this}computeBoundingSphere(){}},
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
  // start the LAN deathmatch on killhouse, like an online match
  vm.runInContext(`lanRole='ffa';startGame(MODES.LAN,'killhouse')`, vmc); stepFrames(15);
  check('killhouse map builds and game starts', vm.runInContext('running', vmc));
  check('map is killhouse', vm.runInContext('mapName', vmc) === 'killhouse');

  const geo = vm.runInContext(`({bots:bots.length,spawns:killSpawns.length,crates:ammoCrates.length,cols:col.length,tops:tops.length})`, vmc);
  check('room-grid colliders built', geo.cols > 150, geo.cols + ' colliders');
  check('catwalk roofs standable', geo.tops > 40, geo.tops + ' tops');
  check('10 deathmatch spawns placed', geo.spawns === 10, geo.spawns + ' spawns');
  check('ammo crates placed', geo.crates >= 7, geo.crates + ' crates');
  check('combatants spawned', geo.bots >= 8, geo.bots + ' bots');

  // player stands on the arena floor at the plaza
  vm.runInContext(`C[act].x=105.6;C[act].z=75.6;C[act].y=support(105.6,75.6,0);C[act].vy=0;C[act].ground=1;yaw=0;lp=0`, vmc); stepFrames(2);
  const py = vm.runInContext('C[act].y', vmc);
  check('player supported by arena floor', py > -0.1 && py < 1, 'y=' + py.toFixed(2));

  // outer walls keep the player in: walk west 8 s, must stay inside the hall
  vm.runInContext(`yaw=Math.PI/2`, vmc); // face -x (west)
  fire('keydown', { code: 'KeyW' }); stepFrames(480); fire('keyup', { code: 'KeyW' });
  const westX = vm.runInContext('C[act].x', vmc);
  check('outer wall blocks escape west', westX > 4.6, 'x=' + westX.toFixed(1) + ' (hall west wall at 5.6)');

  // interior partitions stop a straight run east from the plaza
  vm.runInContext(`C[act].x=105.6;C[act].z=75.6;C[act].y=support(C[act].x,C[act].z,0);C[act].ground=1;yaw=-Math.PI/2`, vmc); // face +x
  fire('keydown', { code: 'KeyW' }); stepFrames(240); fire('keyup', { code: 'KeyW' });
  const eastX = vm.runInContext('C[act].x', vmc);
  check('partitions stop a straight run', eastX < 160, 'x=' + eastX.toFixed(1));

  // pistol: switch, fire, ammo bookkeeping, HUD name
  vm.runInContext(`C[act].x=105.6;C[act].z=75.6;C[act].y=support(C[act].x,C[act].z,0);C[act].ground=1;yaw=0;lp=0;switchW('pistol')`, vmc);
  const pAm0 = vm.runInContext('wstate.pistol.am', vmc);
  fire('keydown', { code: 'KeyF' }); stepFrames(20); fire('keyup', { code: 'KeyF' });
  const pAm1 = vm.runInContext('wstate.pistol.am', vmc);
  check('pistol fires and consumes ammo', pAm1 < pAm0, pAm0 + ' -> ' + pAm1);
  check('pistol HUD name', vm.runInContext(`document.getElementById('wn').textContent`, vmc) === 'M9 PISTOL');
  const pDmg = vm.runInContext('WPNS.pistol.dmg', vmc), rDmg = vm.runInContext('WPNS.rifle.dmg', vmc);
  check('pistol hits harder per shot than rifle', pDmg > rDmg, pDmg + ' vs ' + rDmg);

  // knife: melee kills at close range, no ammo use
  vm.runInContext(`startGame(MODES.LAN,'killhouse')`, vmc); stepFrames(5);
  vm.runInContext(`switchW('knife');const kb=bots.find(b=>!b.dead);kb.home=[kb.x-.1,kb.x+.1,kb.z-.1,kb.z+.1];kb.wp=[kb.x,kb.z];`, vmc);
  vm.runInContext(`C[act].x=kb.x-1.2;C[act].z=kb.z;C[act].y=support(C[act].x,C[act].z,0);C[act].ground=1;yaw=Math.PI/2;lp=0`, vmc); // stub camera faces +x toward the bot
  const kl0 = vm.runInContext('H.kl', vmc);
  for (let i = 0; i < 8; i++) vm.runInContext(`meleeHit(C[act])`, vmc);
  const kl1 = vm.runInContext('H.kl', vmc);
  check('knife kills at close range', kl1 > kl0, kl0 + ' -> ' + kl1);
  check('knife uses no ammo', vm.runInContext('wstate.knife.am', vmc) === 0);

  // ammo crate pickup refills reserves + cooldown
  vm.runInContext(`switchW('rifle');wstate.rifle.rs=0;const cr=ammoCrates[0];C[act].x=cr.x;C[act].z=cr.z;C[act].y=support(cr.x,cr.z,0);C[act].ground=1`, vmc);
  stepFrames(6);
  check('ammo crate refills rifle reserve', vm.runInContext('wstate.rifle.rs', vmc) > 0, 'rs=' + vm.runInContext('wstate.rifle.rs', vmc));
  check('ammo crate goes on cooldown', vm.runInContext('ammoCrates[0].used', vmc) === 1);

  // respawn keeps weapons healthy
  vm.runInContext(`hurt(999)`, vmc); stepFrames(3);
  check('respawn refills rifle mag', vm.runInContext('wstate.rifle.am', vmc) === 30);
  check('respawn switches back to rifle', vm.runInContext('curW', vmc) === 'rifle');

  // other maps unaffected
  vm.runInContext(`startGame(MODES.SINGLE,'compound')`, vmc); stepFrames(10);
  check('compound mode still works', vm.runInContext('running', vmc));
  const oldBots = vm.runInContext('bots.length', vmc);
  check('compound bots spawn as before', oldBots > 3, oldBots + ' bots');
  check('rifle is default weapon', vm.runInContext('curW', vmc) === 'rifle' && vm.runInContext(`document.getElementById('wn').textContent`, vmc) === 'M4 RIFLE');
} catch (e) {
  console.log('FAIL: exception during test run:', e.message);
  console.log(e.stack.split('\n').slice(0, 4).join('\n'));
  failed++;
}
console.log(failed ? '\n' + failed + ' test(s) FAILED' : '\nALL TESTS PASSED');
process.exit(failed ? 1 : 0);
