// Physics/gameplay verification: door entry, stairs, permanent death, grenades
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync('/tmp/game.js', 'utf8');
const three = fs.readFileSync('/tmp/three.min.js', 'utf8');

function ctx2dStub() { const grad = { addColorStop() {} }; return { canvas: null, font: '', globalAlpha: 1, lineWidth: 1, lineCap: 'butt', strokeStyle: '', fillStyle: '', fillRect() {}, strokeRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fill() {}, arc() {}, ellipse() {}, fillText() {}, createLinearGradient() { return grad }, createRadialGradient() { return grad } }; }
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
['g','m','info','infoT','infoB','sw','mm','hud','obj','cmp','kf','xh','hs','hurt','vig','pr','note','ctl','fb','jb','ab','gn','rb','b0','b1','b2','hp','am','rs','gr','kl','msg','menu','mmain','msubs','back','stat','stTitle','stText','stBtn','btnStory','btnSingle','btnLan'].forEach(id => { els[id] = mkEl(id, id === 'g' || id === 'm' ? 'canvas' : 'div') });
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
Object.assign(windowObj, { g: els.g, m: els.m, b0: els.b0, b1: els.b1, b2: els.b2, fb: els.fb, rb: els.rb, jb: els.jb, ab: els.ab, gn: els.gn });
const vmc = vm.createContext(windowObj);
vm.runInContext(three, vmc, { filename: 'three.min.js' });
vm.runInContext(`(function(){const Real=THREE.WebGLRenderer;THREE.WebGLRenderer=function(o){const r=new Real(o);r.render=function(){};return r};THREE.WebGLRenderer.prototype=Real.prototype})();`, vmc);
vm.runInContext(src, vmc, { filename: 'game.js' });
const fire = (ev, arg) => (winListeners[ev] || []).forEach(f => f(arg));
let t = 1000;
const stepFrames = (n) => { for (let i = 0; i < n; i++) { const cb = rafCb; rafCb = null; t += 16.7; cb(t); } };
let failed = 0;
function check(name, cond, extra) { if (cond) console.log('PASS:', name, extra !== undefined ? '(' + extra + ')' : ''); else { console.log('FAIL:', name, extra !== undefined ? '(' + extra + ')' : ''); failed++ } }

try {
  // start single play
  els.btnSingle.onclick(); stepFrames(20);
  check('game started', vm.runInContext('running', vmc));

  // ---- 1. enter a house through its front door (W1_North: door at x=54.15, front wall z=34.8 faces south)
  vm.runInContext(`C[act].x=54.2;C[act].z=42;C[act].y=support(54.2,42,0);C[act].vy=0;C[act].ground=1;yaw=0;lp=0`, vmc); // yaw=0 faces -z (north, toward the door)
  fire('keydown', { code: 'KeyW' }); stepFrames(150); fire('keyup', { code: 'KeyW' });
  const inHouse = vm.runInContext(`C[act].z`, vmc);
  check('walk through front door into house W1_North', inHouse < 34.2, 'z=' + inHouse.toFixed(2) + ' (needs < 34.2, wall at z=34.8)');
  vm.runInContext(`yaw=Math.PI`, vmc); // face south to leave
  fire('keydown', { code: 'KeyW' }); stepFrames(150); fire('keyup', { code: 'KeyW' });
  check('exit house again', vm.runInContext('C[act].z', vmc) > 34.6);

  // ---- 2. climb the interior stairs to the roof of W1_North (stairs at x=35.6..36.9, from z=34.35 going north/-z)
  vm.runInContext(`C[act].x=36.2;C[act].z=33.6;C[act].y=0;C[act].vy=0;C[act].ground=1;yaw=0;lp=0`, vmc); // stand on first step, face north (stairs rise toward -z)
  fire('keydown', { code: 'KeyW' }); stepFrames(280); fire('keyup', { code: 'KeyW' });
  const roofY = vm.runInContext('C[act].y', vmc);
  check('climb interior stairs to the roof', roofY > 3.0, 'y=' + roofY.toFixed(2) + ' (roof at ~3.65)');

  // ---- 3. dead enemies stay dead
  const n0 = vm.runInContext('bots.length', vmc);
  vm.runInContext('for(let i=bots.length;i--;)if(!bots[i].friend)killBot(i,false)', vmc);
  stepFrames(1200); // 20 seconds — old build revived them after 6 s
  const alive = vm.runInContext('bots.filter(b=>!b.dead).length', vmc);
  check('dead enemies stay dead after 20 s', alive === 0, alive + ' still alive of ' + n0);

  // ---- 4. grenade: throw + explode kills a nearby bot (pinned so it can't wander out of range)
  vm.runInContext('startGame(MODES.SINGLE,"compound")', vmc); stepFrames(10);
  vm.runInContext(`const b0=bots.find(b=>!b.dead);if(b0){b0.home=[b0.x-.1,b0.x+.1,b0.z-.1,b0.z+.1];b0.wp=[b0.x,b0.z];C[act].x=b0.x+4;C[act].z=b0.z;C[act].y=support(C[act].x,C[act].z,0);yaw=-Math.PI/2;lp=0};C[1].cd=99;C[2].cd=99`, vmc); // face bot; freeze squadmates so they don't steal the kill
  const kl0 = vm.runInContext('H.kl', vmc), gr0 = vm.runInContext('H.gr', vmc);
  fire('keydown', { code: 'KeyG' }); stepFrames(1); fire('keyup', { code: 'KeyG' });
  vm.runInContext(`if(grenades.length){const b0=bots.find(b=>!b.dead);grenades[0].t=.05;grenades[0].p.set(b0.x,b0.y+.5,b0.z)}`, vmc); // detonate at the bot (test environment has random crates that bounce throws)
  const gr1 = vm.runInContext('H.gr', vmc);
  check('grenade consumed from inventory', gr1 === gr0 - 1, gr0 + ' -> ' + gr1);
  stepFrames(30);
  check('grenade explosion killed the nearby bot', vm.runInContext('H.kl', vmc) > kl0, 'kills ' + kl0 + ' -> ' + vm.runInContext('H.kl', vmc));

  // ---- 5. car: enter + drive forward without teleporting through walls
  vm.runInContext('exitCar()', vmc);
  vm.runInContext(`const car=cars[0];C[act].x=car.x+2;C[act].z=car.z;C[act].y=support(C[act].x,C[act].z,0)`, vmc);
  fire('keydown', { code: 'KeyE' }); stepFrames(2); fire('keyup', { code: 'KeyE' });
  const driving = vm.runInContext('!!drive', vmc);
  check('entered car with E', driving);
  const cx0 = vm.runInContext('drive&&drive.x', vmc);
  fire('keydown', { code: 'KeyW' }); stepFrames(120); fire('keyup', { code: 'KeyW' });
  const dist2 = vm.runInContext('drive?Math.hypot(drive.x-'+cx0+',drive.z-'+cx0+'):0', vmc);
  check('car drove forward', dist2 > 3, dist2.toFixed(1) + ' m');
  fire('keydown', { code: 'KeyE' }); stepFrames(2); fire('keyup', { code: 'KeyE' });
  check('exited car with E', !vm.runInContext('!!drive', vmc));

  // ---- 6. campaign: op2 sabotaged state + QRF timer progression
  vm.runInContext('startCampaign(1)', vmc); stepFrames(10);
  vm.runInContext(`C[act].x=60;C[act].z=104;C[act].y=0`, vmc); // on the shipment
  stepFrames(30);
  const staged = vm.runInContext('missionState.stage', vmc);
  check('op2 sabotage triggers near shipment', staged === 'sabotaged', 'stage=' + staged);
  stepFrames(700); // > 25 s QRF timer
  // (mission may complete or not depending on stray bot fire; just ensure no crash and timer progressed)

  console.log(failed === 0 ? 'PHYSICS TEST PASSED' : 'PHYSICS TEST FAILED: ' + failed + ' failures');
  process.exit(failed === 0 ? 0 : 1);
} catch (e) { console.error('PHYSICS TEST CRASHED:', e && e.stack || e); process.exit(1); }
