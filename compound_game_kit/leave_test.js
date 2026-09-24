// Focused debug: late-joiner welcome snapshot + pleave on abrupt disconnect
const net = require('net');
const crypto = require('crypto');
const { spawn } = require('child_process');
const PORT = 8241;
const srv = spawn('node', ['lan_server.js', String(PORT)], { stdio: 'pipe' });
srv.stdout.on('data', d => process.stdout.write('[srv] ' + d));
srv.stderr.on('data', d => process.stdout.write('[srv-err] ' + d));

function client(name, onMsg) {
  return new Promise(resolve => {
    const s = net.connect(PORT, '127.0.0.1', () => {
      s.write(`GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${crypto.randomBytes(16).toString('base64')}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    });
    let up = false, buf = Buffer.alloc(0), msgs = [];
    s.on('data', d => {
      buf = Buffer.concat([buf, d]);
      if (!up) {
        const i = buf.indexOf('\r\n\r\n');
        if (i < 0) return;
        up = true; buf = buf.slice(i + 4);
        const send = p => {
          const payload = Buffer.from(JSON.stringify(p));
          const mask = crypto.randomBytes(4), mk = Buffer.from(payload);
          for (let i2 = 0; i2 < mk.length; i2++) mk[i2] ^= mask[i2 & 3];
          s.write(Buffer.concat([Buffer.from([0x81, 0x80 | payload.length]), mask, mk]));
        };
        send({ t: 'join', room: 'dbg', name, map: 'compound' });
        resolve({ sock: s, send, msgs });
        return;
      }
      let off = 0;
      while (off + 2 <= buf.length) {
        const l0 = buf[off + 1] & 0x7f; let len = l0, hdr = 2;
        if (l0 === 126) { if (off + 4 > buf.length) break; len = buf.readUInt16BE(off + 2); hdr = 4; }
        if (off + hdr + len > buf.length) break;
        msgs.push(JSON.parse(buf.slice(off + hdr, off + hdr + len).toString()));
        off += hdr + len;
      }
      buf = buf.slice(off);
      if (onMsg) onMsg(msgs[msgs.length - 1]);
    });
  });
}
(async () => {
  await new Promise(r => setTimeout(r, 600));
  const alice = await client('Alice');
  await new Promise(r => setTimeout(r, 300));
  const bob = await client('Bob');
  await new Promise(r => setTimeout(r, 300));
  console.log('Bob got pjoin for Alice:', bob.msgs.some(m => m.t === 'pjoin' && m.name === 'Alice'));
  alice.sock.destroy();
  await new Promise(r => setTimeout(r, 500));
  console.log('Bob got pleave:', bob.msgs.some(m => m.t === 'pleave'));
  console.log('Bob welcome players:', JSON.stringify(bob.msgs.find(m => m.t === 'welcome')?.players));
  srv.kill();
  process.exit(0);
})();
