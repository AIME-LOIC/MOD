#!/usr/bin/env node
/* ============================================================
   COMPOUND OPS — ONLINE MULTIPLAYER SERVER (deployable)
   Dependency-free Node 16+.  Usage:  node game_server.js [port]
   Deploy anywhere that runs Node (Render / Railway / Fly / VPS / Pterodactyl):
     - start command:  node game_server.js   (PORT from env or argv)
     - health check:   GET /api/health  -> 200 {"ok":true,...}
   Everything the LAN server does, plus:
     - PUBLIC room browser     GET /api/rooms
     - QUICK MATCH matchmaking (join {quick:1} -> fullest open room)
     - in-game CHAT relay
     - PERSISTENT score board  (data/scores.json: kills/deaths/wins/matches)
     - rate limiting + payload caps + room/player caps (safe on public internet)
   ============================================================ */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const zlib = require('zlib');

const PORT = Number(process.argv[2] || process.env.PORT) || 8080;
const TICK = 50;                    // ms between state broadcasts
const MAX_ROOMS = 64;               // concurrent room cap
const MAX_PLAYERS = 24;             // per room
const ROOM_TTL = 10 * 60 * 1000;    // empty rooms are dropped after 10 min
const SCORES_FILE = path.join(__dirname, 'data', 'scores.json');
const MSG_BUDGET = 50, MSG_REFILL = 25; // per-sec token bucket per socket
const state = { rooms: new Map(), scores: new Map() };

/* ---------------- persistence (leaderboard) ---------------- */
function loadScores() {
  try { const j = JSON.parse(fs.readFileSync(SCORES_FILE, 'utf8')); if (j && j.scores) for (const k in j.scores) state.scores.set(k, j.scores[k]); }
  catch (e) {}
}
let scoresDirty = false, lastFlush = 0;
function touchScores() { scoresDirty = true; }
function flushScores(force) {
  if (!scoresDirty) return;
  const now = Date.now();
  if (!force && lastFlush !== 0 && now - lastFlush < 10000) return;
  try {
    fs.mkdirSync(path.dirname(SCORES_FILE), { recursive: true });
    const out = {}; state.scores.forEach((v, k) => out[k] = v);
    fs.writeFileSync(SCORES_FILE, JSON.stringify({ v: 1, t: now, scores: out }));
    scoresDirty = false; lastFlush = now;
  } catch (e) {}
}
function player(name) {
  const k = String(name || '').toLowerCase();
  let s = state.scores.get(k);
  if (!s) { s = { name: String(name || ''), k: 0, d: 0, w: 0, m: 0, last: 0 }; state.scores.set(k, s); }
  if (name) s.name = String(name).slice(0, 16);
  return s;
}
function topPlayers(n) {
  const arr = []; state.scores.forEach(s => { if (s.k || s.d || s.w || s.m) arr.push(s); });
  arr.sort((a, b) => (b.k - a.k) || (b.w - a.w) || (a.d - b.d));
  return arr.slice(0, n).map(s => ({ name: s.name, k: s.k, d: s.d, w: s.w, m: s.m }));
}
loadScores();

/* ---------------- rooms ---------------- */
function guid() { return crypto.randomBytes(16).toString('hex'); }
function roomCode() { const A = 'ACDEFHJKLMNPRTUVWXY345789'; let s = ''; for (let i = 0; i < 5; i++) s += A[crypto.randomBytes(1)[0] % A.length]; return s; }
function getRoom(name, map, mode, pub, maxPlayers) {
  let r = state.rooms.get(name);
  if (r) return r;
  if (state.rooms.size >= MAX_ROOMS) return null;
  r = { name, map: map || 'compound', mode: mode || 'coop', pub: pub !== false, max: Math.max(2, Math.min(MAX_PLAYERS, maxPlayers || MAX_PLAYERS)), created: Date.now(), players: new Map(), board: new Map(), dirty: false, chatSeq: 0 };
  state.rooms.set(name, r);
  return r;
}
function roomInfo(r) {
  const players = [];
  r.players.forEach(p => players.push({ id: p.id, name: p.name, k: p.kills, d: p.deaths }));
  return { name: r.name, map: r.map, mode: r.mode, pub: r.pub, max: r.max, players };
}
function roomBoard(r) {
  const arr = []; r.board.forEach(s => arr.push(s));
  arr.sort((a, b) => (b.k - a.k) || (a.d - b.d));
  return arr.slice(0, 10).map(s => ({ name: s.name, k: s.k, d: s.d }));
}

/* ---------------- static files ---------------- */
const fileCache = new Map();
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.json': 'application/json', '.glb': 'model/gltf-binary', '.png': 'image/png', '.ico': 'image/x-icon' };
function serveFile(res, name, req) {
  if (!/^[\w. -]+$/.test(name) || name.includes('..')) { res.writeHead(404); res.end('not found'); return; }
  const full = path.join(__dirname, name);
  let mt = 0;
  try { mt = fs.statSync(full).mtimeMs; } catch (e) { res.writeHead(404); res.end('not found'); return; }
  const c = fileCache.get(full);
  if (!c || c.m !== mt) {
    try { const b = fs.readFileSync(full); fileCache.set(full, { m: mt, b, g: zlib.gzipSync(b, { level: 9 }) }); } catch (e) { res.writeHead(404); res.end('not found'); return; }
  }
  const ext = path.extname(name).toLowerCase();
  const cc = fileCache.get(full);
  const gz = !!req && /gzip/.test(String(req.headers['accept-encoding'] || '')) && /\.(html|js|json|css|txt)$/.test(name); /* glb is already compressed */
  if (gz) res.setHeader('Content-Encoding', 'gzip');
  res.writeHead(200, {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'Access-Control-Allow-Origin': '*',
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': 'public, max-age=86400',
    'Content-Length': (gz ? cc.g : cc.b).length
  });
  res.end(gz ? cc.g : cc.b);
}

/* ---------------- HTTP ---------------- */
const server = http.createServer((req, res) => {
  let url;
  try { url = decodeURIComponent((req.url || '/').split('?')[0]); } catch (e) { res.writeHead(400); res.end(); return; }
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  if (url === '/ping' || url === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, game: 'compound-ops', rooms: state.rooms.size, players: [...state.rooms.values()].reduce((n, r) => n + r.players.size, 0), uptime: Math.round(process.uptime()), t: Date.now() }));
    return;
  }
  if (url === '/api/rooms') {
    const out = [];
    state.rooms.forEach(r => { if (r.pub) out.push(roomInfo(r)); });
    out.sort((a, b) => b.players.length - a.players.length);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(out));
    return;
  }
  if (url === '/' || url === '/index.html') url = '/compound_game.html';
  serveFile(res, url.slice(1), req);
});

/* ---------------- websocket plumbing (no deps) ---------------- */
function wsAccept(key) { return crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64'); }
function encodeFrame(data, opcode) {
  const len = data.length;
  let header;
  if (len < 126) header = Buffer.from([0x80 | opcode, len]);
  else if (len < 65536) { header = Buffer.alloc(4); header[0] = 0x80 | opcode; header[1] = 126; header.writeUInt16BE(len, 2); }
  else { header = Buffer.alloc(10); header[0] = 0x80 | opcode; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2); }
  return Buffer.concat([header, data]);
}
function decodeFrames(buf, onMsg, onLeft) {
  let off = 0;
  while (off + 2 <= buf.length) {
    const fin = buf[off] & 0x80, op = buf[off] & 0x0f;
    let len = buf[off + 1] & 0x7f, mask = buf[off + 1] & 0x80, hdr = 2;
    if (len === 126) { if (off + 4 > buf.length) break; len = buf.readUInt16BE(off + 2); hdr = 4; }
    else if (len === 127) { if (off + 10 > buf.length) break; if (len && buf.readBigUInt64BE(off + 2) > 1 << 20) { onMsg(null); return; } len = Number(buf.readBigUInt64BE(off + 2)); hdr = 10; }
    const maskKey = mask ? buf.slice(off + hdr, off + hdr + 4) : null;
    if (mask) hdr += 4;
    if (off + hdr + len > buf.length) break;
    let payload = buf.slice(off + hdr, off + hdr + len);
    if (maskKey) { payload = Buffer.from(payload); for (let i = 0; i < payload.length; i++) payload[i] ^= maskKey[i & 3]; }
    off += hdr + len;
    if (op === 8) { onMsg(null); return; }
    if (op === 10) { onMsg('__pong__'); continue; } // browser pong → counts as liveness (background tabs throttle rAF to 0 FPS)
    if (op === 1 || op === 2) onMsg(payload.toString('utf8'));
  }
  onLeft(buf.slice(off));
}
function send2(p, obj) { if (p.socket && p.socket.writable) { try { p.socket.write(encodeFrame(Buffer.from(JSON.stringify(obj)), 1)); } catch (e) {} } }

/* ---------------- upgrade / gameplay ---------------- */
server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return; }
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + wsAccept(key) + '\r\n\r\n');
  socket.setNoDelay(true);
  let buf = Buffer.alloc(0), alive = true, tokens = MSG_BUDGET, lastTk = Date.now();

  const pl = { socket, id: guid(), name: null, room: null, state: null, kills: 0, deaths: 0, lastSeen: Date.now() };
  const send = o => send2(pl, o);

  function budget() { // token bucket: burst 50, refill 25/s
    const now = Date.now(); tokens = Math.min(MSG_BUDGET, tokens + (now - lastTk) * MSG_REFILL / 1000); lastTk = now;
    if (tokens < 1) return false; tokens -= 1; return true;
  }
  function cleanup() {
    if (!alive) return; alive = false;
    clearInterval(pingIv); clearInterval(ttlIv);
    try { socket.end(); } catch (e) {}
    if (pl.room) {
      const r = pl.room;
      r.players.delete(pl.id);
      r.players.forEach(p => send2(p, { t: 'pleave', id: pl.id, name: pl.name }));
      if (r.players.size === 0) { if (!r.kept) state.rooms.delete(r.name); }
      console.log('[' + r.name + '] ' + pl.name + ' left (' + r.players.size + ' left)');
      pl.room = null;
    }
    flushScores(false);
  }
  socket.on('data', chunk => {
    buf = buf.length ? Buffer.concat([buf, chunk]) : chunk;
    if (buf.length > 1 << 20) { cleanup(); return; }
    decodeFrames(buf, msg => {
      if (msg === null) { cleanup(); return; }
      if (msg === '__pong__') { pl.lastSeen = Date.now(); return; } // keepalive from auto-pong
      if (!budget()) return;
      let m; try { m = JSON.parse(msg); } catch (e) { return; }
      pl.lastSeen = Date.now();
      if (m.t === 'join') {
        if (pl.room) return;
        pl.name = String(m.name || 'Rookie').replace(/[^\w \-.]/g, '').trim().slice(0, 16) || 'Rookie';
        pl.id = (typeof m.pid === 'string' && m.pid.length <= 32 && /^[\w-]+$/.test(m.pid)) ? m.pid : pl.id;
        let rname, map = String(m.map || 'compound').slice(0, 16), mode = String(m.mode || 'coop').slice(0, 10);
        const quick = m.quick === true || m.quick === 1 || m.quick === '1' || m.quick === 'true'; // tolerate numeric/string quick flags from clients
        if (quick) { // QUICK MATCH: fullest public room with space, else new room
          let best = null;
          state.rooms.forEach(r => { if (r.pub && r.players.size < r.max) { if (m.mode && r.mode !== m.mode) return; if (!best || r.players.size > best.players.size) best = r; } });
          if (best) rname = best.name;
          else { rname = (mode === 'ffa' ? 'match-' : 'squad-') + roomCode(); mode = m.mode || 'coop'; }
        } else {
          rname = String(m.room || 'ops').replace(/[^\w-]/g, '').toLowerCase().slice(0, 20) || 'ops';
        }
        let r = getRoom(rname, map, mode, quick ? true : m.pub !== false, m.maxPlayers);
        if (!r) { send({ t: 'err', e: 'Server full — try again later' }); return; }
        if (r.players.size >= r.max) {
          if (quick) { rname = (mode === 'ffa' ? 'match-' : 'squad-') + roomCode(); r = getRoom(rname, map, mode, true, m.maxPlayers); }
          if (!r || r.players.size >= r.max) { send({ t: 'err', e: 'Room "' + rname + '" is full (' + r.max + ' players)' }); return; }
        }
        pl.room = r; pl.kills = 0; pl.deaths = 0;
        r.players.set(pl.id, pl);
        send({ t: 'welcome', id: pl.id, room: r.name, map: r.map, mode: r.mode, max: r.max, quick: quick, players: roomInfo(r).players, lb: topPlayers(10) });
        r.players.forEach(p => { if (p !== pl) send2(p, { t: 'pjoin', id: pl.id, name: pl.name }); });
        console.log('[' + r.name + '] ' + pl.name + ' joined' + (quick ? ' (quick match)' : '') + ' (' + r.players.size + '/' + r.max + ')');
      } else if (m.t === 's' && pl.room) {
        pl.state = m; pl.room.dirty = true;
      } else if (m.t === 'ev' && pl.room) {
        const r = pl.room, a = m.a || {};
        if (m.k === 'kill') { // update live scoreboard + global scores (server-side)
          pl.kills = Math.min(999, pl.kills + 1);
          const vid = typeof a.vid === 'string' && r.players.get(a.vid);
          if (vid) { vid.deaths = Math.min(9999, vid.deaths + 1); player(vid.name).d++; }
          player(pl.name).k++; player(pl.name).last = Date.now();
          touchScores();
          r.board.set(pl.id, { name: pl.name, k: pl.kills, d: pl.deaths });
          if (vid) r.board.set(vid.id, { name: vid.name, k: vid.kills, d: vid.deaths });
        } else if (m.k === 'win' && typeof a.w === 'string') {
          const w = player(a.w); w.w++; w.m++; w.last = Date.now(); touchScores();
          r.board.forEach(s => { const g = player(s.name); g.m++; });
        } else if (m.k === 'end') { // match summary -> count a match for everyone present
          r.board.forEach(s => { const g = player(s.name); g.m++; g.last = Date.now(); }); touchScores();
        }
        r.players.forEach(p => { if (p !== pl) send2(p, { t: 'ev', id: pl.id, k: m.k, a: m.a }); });
      } else if (m.t === 'chat' && pl.room) {
        const txt = String(m.m || '').slice(0, 120);
        if (!txt) return;
        pl.room.players.forEach(p => { if (p !== pl) send2(p, { t: 'chat', id: pl.id, name: pl.name, m: txt }); });
      } else if (m.t === 'name' && pl.room) {
        pl.name = String(m.name || pl.name).replace(/[^\w \-.]/g, '').trim().slice(0, 16) || pl.name;
        pl.room.players.forEach(p => { if (p !== pl) send2(p, { t: 'pjoin', id: pl.id, name: pl.name }); });
      } else if (m.t === 'rooms') { // list public rooms on demand
        const out = [];
        state.rooms.forEach(r => { if (r.pub) out.push({ name: r.name, mode: r.mode, map: r.map, n: r.players.size, max: r.max }); });
        out.sort((a, b) => b.n - a.n);
        send({ t: 'rooms', rooms: out });
      } else if (m.t === 'lb') {
        send({ t: 'lb', lb: topPlayers(10) });
      }
    }, left => { buf = left; });
  });

  const pingIv = setInterval(() => {
    if (!alive) return;
    try { socket.write(encodeFrame(Buffer.alloc(0), 9)); } catch (e) { cleanup(); }
  }, 5000);
  const ttlIv = setInterval(() => { if (Date.now() - pl.lastSeen > 30000) cleanup(); }, 5000); // 30s: pongs keep background-tab players alive

  socket.on('error', cleanup);
  socket.on('close', cleanup);
  socket.on('end', cleanup);
  socket.on('prefinish', cleanup);
});

/* ---------------- broadcast loop + housekeeping ---------------- */
setInterval(() => {
  state.rooms.forEach(room => {
    if (!room.dirty) return; room.dirty = false;
    const states = [];
    room.players.forEach(p => { if (p.state) states.push({ id: p.id, name: p.name, s: p.state }); });
    if (!states.length || room.players.size < 2) return;
    const msg = encodeFrame(Buffer.from(JSON.stringify({ t: 'st', players: states })), 1);
    room.players.forEach(p => { if (p.socket.writable) { try { p.socket.write(msg); } catch (e) {} } });
  });
}, TICK);
setInterval(() => { // drop empty stale rooms
  const now = Date.now();
  state.rooms.forEach((r, name) => { if (r.players.size === 0 && now - r.created > ROOM_TTL && !r.kept) state.rooms.delete(name); });
  flushScores(false);
}, 30000);
setInterval(() => flushScores(true), 60000);

process.on('SIGTERM', () => { flushScores(true); process.exit(0); });
process.on('SIGINT', () => { flushScores(true); process.exit(0); });

server.listen(PORT, () => {
  console.log('==========================================================');
  console.log(' Compound Ops ONLINE server  —  port ' + PORT);
  console.log('==========================================================');
  console.log(' Game:            http://localhost:' + PORT + '/');
  console.log(' Health check:    http://localhost:' + PORT + '/api/health');
  console.log(' Public rooms:    http://localhost:' + PORT + '/api/rooms');
  console.log(' Deploy: keep "node game_server.js" as the start command;');
  console.log('         expose TCP ' + PORT + ' (env PORT is respected).');
  console.log('==========================================================');
});
