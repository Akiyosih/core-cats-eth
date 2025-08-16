import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { randomBytes } from 'crypto';
import Database from 'better-sqlite3';
import { Wallet, getBytes, solidityPackedKeccak256 } from 'ethers';

const PORT = process.env.PORT ? Number(process.env.PORT) : 8787;
const CORE_CATS_ADDRESS = (process.env.CORE_CATS_ADDRESS || '').toLowerCase();

const SIGNER_PRIVATE_KEY = process.env.SIGNER_PRIVATE_KEY;
const SIGNER_ADDRESS     = (process.env.SIGNER_ADDRESS || '').toLowerCase();

if (!SIGNER_PRIVATE_KEY || !SIGNER_ADDRESS || !CORE_CATS_ADDRESS) {
  console.error('SIGNER_PRIVATE_KEY / SIGNER_ADDRESS / CORE_CATS_ADDRESS が .env に未設定です');
  process.exit(1);
}

// シンプルな SQLite（./nonce.sqlite）で nonce の再利用禁止を担保
const db = new Database('./nonce.sqlite');
db.exec(`
CREATE TABLE IF NOT EXISTS nonces(
  nonce TEXT PRIMARY KEY,
  to_addr TEXT NOT NULL,
  expiry INTEGER NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nonces_expiry ON nonces(expiry);
`);

// 期限切れの掃除
function gcExpired() {
  const now = Math.floor(Date.now() / 1000);
  db.prepare('DELETE FROM nonces WHERE used=1 OR expiry < ?').run(now - 3600);
}

// ECDSA 署名（EIP-191 前置詞は signMessage 側で付与される）
// inner = keccak256(abi.encode(to, nonce, expiry))
// signature = signer.signMessage(bytes32(inner))
const signer = new Wallet(SIGNER_PRIVATE_KEY);

const app = express();
app.use(cors());
app.use(express.json());

// 健康確認
app.get('/health', (_req, res) => res.json({ ok: true, signer: SIGNER_ADDRESS }));

// 署名発行
app.post('/get-signature', async (req, res) => {
  try {
    const { to } = req.body || {};
    if (!to || typeof to !== 'string' || !to.startsWith('0x') || to.length !== 42) {
      return res.status(400).json({ error: 'invalid to' });
    }
    const toAddr = to.toLowerCase();

    // 期限（秒）: 既定 300 秒（5分）
    const expirySecDefault = 300;
    const now = Math.floor(Date.now() / 1000);
    const expiry = now + expirySecDefault;

    // 乱数 nonce（32 bytes -> hex）
    const nonceBytes = randomBytes(32);
    const nonce = '0x' + nonceBytes.toString('hex');

    // DB へ保存（未使用として記録）
    db.prepare('INSERT INTO nonces(nonce, to_addr, expiry, used, created_at) VALUES(?,?,?,?,?)')
      .run(nonce, toAddr, expiry, 0, now);

    // CoreCats.sol と同一: keccak256(abi.encodePacked(to, nonce, expiry, block.chainid, address(this)))
    // ethers v6: solidityPackedKeccak256 を使う
    const chainId = Number(process.env.CHAIN_ID || 11155111); // Sepolia 既定
    const innerHash = solidityPackedKeccak256(
      ['address','bytes32','uint256','uint256','address'],
      [toAddr, nonce, expiry, chainId, CORE_CATS_ADDRESS]
    );

    // signMessage(bytes): EIP-191 前置詞付き
    const sig = await signer.signMessage(getBytes(innerHash));

    // 簡易レスポンス
    res.json({
      to: toAddr,
      nonce,
      expiry,
      signature: sig,
      signer: SIGNER_ADDRESS,
      algorithm: 'EIP-191(personal_sign) over keccak256(abi.encodePacked(address,bytes32,uint256,uint256,address))'
    });

    // 後始末（期限切れの掃除はベストエフォート）
    gcExpired();
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: 'internal' });
  }
});

// nonce を使用済みにする（mint 後に呼ぶ用途 / 任意）
app.post('/mark-used', (req, res) => {
  const { nonce } = req.body || {};
  if (!nonce || typeof nonce !== 'string') return res.status(400).json({ error: 'invalid nonce' });
  const row = db.prepare('SELECT nonce, used FROM nonces WHERE nonce=?').get(nonce);
  if (!row) return res.status(404).json({ error: 'not found' });
  if (row.used) return res.json({ ok: true, already: true });
  db.prepare('UPDATE nonces SET used=1 WHERE nonce=?').run(nonce);
  return res.json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`signature server listening on http://localhost:${PORT}`);
});
