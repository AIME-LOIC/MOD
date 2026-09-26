// Backend test: real game_server.js — health, room browser, quick match,
// state relay, chat, server-side kill scoring, leaderboard, rate limiting.
const http = require('http');
const crypto = require('crypto');
const { spawn } = require('child_process');

const PORT = 8188;
function get(path) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path }, r => {
      let b = ''; r.on('data', d => b += d); r.on('end', () => res({ status: r.statusCode, body: b }));
    }).on('error', rej);
  });
}
function wsFrame(payload, opcode = 1, mask = true) {
  const data = Buffer.from(payload);
  const len = data.length;
  let header;
  if (len < 126) header = Buffer.from([0x80 | opcode, (mask ? 0x80 : 0) | len]);
  else { header = Buffer.alloc(4); header[0] = 0x80 | opcode; header[1] = (mask ? 0x80 : 0) | 126; header.writeUInt16BE(len, 2); }
  if (!mask) return Buffer.concat([header, data]);
  const key = crypto.randomBytes(4);
  const masked = Buffer.from(data);
  for (let i = 0; i < masked.length; i++) masked[i] ^= key[i & 3];
  return Buffer.concat([header, key, masked]);
}
function wsClient(name, joinMsg) {
  return new Promise((resolve, reject) => {
    const net = require('net');
    const key = crypto.randomBytes(16).toString('base64');
    const sock = net.connect(PORT, '127.0.0.1', () => {
      sock.write(`GET /ws HTTP/1.1\r\nHost: localhost:${PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    });
    let buf = Buffer.alloc(0), upgraded = false;
    const client = { msgs: [], send: obj => sock.write(wsFrame(JSON.stringify(obj))), close: () => sock.destroy() };
    sock.on('data', d => {
      buf = Buffer.concat([buf, d]);
      if (!upgraded) {
        const idx = buf.indexOf('\r\n\r\n');
        if (idx < 0) return;
        const head = buf.slice(0, idx).toString();
        if (!/101/.test(head)) return reject(new Error('handshake failed: ' + head.split('\r\n')[0]));
        upgraded = true; buf = buf.slice(idx + 4);
        if (joinMsg) client.send(joinMsg);
      }
      let off = 0;
      while (off + 2 <= buf.length) {
        const len0 = buf[off + 1] & 0x7f; let len = len0, hdr = 2;
        if (len0 === 126) { if (off + 4 > buf.length) break; len = buf.readUInt16BE(off + 2); hdr = 4; }
        else if (len0 === 127) { if (off + 10 > buf.length) break; len = Number(buf.readBigUInt64BE(off + 2)); hdr = 10; }
        if (off + hdr + len > buf.length) break;
        client.msgs.push(JSON.parse(buf.slice(off + hdr, off + hdr + len).toString()));
        off += hdr + len;
      }
      buf = buf.slice(off);
      if (client.msgs.some(m => m.t === 'welcome')) resolve(client);
    });
    sock.on('error', reject);
    setTimeout(() => reject(new Error('ws timeout')), 4000);
  });
}
const wait = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const srv = spawn('node', ['game_server.js', String(PORT)], { cwd: __dirname, stdio: 'pipe' });
  srv.stdout.on('data', d => process.stdout.write('[srv] ' + d));
  srv.stderr.on('data', d => process.stdout.write('[srv-err] ' + d));
  await wait(700);
  let failed = 0;
  const check = (n, c, extra) => { console.log((c ? 'PASS: ' : 'FAIL: ') + n, extra !== undefined ? '(' + extra + ')' : ''); if (!c) failed++; };
  try {
    const h = await get('/api/health');
    const hj = JSON.parse(h.body);
    check('GET /api/health 200 ok:true', h.status === 200 && hj.ok === true);
    const page = await get('/compound_game.html');
    check('GET /compound_game.html served', page.status === 200 && page.body.length > 50000, page.body.length + ' bytes');

    const jm = { t: 'join', room: 'backend-room', name: 'Alice', pid: 'test-alice', map: 'compound', mode: 'ffa', pub: true };
    const a = await wsClient('Alice', jm);
    const wA = a.msgs.find(m => m.t === 'welcome');
    check('Alice joined private room', wA && wA.room === 'backend-room');
    const b = await wsClient('Bob', { t: 'join', room: 'backend-room', name: 'Bob', pid: 'test-bob', map: 'compound', mode: 'ffa', pub: true });
    await wait(200);
    check('Bob welcomed with existing roster (incl. Alice)', (() => { const w = b.msgs.find(m => m.t === 'welcome'); return w && w.players.some(p => p.name === 'Alice'); })());
    check('Alice saw pjoin for Bob', a.msgs.some(m => m.t === 'pjoin' && m.name === 'Bob'));

    // state relay
    a.send({ t: 's', x: 100, z: 58, y: 0, r: 0, hp: 100, am: 30, v: 5, dead: 0, shoot: 0, sx: 0, sy: 0, sz: 0 });
    await wait(300);
    check('state broadcast reaches Bob', b.msgs.some(m => m.t === 'st' && m.players.some(p => p.id === 'test-alice' && p.s.x === 100)));

    // chat relay
    a.send({ t: 'chat', m: 'hello from alice' });
    await wait(250);
    check('chat relayed to Bob', b.msgs.some(m => m.t === 'chat' && m.name === 'Alice' && m.m === 'hello from alice'));

    // server-side kill scoring: Alice kills Bob (by vid)
    a.send({ t: 'ev', k: 'kill', a: { a: 'Alice', b: 'Bob', vid: 'test-bob' } });
    await wait(250);
    const rooms = JSON.parse((await get('/api/rooms')).body);
    const ar = rooms.find(r => r.name === 'backend-room');
    check('kill counted on server (Alice k=1)', ar && ar.players.some(p => p.name === 'Alice' && p.k === 1), JSON.stringify(ar && ar.players));
    check('death counted on server (Bob d=1)', ar && ar.players.some(p => p.name === 'Bob' && p.d === 1));
    check('kill event relayed to Bob', b.msgs.some(m => m.t === 'ev' && m.k === 'kill'));

    // leaderboard persisted
    await wait(300);
    a.send({ t: 'lb' });
    await wait(400);
    check('global leaderboard has Alice with 1 kill', a.msgs.some(m => m.t === 'lb' && m.lb.some(p => p.name === 'Alice' && p.k >= 1)));
    check('scores.json written', require('fs').existsSync(__dirname + '/data/scores.json'));

    // quick match: joins the fullest public room with space; else opens a new one
    const q1 = await wsClient('Carol', { t: 'join', quick: 1, name: 'Carol', mode: 'ffa', map: 'compound' });
    const w1 = q1.msgs.find(m => m.t === 'welcome');
    check('quick match joined fullest public room (backend-room)', w1 && w1.quick === true && w1.room === 'backend-room', w1 && w1.room);
    const q2 = await wsClient('Dave', { t: 'join', quick: 1, name: 'Dave', mode: 'ffa', map: 'compound' });
    const w2 = q2.msgs.find(m => m.t === 'welcome');
    check('quick match pools players into same room', w2 && w2.room === w1.room, w1.room + ' vs ' + w2.room);

    // rooms listing over ws
    q2.send({ t: 'rooms' });
    await wait(300);
    check('ws rooms listing includes backend-room', q2.msgs.some(m => m.t === 'rooms' && m.rooms.some(r => r.name === 'backend-room')));

    // rate limiting: 200 rapid chats from Dave -> Bob should receive far fewer than sent (token bucket: 50 burst, 25/s)
    for (let i = 0; i < 200; i++) q2.send({ t: 'chat', m: 'spam' + i });
    await wait(1200);
    const relayed = b.msgs.filter(m => m.t === 'chat' && m.name === 'Dave').length;
    check('spam throttled by token bucket', relayed < 120, relayed + ' of 200 relayed');
    check('server survived spam without crash', (await get('/api/health')).status === 200);

    // leave notifications
    q1.close();
    await wait(400);
    check('Dave notified of Carol leaving', q2.msgs.some(m => m.t === 'pleave'));

    a.close(); b.close(); q2.close();
    console.log(failed === 0 ? 'BACKEND TEST PASSED' : 'BACKEND TEST FAILED: ' + failed + ' failures');
    process.exit(failed === 0 ? 0 : 1);
  } catch (e) {
    console.error('BACKEND TEST CRASHED:', e && e.stack || e);
    process.exit(1);
  } finally { srv.kill(); }
})();
