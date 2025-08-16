import 'dotenv/config';
import { JsonRpcProvider, Wallet, Contract } from 'ethers';
import fs from 'fs';

const CONTRACT = "0xB9b44398952D3F38CB66d9f5bD2bd03B0B809C1A"; // CoreCats

async function main() {
  const TO     = process.env.MINT_TO || process.env.PUBLIC_ADDRESS || ''; // 自分のEOAなど
  const RPC    = process.env.SEPOLIA_RPC_URL!;
  const OWNER  = process.env.PRIVATE_KEY!; // オーナー鍵である必要はない（mint を送るのは受益者でOK、手数料負担者）
  if (!TO || !RPC || !OWNER) throw new Error('MINT_TO/SEPOLIA_RPC_URL/PRIVATE_KEY を確認してください');

  // サーバから署名を取得
  const sigRes = await fetch('http://localhost:8787/get-signature', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ to: TO })
  });
  if (!sigRes.ok) throw new Error('get-signature failed');
  const { to, nonce, expiry, signature } = await sigRes.json();

  // コントラクト attach
  const abi = JSON.parse(fs.readFileSync('artifacts/contracts/CoreCats.sol/CoreCats.json','utf8')).abi;
  const provider = new JsonRpcProvider(RPC);
  const wallet   = new Wallet(OWNER, provider);
  const cc = new Contract(CONTRACT, abi, wallet);

  console.log('mint to:', to);
  const tx = await cc.mint(to, nonce, expiry, signature);
  console.log('tx:', tx.hash);
  const receipt = await tx.wait();
  console.log('status:', receipt?.status);

  // 使用済みマーキング（任意）
  await fetch('http://localhost:8787/mark-used', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ nonce })
  }).catch(()=>{});
}

main().catch((e) => { console.error(e); process.exit(1); });
