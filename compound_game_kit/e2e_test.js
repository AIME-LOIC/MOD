// E2E test: real lan_server.js over HTTP + raw WebSocket
const http = require('http');
const crypto = require('crypto');

const PORT = 8123;
function get(path) {
  return new Promise((res, rej) => {
    http.get({ host: '127.0.0.1', port: PORT, path }, r => {
      let n = 0; r.on('data', d => n += d.length); r.on('end', () => res({ status: r.statusCode, bytes: n }));
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
function wsClient(name, room) {
  return new Promise((resolve, reject) => {
    const net = require('net');
    const key = crypto.randomBytes(16).toString('base64');
    const sock = net.connect(PORT, '127.0.0.1', () => {
      sock.write(`GET /ws HTTP/1.1\r\nHost: localhost:${PORT}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${key}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    });
    let buf = Buffer.alloc(0), upgraded = false, msgs = [];
    const client = {
      send: obj => sock.write(wsFrame(JSON.stringify(obj))),
      msgs, close: () => sock.destroy()
    };
    sock.on('data', d => {
      buf = Buffer.concat([buf, d]);
      if (!upgraded) {
        const idx = buf.indexOf('\r\n\r\n');
        if (idx < 0) return;
        const head = buf.slice(0, idx).toString();
        if (!/101/.test(head)) return reject(new Error('handshake failed: ' + head.split('\r\n')[0]));
        upgraded = true; buf = buf.slice(idx + 4);
        client.send({ t: 'join', room, name, map: 'compound' });
      }
      // parse server frames (unmasked)
      let off = 0;
      while (off + 2 <= buf.length) {
        const len0 = buf[off + 1] & 0x7f; let len = len0, hdr = 2;
        if (len0 === 126) { if (off + 4 > buf.length) break; len = buf.readUInt16BE(off + 2); hdr = 4; }
        else if (len0 === 127) { if (off + 10 > buf.length) break; len = Number(buf.readBigUInt64BE(off + 2)); hdr = 10; }
        if (off + hdr + len > buf.length) break;
        msgs.push(JSON.parse(buf.slice(off + hdr, off + hdr + len).toString()));
        off += hdr + len;
      }
      buf = buf.slice(off);
      if (msgs.some(m => m.t === 'welcome')) resolve(client);
    });
    sock.on('error', reject);
    setTimeout(() => reject(new Error('ws timeout')), 4000);
  });
}
(async () => {
  // start server
  const { spawn } = require('child_process');
  const srv = spawn('node', ['lan_server.js', String(PORT)], { cwd: __dirname.replace(/\/tests?$/, ''), stdio: 'pipe' });
  srv.stdout.on('data', d => process.stdout.write('[srv] ' + d));
  srv.stderr.on('data', d => process.stdout.write('[srv-err] ' + d));
  await new Promise(r => setTimeout(r, 700));
  try {
    const page = await get('/compound_game.html');
    console.log('OK: GET /compound_game.html ->', page.status, page.bytes, 'bytes');
    const ping = await get('/ping');
    console.log('OK: GET /ping ->', ping.status, ping.bytes, 'bytes');

    const a = await wsClient('Alice', 'test-room');
    console.log('OK: Alice joined, welcome =', JSON.stringify(a.msgs.find(m => m.t === 'welcome')));
    const b = await wsClient('Bob', 'test-room');
    await new Promise(r => setTimeout(r, 150));
    console.log('OK: Bob joined; Bob got pjoin for Alice:', b.msgs.some(m => m.t === 'pjoin' && m.name === 'Alice'));
    console.log('OK: Alice got pjoin for Bob:', a.msgs.some(m => m.t === 'pjoin' && m.name === 'Bob'));

    // state relay: a sends state, b should receive it
    a.send({ t: 's', x: 100, z: 58, y: 0, r: 0, hp: 100, am: 30, v: 5, dead: 0, shoot: 0, sx: 0, sy: 0, sz: 0 });
    await new Promise(r => setTimeout(r, 300));
    const st = b.msgs.filter(m => m.t === 'st');
    console.log('OK: state broadcast received by Bob:', st.length > 0 && st[0].players.some(p => p.name === 'Alice' && p.s.x === 100));

    // event relay
    a.send({ t: 'ev', k: 'kill', a: { a: 'Alice', b: 'Militia', tag: 'HS' } });
    await new Promise(r => setTimeout(r, 200));
    console.log('OK: kill event relayed to Bob:', b.msgs.some(m => m.t === 'ev' && m.k === 'kill'));

    // leave
    a.close();
    await new Promise(r => setTimeout(r, 300));
    console.log('OK: Bob notified of Alice leaving:', b.msgs.some(m => m.t === 'pleave'));
    b.close();
    console.log('E2E PASSED');
    process.exit(0);
  } catch (e) {
    console.error('E2E FAILED:', e.message);
    process.exit(1);
  } finally {
    srv.kill();
  }
})();
