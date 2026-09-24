// Minimal repro: does the real server notice an abrupt client disconnect?
const net = require('net');
const crypto = require('crypto');
const { spawn } = require('child_process');
const PORT = 8252;
const srv = spawn('node', ['lan_server.js', String(PORT)], { stdio: ['ignore', 'pipe', 'pipe'] });
srv.stdout.on('data', d => process.stdout.write('[out] ' + d));
srv.stderr.on('data', d => process.stdout.write('[err] ' + d));

const waitReady = () => new Promise(res => {
  const tryConn = () => {
    const probe = net.connect(PORT, '127.0.0.1');
    probe.on('connect', () => { probe.destroy(); res(); });
    probe.on('error', () => setTimeout(tryConn, 200));
  };
  tryConn();
});

(async () => {
  await waitReady();
  const s = net.connect(PORT, '127.0.0.1', () => {
    s.write(`GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${crypto.randomBytes(16).toString('base64')}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
  });
  let step = 0;
  s.on('data', d => {
    step++;
    if (step === 1) { // 101 handshake received -> send join
      const p = Buffer.from(JSON.stringify({ t: 'join', room: 'repro', name: 'Ghost' }));
      const mask = crypto.randomBytes(4), mk = Buffer.from(p);
      for (let i = 0; i < mk.length; i++) mk[i] ^= mask[i & 3];
      s.write(Buffer.concat([Buffer.from([0x81, 0x80 | p.length]), mask, mk]));
      setTimeout(() => { console.log('[test] destroying client socket now'); s.destroy(); }, 400);
    }
  });
  s.on('error', e => console.log('[test] client err', e.code));
  setTimeout(() => { console.log('[test] done — if no "[repro] Ghost left" above, server missed the disconnect'); srv.kill(); process.exit(0); }, 2500);
})();
