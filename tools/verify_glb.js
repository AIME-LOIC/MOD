#!/usr/bin/env node
/* Verify character_human.glb structure + silhouette (no deps).
   Checks: skin with >=20 joints, vertex colors, Idle+Walk clips,
   human proportions (shoulders wider than waist, narrow head, height ~1.87 m). */
'use strict';
const fs = require('fs');
const path = process.argv[2] || 'character_human.glb';
const buf = fs.readFileSync(path);
if (buf.readUInt32LE(0) !== 0x46546C67) { console.log('FAIL: not a GLB'); process.exit(1); }
let off = 12, json = null, bin = null;
while (off < buf.length) {
  const len = buf.readUInt32LE(off), type = buf.readUInt32LE(off + 4);
  const chunk = buf.slice(off + 8, off + 8 + len);
  if (type === 0x4E4F534A) json = JSON.parse(chunk.toString('utf8'));
  if (type === 0x004E4942) bin = chunk;
  off += 8 + len;
}
let fails = 0;
const check = (name, ok, extra) => { console.log((ok ? 'PASS' : 'FAIL') + ': ' + name + (extra ? ' (' + extra + ')' : '')); if (!ok) fails++; };

check('GLB header', !!json, json.asset ? 'generator: ' + (json.asset.generator || '?') : '');
const skins = json.skins || [], meshes = json.meshes || [], anims = json.animations || [];
check('skin present with >=20 joints', skins.length === 1 && skins[0].joints.length >= 20, skins[0] ? skins[0].joints.length + ' joints' : 'none');
const meshNames = meshes.map(m => m.name).join(',');
check('5 body-part meshes', meshes.length === 5, meshNames);
const hasVC = meshes.every(m => m.primitives.every(p => p.attributes.COLOR_0 !== undefined));
check('vertex colors on all parts', hasVC);

// accessor reader
function readAcc(idx) {
  const a = json.accessors[idx], bv = json.bufferViews[a.bufferView];
  const start = (bv.byteOffset || 0) + (a.byteOffset || 0);
  const comp = { SCALAR: 1, VEC3: 3, VEC4: 4 }[a.type];
  const arr = new Float32Array(bin.buffer, bin.byteOffset + start, a.count * comp);
  return { arr, count: a.count, comp };
}
// gather all mesh POSITIONs, per mesh (arms are in A-pose, so silhouettes must be checked per part)
let all = [];
const perMesh = {};
for (const m of meshes) {
  const pts = [];
  for (const p of m.primitives) { const a = readAcc(p.attributes.POSITION); for (let i = 0; i < a.count; i++) pts.push([a.arr[i * 3], a.arr[i * 3 + 1], a.arr[i * 3 + 2]]); }
  perMesh[m.name] = pts;
  all = all.concat(pts);
}
function bbox(pts) {
  let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (const p of pts) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], p[k]); mx[k] = Math.max(mx[k], p[k]); }
  return { mn, mx, size: [mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]] };
}
const bbBody = bbox(perMesh.Body), bbLegL = bbox(perMesh.LegL), bbLegR = bbox(perMesh.LegR), bbArmL = bbox(perMesh.ArmL);
console.log('  [bboxes] Body', bbBody.size.map(v => v.toFixed(2)).join('x'),
  '| LegL', bbLegL.size.map(v => v.toFixed(2)).join('x'),
  '| ArmL', bbArmL.size.map(v => v.toFixed(2)).join('x'));
let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9, minZ = 1e9, maxZ = -1e9;
for (const [x, y, z] of all) { minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y); minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z); }
const height = maxY - minY, width = maxX - minX, depth = maxZ - minZ;
check('height ~1.87 m', height > 1.7 && height < 2.0, height.toFixed(3) + ' m');

// silhouette from the Body mesh only (A-pose arms would contaminate full-body slices)
function xExtentAt(pts, yc, tol) {
  let mn = 1e9, mx = -1e9, n = 0;
  for (const [x, y] of pts) if (Math.abs(y - yc) < tol) { mn = Math.min(mn, x); mx = Math.max(mx, x); n++; }
  return n > 20 ? mx - mn : null;
}
const shoulder = xExtentAt(perMesh.Body, 1.34 * (height / 1.87), 0.025);
const waist = xExtentAt(perMesh.Body, 1.08 * (height / 1.87), 0.025);
const head = xExtentAt(perMesh.Body, 1.72 * (height / 1.87), 0.025);
check('shoulders wider than waist (Body mesh)', shoulder && waist && shoulder > waist * 1.15, 'shoulder ' + (shoulder || 0).toFixed(3) + ' vs waist ' + (waist || 0).toFixed(3));
check('head much narrower than shoulders', head && shoulder && head < shoulder * 0.55, 'head ' + (head || 0).toFixed(3));
check('two separated legs', (function () {
  const lPts = perMesh.LegL.filter(p => p[1] < 0.5), rPts = perMesh.LegR.filter(p => p[1] < 0.5);
  if (!lPts.length || !rPts.length) return false;
  let lmn = 1e9, rmx = -1e9;
  for (const p of lPts) lmn = Math.min(lmn, p[0]);
  for (const p of rPts) rmx = Math.max(rmx, p[0]);
  return lmn - rmx > 0.005;
})(), 'legs split below y=0.5');
check('legs are tall tubes (~0.9 m)', bbLegL.size[1] > 0.8 && bbLegL.size[0] < 0.25, 'h=' + bbLegL.size[1].toFixed(2) + ' w=' + bbLegL.size[0].toFixed(2));
check('arms reach outward (A-pose)', bbArmL.size[0] > 0.45, 'x-extent ' + bbArmL.size[0].toFixed(2) + ' m');

// animations
const names = anims.map(a => a.name);
check('Idle + Walk clips', names.includes('Idle') && names.includes('Walk'), names.join(', '));
const walk = anims.find(a => a.name === 'Walk');
const rotChans = walk.channels.filter(c => c.target.path === 'rotation').length;
check('Walk drives many bones', rotChans >= 10, rotChans + ' rotation channels');
const idle = anims.find(a => a.name === 'Idle');
const idleRot = idle.channels.filter(c => c.target.path === 'rotation').length;
check('Idle animates (not a static pose)', idleRot >= 4, idleRot + ' rotation channels');
// walk legs actually swing: gather quaternion variance on thigh channels
function quatRange(anim, boneIdx) {
  const chans = anim.channels.filter(c => c.target.path === 'rotation' && c.target.node === boneIdx);
  let minMax = null;
  for (const c of chans) {
    const s = anim.samplers[c.sampler], out = readAcc(s.output);
    let mn = [1e9, 1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9, -1e9];
    for (let i = 0; i < out.count; i++) for (let k = 0; k < 4; k++) { const v = out.arr[i * 4 + k]; mn[k] = Math.min(mn[k], v); mx[k] = Math.max(mx[k], v); }
    if (!minMax) minMax = [mn, mx];
  }
  return minMax;
}
const nodeThighL = json.nodes.findIndex(n => n.name === 'thigh.L');
if (nodeThighL >= 0) {
  const [mn, mx] = quatRange(walk, nodeThighL);
  let d = 0; for (let k = 0; k < 4; k++) d = Math.max(d, mx[k] - mn[k]);
  check('thigh.L swings during Walk', d > 0.08, 'quat delta ' + d.toFixed(3));
} else check('thigh.L bone named in nodes', false);

console.log(fails ? 'VERIFY FAILED (' + fails + ')' : 'GLB VERIFY PASSED');
process.exit(fails ? 1 : 0);
