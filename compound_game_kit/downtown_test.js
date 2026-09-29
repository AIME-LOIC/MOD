// DOWNTOWN map verification (no deps): run `node downtown_test.js`
// GLB towers/hotel/houses spawn colliders; stairs + slab holes make floors climbable;
// rooftop pool is a deep water zone; GLB cars drive, take damage and torch.
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
    self.open = () => {}; self.send = () => { self.status = 0;
      const want = self._url || '';
      let f = null;
      if (want.indexOf('skyscraper') >= 0) f = 'skyscraper.glb';
      else if (want.indexOf('hotel') >= 0) f = 'hotel.glb';
      else if (want.indexOf('house_small') >= 0) f = 'house_small.glb';
      else if (want.indexOf('house_duplex') >= 0) f = 'house_duplex.glb';
      else if (want.indexOf('car_sedan') >= 0) f = 'car_sedan.glb';
      else if (want.indexOf('car_van') >= 0) f = 'car_van.glb';
      else if (want.indexOf('car_pickup') >= 0) f = 'car_pickup.glb';
      else if (want.indexOf('sos_technical') >= 0) f = 'sos_technical_school_v3.glb';
      self.response = f ? fs.readFileSync(path.join(__dirname, f)) : null; }; },
  WebSocket: function (url) { this.readyState = 1; this.send = () => {}; this.close = () => {}; setTimeout(() => { this.onopen && this.onopen() }, 0) },
  performance, console, Math, Date, JSON, setTimeout, clearTimeout, setInterval, clearInterval,
  Uint8Array, Float32Array, Uint16Array, Uint32Array, Int16Array, DataView, TextDecoder,
  Map, Set, Error, TypeError, Proxy, Reflect, RegExp, parseInt, parseFloat, isNaN, Promise, Object, Array, Number, String, Symbol, ArrayBuffer,
  document: { getElementById(id) { return els[id] || (els[id] = mkEl(id)) }, createElement(t) { return canvasStub() }, pointerLockElement: null, body: mkEl('body'), documentElement: mkEl('html') },
  AudioContext: function () { return { sampleRate: 44100, createBuffer: () => ({ getChannelData: () => new Float32Array(4410) }), createBufferSource: () => ({ buffer: null, connect() {}, start() {} }), createGain: () => ({ gain: { value: 0 }, connect() {} }), destination: {} } }
};
windowObj.window = windowObj; windowObj.self = windowObj; windowObj.globalThis = windowObj;
windowObj.require = require; windowObj.process = process; // for the GLTF stub's file reads
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
  add(o){this.children.push(o)} remove(o){const i=this.children.indexOf(o);if(i>=0)this.children.splice(i,1)}
  traverse(fn){fn(this);this.children.forEach(c2=>c2.traverse&&c2.traverse(fn))} updateMatrixWorld(){} localToWorld(v){return v}
  getObjectByName(n){return this.children.find(c2=>c2.name===n)||new THREE.Group()}},
 Mesh:class{constructor(g,m){this.geometry=g;this.material=m;this.position=new _V3();this.rotation={x:0,y:0,z:0,set(){},order:''};this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}};this.visible=true;this.castShadow=false;this.receiveShadow=false;this.name='';this.isMesh=true;
  this.quaternion={copy(){return this},invert(){return this},multiply(){return this},clone(){return this},setFromUnitVectors(){return this}}}
  traverse(fn){fn(this)} lookAt(){return this}},
 BoxGeometry:class{},CylinderGeometry:class{},SphereGeometry:class{},PlaneGeometry:class{},CircleGeometry:class{},TorusGeometry:class{},ConeGeometry:class{},IcosahedronGeometry:class{},DodecahedronGeometry:class{},TetrahedronGeometry:class{},TorusGeometry:class{},OctahedronGeometry:class{},
 MeshStandardMaterial:class{constructor(o){Object.assign(this,o||{});this.opacity=1;this.transparent=false}},
 MeshBasicMaterial:class{constructor(o){Object.assign(this,o||{});this.opacity=1;this.transparent=false}},
 CanvasTexture:class{constructor(){this.wrapS=0;this.wrapT=0;this.repeat={set(){}};this.anisotropy=0;this.needsUpdate=false}clone(){return this}},
 InstancedMesh:class{constructor(){this.setMatrixAt=function(){};this.instanceMatrix={needsUpdate:false}}}, Object3D:class{constructor(){this.position=new _V3();this.rotation={};this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}}}updateMatrix(){}},
 PointLight:class{constructor(){this.position=new _V3();this.intensity=0;this.distance=0}},
 SpriteMaterial:class{constructor(o){Object.assign(this,o||{});this.color={setHex(){}};this.opacity=0}}, Sprite:class{constructor(m){this.material=m;this.position=new _V3();this.visible=true;this.scale={x:1,y:1,z:1,set(){},setScalar(){},multiplyScalar(){return this}}}},
 DirectionalLight:class{constructor(){this.position=new _V3();this.target={position:new _V3()};this.intensity=0;this.castShadow=false;this.shadow={mapSize:{set(){}},camera:{}}}},
 HemisphereLight:class{constructor(){this.intensity=0}},AmbientLight:class{constructor(){this.intensity=0}},
 Fog:class{},BufferGeometry:class{constructor(){this.attributes={};this.index=null}setAttribute(k,a){this.attributes[k]=a;return this}setIndex(i){this.index=i;return this}computeBoundingSphere(){}computeVertexNormals(){}},
 BufferAttribute:class{constructor(a,s){this.array=a;this.itemSize=s;
   this.getX=i=>this.array[i*3];this.getY=i=>this.array[i*3+1];this.getZ=i=>this.array[i*3+2];
   this.count=this.array.length/3}},Float32BufferAttribute:class{constructor(a,s){this.array=a;this.itemSize=s}},
 BackSide:1,PCFSoftShadowMap:1,sRGBEncoding:1,ACESFilmicToneMapping:1,DoubleSide:2};
function canvasEl(){return {}}`;
vm.runInContext(THREE_STUB, vmc, { filename: 'three.stub.js' });

// GLTFLoader stub: synchronous parse of the real GLBs from disk into stub meshes
const GLTF_STUB = `
THREE.GLTFLoader=function(){this.load=(url,ok,err)=>{ // synchronous: parse the real GLB now
 let f=null;const u=url||'';
 if(u.indexOf('skyscraper')>=0)f='skyscraper.glb';else if(u.indexOf('hotel')>=0)f='hotel.glb';
 else if(u.indexOf('house_small')>=0)f='house_small.glb';else if(u.indexOf('house_duplex')>=0)f='house_duplex.glb';
 else if(u.indexOf('car_sedan')>=0)f='car_sedan.glb';else if(u.indexOf('car_van')>=0)f='car_van.glb';
 else if(u.indexOf('car_pickup')>=0)f='car_pickup.glb';else if(u.indexOf('character_human')>=0)f='character_human.glb';
 else if(u.indexOf('sos_technical')>=0)f='sos_technical_school_v3.glb';
 if(!f){if(err)err('unknown');return}
 let gltf=null,bin=null;
 try{const fs=require('fs'),path=require('path');
  const buf=fs.readFileSync(path.join(process.cwd(),f));
  const dv=new DataView(buf.buffer,buf.byteOffset,buf.byteLength);let off=12;
  while(off+8<=buf.byteLength){const len=dv.getUint32(off,true),typ=dv.getUint32(off+4,true);off+=8;
   if(typ===0x4E4F534A)gltf=JSON.parse(new TextDecoder().decode(new Uint8Array(buf.buffer,buf.byteOffset+off,len)));
   else if(typ===0x004E4942)bin=new Uint8Array(buf.buffer,buf.byteOffset+off,len);off+=len}}catch(e){if(err)err(e);return}
 if(!gltf||!bin){if(err)err('parse');return}
 const access=i=>{const a=gltf.accessors[i],bv=gltf.bufferViews[a.bufferView||0];
  const comp={5126:Float32Array,5123:Uint16Array,5125:Uint32Array,5121:Uint8Array,5122:Int16Array}[a.componentType];
  const nper={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type];
  return new comp(bin.buffer,bin.byteOffset+(bv.byteOffset||0)+(a.byteOffset||0),a.count*nper)};
 const scene=new THREE.Group();
 gltf.nodes.forEach(n=>{if(n.mesh===undefined)return;const m=gltf.meshes[n.mesh];
  m.primitives.forEach(pr=>{
   const geo=new THREE.BufferGeometry();
   geo.setAttribute('position',new THREE.BufferAttribute(access(pr.attributes.POSITION),3));
   if(pr.indices!==undefined)geo.setIndex(new THREE.BufferAttribute(access(pr.indices),1));
   geo.computeVertexNormals();
   const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({}));
   mesh.name=n.name||'';mesh.castShadow=mesh.receiveShadow=true;scene.add(mesh)})});
 ok({scene:scene,animations:[]})}};
THREE.SkeletonUtils={clone:o=>o.clone()};
`;
vm.runInContext(GLTF_STUB, vmc, { filename: 'gltf.stub.js' });
vm.runInContext(src, vmc, { filename: 'game.js' });
const fire = (ev, arg) => (winListeners[ev] || []).forEach(f => f(arg));
let t = 1000;
const stepFrames = (n) => { for (let i = 0; i < n; i++) { const cb = rafCb; rafCb = null; t += 16.7; cb(t); } };
let failed = 0;
function check(name, cond, extra) { if (cond) console.log('PASS:', name, extra !== undefined ? '(' + extra + ')' : ''); else { console.log('FAIL:', name, extra !== undefined ? '(' + extra + ')' : ''); failed++ } }

try {
  const nAssets = vm.runInContext(`Object.keys(ASSETS).length`, vmc);
  check('GLB assets loaded', nAssets >= 7, nAssets + ' assets');

  vm.runInContext(`startGame(MODES.SINGLE,'downtown')`, vmc); stepFrames(15);
  check('downtown builds and game starts', vm.runInContext('running', vmc));
  const geo = vm.runInContext(`({cols:col.length,tops:tops.length,bots:bots.length,cars:cars.filter(c=>c.kind).length,lads:ladders.length})`, vmc);
  check('towers+hotel+houses spawn colliders', geo.cols > 400, geo.cols + ' colliders');
  check('GLB cars are drivable entities', geo.cars >= 6, geo.cars + ' cars');
  check('bots patrol the district', geo.bots >= 8, geo.bots + ' bots');
  const pool = vm.runInContext(`WATER.find(w=>w.z0<-40&&w.y>25)`, vmc);
  check('hotel rooftop pools are water zones', !!pool, pool ? 'y=' + pool.y + ' bed=' + pool.bed : 'missing: '+vm.runInContext(`JSON.stringify(WATER)`, vmc).slice(0,120));

  // plaza fountain: wade-able water
  const fw = vm.runInContext(`!!WATER.find(w=>w.bed>-1&&w.y<1)`, vmc);
  check('plaza fountain is shallow water', fw);

  // tower is enterable: stand inside the west tower lobby (origin placed at (-42,0); lobby floor y=.5)
  vm.runInContext(`C[act].x=-42;C[act].z=4;C[act].y=support(-42,4,0);C[act].vy=0;C[act].ground=1`, vmc); stepFrames(2);
  const lobbyY = vm.runInContext('C[act].y', vmc);
  check('tower lobby floor supports the player', lobbyY > .3 && lobbyY < 1.2, 'y=' + lobbyY.toFixed(2));

  // climb the tower: stair flight rises eastward from the strip's west end (z=-6.8)
  vm.runInContext(`C[act].x=-53.3;C[act].z=-6.8;C[act].y=support(-53.3,-6.8,0);C[act].ground=1;yaw=-Math.PI/2`, vmc); // face +x
  fire('keydown', { code: 'KeyW' }); stepFrames(500); fire('keyup', { code: 'KeyW' });
  const stairY = vm.runInContext('C[act].y', vmc);
  check('stairs lift the player above the lobby', stairY > 2.2, 'y=' + stairY.toFixed(2));

  // drive a GLB car and wreck it with gunfire
  vm.runInContext(`const c2=cars.find(c=>c.kind);C[act].x=c2.x+2;C[act].z=c2.z;C[act].y=support(C[act].x,C[act].z,0)`, vmc);
  fire('keydown', { code: 'KeyE' }); stepFrames(2); fire('keyup', { code: 'KeyE' });
  check('GLB car is drivable', vm.runInContext('!!drive', vmc));
  fire('keydown', { code: 'KeyW' }); stepFrames(100); fire('keyup', { code: 'KeyW' });
  const carMoved = vm.runInContext('drive?drive.v||0:0', vmc);
  fire('keydown', { code: 'KeyE' }); stepFrames(2); fire('keyup', { code: 'KeyE' });
  // parked GLB cars torch when a grenade lands on them (damage system)
  const wrecked = vm.runInContext(`(function(){const c=cars.find(c=>c.kind&&!c.burnt);C[act].x=c.x+5;C[act].z=c.z;C[act].y=support(C[act].x,C[act].z,0);
   explode(new THREE.Vector3(c.x,1,c.z));return c.burnt})()`, vmc);
  check('GLB car torched by explosion', wrecked);

  // campaign story: GLASS CITY is op 1 and uses downtown
  const op1 = vm.runInContext(`CAMPAIGN[0]`, vmc);
  check('story op 1 is GLASS CITY on downtown', op1.title.indexOf('GLASS CITY') >= 0 && op1.map === 'downtown', op1.title);
  const ops = vm.runInContext(`CAMPAIGN.length`, vmc);
  check('campaign extended with downtown story', ops === 8, ops + ' ops');
} catch (e) { console.log('FAIL: exception —', e.stack); failed++ }

console.log(failed ? 'DOWNTOWN TEST FAILED (' + failed + ')' : 'DOWNTOWN TEST PASSED');
process.exit(failed ? 1 : 0);
