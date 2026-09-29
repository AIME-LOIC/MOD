// DUEL 1v1 verification over the real online backend (game_server.js): run `node duel_test.js`
// Alice + Bob join a duel room (capped at 2), states relay, kills credit the victim,
// Carol is refused (room full), and the room browser labels the mode 1v1 DUEL.
const http = require('http');
const crypto = require('crypto');

const PORT = 8129;
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
function wsClient(joinMsg) {
  return new Promise((resolve, reject) => {
    const net = require('net');
    const key = crypto.randomBytes(16).toString('base64');
    const sock = net.connect(PORT, '127.0.0.1', () => {
      sock.write(`GET /ws HTTP/1.1\r\nHost: localhost:${PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    });
    let buf = Buffer.alloc(0), upgraded = false; const msgs = [];
    const client = { send: obj => sock.write(wsFrame(JSON.stringify(obj))), msgs, close: () => sock.destroy() };
    sock.on('data', d => {
      buf = Buffer.concat([buf, d]);
      if (!upgraded) {
        const idx = buf.indexOf('\r\n\r\n');
        if (idx < 0) return;
        const head = buf.slice(0, idx).toString();
        if (!/101/.test(head)) return reject(new Error('handshake failed'));
        upgraded = true; buf = buf.slice(idx + 4);
        client.send(joinMsg);
      }
      let off = 0;
      while (off + 2 <= buf.length) {
        const len0 = buf[off + 1] & 0x7f; let len = len0, hdr = 2;
        if (len0 === 126) { if (off + 4 > buf.length) break; len = buf.readUInt16BE(off + 2); hdr = 4; }
        else if (len0 === 127) { if (off + 10 > buf.length) break; len = Number(buf.readBigUInt64BE(off + 2)); hdr = 10; }
        if (off + hdr + len > buf.length) break;
        try { msgs.push(JSON.parse(buf.slice(off + hdr, off + hdr + len).toString())); } catch (e) {}
        off += hdr + len;
      }
      buf = buf.slice(off);
      if (client.wantWelcome && msgs.some(m => m.t === 'welcome')) { client.wantWelcome = false; resolve(client); }
      if (msgs.some(m => m.t === 'err')) resolve(client);
    });
    sock.on('error', reject);
    client.wantWelcome = true;
    setTimeout(() => resolve(client), 3000); // resolve anyway; tests inspect msgs
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const { spawn } = require('child_process');
  const srv = spawn('node', ['game_server.js', String(PORT)], { cwd: __dirname, stdio: 'pipe' });
  await new Promise(done => {
    const poll = () => http.get({ host: '127.0.0.1', port: PORT, path: '/ping' }, r => { r.resume(); done(); }).on('error', () => setTimeout(poll, 200));
    poll();
  });

  let failed = 0;
  const check = (name, cond, extra) => { if (cond) console.log('PASS:', name, extra !== undefined ? '(' + extra + ')' : ''); else { console.log('FAIL:', name, extra !== undefined ? '(' + extra + ')' : ''); failed++ } };

  try {
    const alice = await wsClient({ t: 'join', room: 'dueltest', name: 'Alice', map: 'downtown', mode: 'duel' });
    const wA = alice.msgs.find(m => m.t === 'welcome');
    check('Alice joins duel room', wA && wA.mode === 'duel', wA ? 'mode=' + wA.mode : 'no welcome');
    check('duel room capped at 2 players', wA && wA.max === 2, wA ? 'max=' + wA.max : '?');

    const bob = await wsClient({ t: 'join', room: 'dueltest', name: 'Bob', map: 'downtown', mode: 'duel' });
    const wB = bob.msgs.find(m => m.t === 'welcome');
    check('Bob joins the same duel room', wB && wB.room === 'dueltest');
    await sleep(200);
    check('Alice notified of Bob joining', alice.msgs.some(m => m.t === 'pjoin' && m.name === 'Bob'));

    // states relay both ways
    alice.send({ t: 's', x: 10, z: 20, y: 0, r: 1, hp: 90, am: 30, v: 0, dead: 0, shoot: 0, sx: 0, sy: 1.5, sz: 0 });
    await sleep(250);
    const st = bob.msgs.find(m => m.t === 'st' && m.players.some(p => p.name === 'Alice' && p.s.x === 10));
    check('duel state broadcast reaches the rival', !!st);

    // PvP kill with victim crediting: Alice kills Bob
    const bobId = wB ? wB.players.find(p => p.name === 'Bob').id : 'bob';
    alice.send({ t: 'ev', k: 'kill', a: { a: 'Alice', b: 'Bob', tag: 'HS', vid: bobId } });
    await sleep(250);
    const ev = bob.msgs.find(m => m.t === 'ev' && m.k === 'kill' && m.a && m.a.b === 'Bob');
    check('kill event relays to the victim', !!ev);
    const wB2 = bob.msgs.filter(m => m.t === 'welcome').pop() || wB;

    // room full: Carol cannot squeeze into the duel
    const carol = await wsClient({ t: 'join', room: 'dueltest', name: 'Carol', map: 'downtown', mode: 'duel' });
    await sleep(250);
    const err = carol.msgs.find(m => m.t === 'err');
    check('third player refused — duel stays 1v1', !!err, err ? err.e : 'no error');

    // room browser labels the duel
    const br = await wsClient({ t: 'rooms' });
    br.send({ t: 'rooms' });
    await sleep(250);
    const rooms = br.msgs.filter(m => m.t === 'rooms').pop();
    const duelRoom = rooms && rooms.rooms.find(r => r.name === 'dueltest');
    check('room browser exposes duel mode', duelRoom && duelRoom.mode === 'duel', duelRoom ? 'mode=' + duelRoom.mode : 'missing');
    br.close();

    alice.close(); bob.close(); carol.close();
  } catch (e) { console.log('FAIL: exception —', e.message); failed++ }

  srv.kill();
  console.log(failed ? 'DUEL TEST FAILED (' + failed + ')' : 'DUEL TEST PASSED');
  process.exit(failed ? 1 : 0);
})();
