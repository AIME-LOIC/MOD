#!/usr/bin/env node
/* Compound Ops - LAN server (no dependencies, Node 14+)
   Usage:  node lan_server.js [port]
   Then open http://<this-machine-ip>:PORT/compound_game.html on every PC,
   choose SERVER PLAY, type a room name, and play. */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.argv[2]) || 8080;
const TICK = 50; // ms between state broadcasts
const rooms = new Map(); // name -> room

const fileCache = new Map();
function serveFile(res, name) {
  const full = path.join(__dirname, name);
  let mt = 0;
  try { mt = fs.statSync(full).mtimeMs; } catch (e) { res.writeHead(404); res.end('not found'); return; }
  const c = fileCache.get(full);
  if (!c || c.m !== mt) {
    try { fileCache.set(full, { m: mt, b: fs.readFileSync(full) }); }
    catch (e) { res.writeHead(404); res.end('not found'); return; }
  }
  const ext = path.extname(name).toLowerCase();
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json' }[ext] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': mime, 'Access-Control-Allow-Origin': '*' });
  res.end(fileCache.get(full).b);
}

const server = http.createServer((req, res) => {
  let url = decodeURIComponent((req.url || '/').split('?')[0]);
  if (url === '/ping') { res.writeHead(200, { 'Access-Control-Allow-Origin': '*' }); res.end('ok'); return; }
  if (url === '/' || url === '/index.html') url = '/compound_game.html';
  serveFile(res, url.slice(1));
});

function guid() { return crypto.randomBytes(16).toString('hex'); }
function wsAccept(key) {
  return crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
}
function makeMask(len) { const b = Buffer.alloc(4); crypto.randomFillSync(b); return b; }

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
    else if (len === 127) { if (off + 10 > buf.length) break; len = Number(buf.readBigUInt64BE(off + 2)); hdr = 10; }
    const maskKey = mask ? buf.slice(off + hdr, off + hdr + 4) : null;
    if (mask) hdr += 4;
    if (off + hdr + len > buf.length) break;
    let payload = buf.slice(off + hdr, off + hdr + len);
    if (maskKey) { payload = Buffer.from(payload); for (let i = 0; i < payload.length; i++) payload[i] ^= maskKey[i & 3]; }
    off += hdr + len;
    if (op === 8) { onMsg(null); return; } // close
    if (op === 10) { onMsg('__pong__'); continue; } // browser pong → liveness (background tabs throttle rAF)
    if (op === 1 || op === 2) onMsg(payload.toString('utf8'));
  }
  onLeft(buf.slice(off));
}

server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return; }
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + wsAccept(key) + '\r\n\r\n');
  socket.setNoDelay(true);
  let buf = Buffer.alloc(0);
  let alive = true;
  const player = { socket, id: guid(), name: null, room: null, state: null, lastSeen: Date.now() };

  const send = obj => { if (alive && socket.writable) { try { socket.write(encodeFrame(Buffer.from(JSON.stringify(obj)), 1)); } catch (e) {} } };

  socket.on('data', chunk => {
    buf = buf.length ? Buffer.concat([buf, chunk]) : chunk;
    if (buf.length > 1 << 20) { buf = Buffer.alloc(0); return; }
    decodeFrames(buf, msg => {
      if (msg === null) { cleanup(); return; }
      if (msg === '__pong__') { player.lastSeen = Date.now(); return; }
      let m; try { m = JSON.parse(msg); } catch (e) { return; }
      player.lastSeen = Date.now();
      if (m.t === 'join') {
        player.name = String(m.name || 'Rookie').slice(0, 16);
        const rname = String(m.room || 'ops').slice(0, 16).toLowerCase();
        let room = rooms.get(rname);
        if (!room) { room = { name: rname, map: String(m.map || 'compound'), players: new Map() }; rooms.set(rname, room); }
        player.room = room;
        player.id = m.pid || player.id;
        room.players.set(player.id, player);
        send({ t: 'welcome', id: player.id, room: rname, map: room.map, players: snapshot(room) });
        room.players.forEach(p => { if (p !== player) send2(p, { t: 'pjoin', id: player.id, name: player.name }); });
        console.log('[' + rname + '] ' + player.name + ' joined (' + room.players.size + ' in room)');
      } else if (m.t === 's' && player.room) {
        player.state = m; // {x,z,y,r,hp,am,v,dead,shoot,hs}
        player.room.dirty = true;
      } else if (m.t === 'ev' && player.room) {
        player.room.players.forEach(p => { if (p !== player) send2(p, { t: 'ev', id: player.id, k: m.k, a: m.a }); });
      } else if (m.t === 'name' && player.room) {
        player.name = String(m.name || player.name).slice(0, 16);
        player.room.players.forEach(p => { if (p !== player) send2(p, { t: 'pjoin', id: player.id, name: player.name }); });
      }
    }, left => { buf = left; });
  });
  const pingIv = setInterval(() => {
    if (!alive) return;
    try { socket.write(encodeFrame(Buffer.alloc(0), 9)); } // ping; a dead socket throws on write
    catch (e) { cleanup(); }
  }, 5000);
  const iv = setInterval(() => { if (Date.now() - player.lastSeen > 30000) cleanup(); }, 5000); // pongs keep background-tab players alive
  function cleanup() {
    if (!alive) return; alive = false;
    clearInterval(pingIv); clearInterval(iv);
    try { socket.end(); } catch (e) {}
    if (player.room) {
      player.room.players.delete(player.id);
      player.room.players.forEach(p => send2(p, { t: 'pleave', id: player.id }));
      if (player.room.players.size === 0) rooms.delete(player.room.name);
      console.log('[' + player.room.name + '] ' + player.name + ' left');
      player.room = null;
    }
  }
  socket.on('error', cleanup);
  socket.on('close', cleanup);
  socket.on('end', cleanup);      // abrupt disconnects (RST/half-close) fire 'end', not always 'close'
  socket.on('prefinish', cleanup);
});
function send2(p, obj) { if (p.socket && p.socket.writable) { try { p.socket.write(encodeFrame(Buffer.from(JSON.stringify(obj)), 1)); } catch (e) {} } }
function snapshot(room) {
  const out = [];
  room.players.forEach(p => out.push({ id: p.id, name: p.name }));
  return out;
}
// broadcast loop: each room's latest states to everyone else
setInterval(() => {
  rooms.forEach(room => {
    if (!room.dirty) return; room.dirty = false;
    const states = [];
    room.players.forEach(p => { if (p.state) states.push({ id: p.id, name: p.name, s: p.state }); });
    if (!states.length || room.players.size < 2) return;
    const msg = encodeFrame(Buffer.from(JSON.stringify({ t: 'st', players: states })), 1);
    room.players.forEach(p => { if (p.socket.writable) { try { p.socket.write(msg); } catch (e) {} } });
  });
}, TICK);

server.listen(PORT, () => {
  const nets = require('os').networkInterfaces();
  const ips = [];
  Object.values(nets).flat().forEach(n => { if (n && n.family === 'IPv4' && !n.internal) ips.push(n.address); });
  console.log('Compound Ops LAN server running on port ' + PORT);
  console.log('On this PC:            http://localhost:' + PORT + '/compound_game.html');
  ips.forEach(ip => console.log('On other PCs (LAN):    http://' + ip + ':' + PORT + '/compound_game.html'));
  console.log('Pick SERVER PLAY in the menu, use the same room name everywhere. Press Ctrl+C to stop.');
  console.log('');
  console.log('If other PCs cannot connect:');
  console.log(' 1) Allow Node.js through the firewall, or open the port:');
  console.log('    Windows (admin):  netsh advfirewall firewall add rule name="CompoundOps" dir=in action=allow protocol=TCP localport=' + PORT);
  console.log('    Linux:            sudo ufw allow ' + PORT + '/tcp');
  console.log(' 2) On the other PC open the http://IP:port address above in the browser (not the file).');
  console.log(' 3) The other PC needs internet access once, to load the three.js library.');
});
