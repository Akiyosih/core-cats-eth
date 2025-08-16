# VERIFY.md

## CoreCats デプロイ履歴と検証手順

この文書は、CoreCats コントラクトのデプロイ履歴と、オンチェーン上でソースコードおよびバイトコードを検証するための手順をまとめたものです。

---

## 0. 概要（検証ポリシー）
- 目的: 誰でも同一手順でローカルの `deployedBytecode` がオンチェーン `runtime bytecode` と一致することを再現できるようにする。
- 前提: Node 18+ / npm、Hardhat v3 系、solc 0.8.28（optimizer enabled, runs=200）。
- 重要ファクト: Verified コントラクト、Etherscan の `#code` ページ、および本リポジトリの `hardhat.config.ts` に記載のコンパイル設定を信頼の起点とする。

## 1. デプロイ履歴（カノニカル）

### ネットワーク: Sepolia (chainId=11155111)
- Contract: CoreCats
- Address: 0xB9b44398952D3F38CB66d9f5bD2bd03B0B809C1A
- Explorer (Verified): https://sepolia.etherscan.io/address/0xB9b44398952D3F38CB66d9f5bD2bd03B0B809C1A#code
- Deployment (Ignition): deploymentId = corecats-clean-a
- Owner EOA: 0xE328e01379c0FC494cabB325AD48ef4b14074a4D
- Tx (first mint via server signature): 0x568679b87ea84bc3663e0dd5f912a5c62581d42f1542b9e90aa3b9d313b645e9
- Signature scheme (server): EIP-191(personal_sign) over keccak256(abi.encodePacked(address to, bytes32 nonce, uint256 expiry, uint256 chainid, address contract))

## 1'. 過去のデプロイ履歴

### デプロイ者アドレス: 0x0F6571F9D5f2698c908A9c2f592151e2BF5aEEb1
- Transaction Hash: 0x42dd8d0c1bbce4c24fd4a6f1fd6cbbc4822f2db1a61785b00668b61901ae1a7f  
  内容: Contract Creation  
- Transaction Hash: 0xcb2e717a96b55a4acbe32dde989870b689555c65e7fdbad737eeb54870d61169  
  内容: Create: CoreCats  

### デプロイ者アドレス: 0xE328e01379c0FC494cabB325AD48ef4b14074a4D
- Transaction Hash: 0x66fdceb618c58454e2a9eae3f46f84542f87ea456c0ed1be343795e0fc474e1a  
  内容: Contract Creation  

---

## 2. 検証手順（Sepolia カノニカル）
1. 上記カノニカルの Explorer を開く（Verified 表示を確認）
2. ローカルで `npx hardhat compile` 実行後、`artifacts/.../CoreCats.json` の `deployedBytecode.object` を取得
3. RPC の `eth_getCode(0xB9b4...C1A)` と keccak256 を突き合わせて一致を確認
4. `owner()` が「Owner EOA」と一致すること、`setSigner` 実行Txが反映されていることを確認

### 2.5. 再現ビルド／バイトコード一致検証コマンド（例）
- 事前準備: `.env` に `SEPOLIA_RPC_URL` を設定済みであること。
- 1) ローカルの runtime bytecode（deployedBytecode）ハッシュを取得
  - `node -e "const fs=require('fs');const a=JSON.parse(fs.readFileSync('artifacts/contracts/CoreCats.sol/CoreCats.json','utf8'));const b='0x'+a.deployedBytecode.object;const {keccak256}=require('ethereum-cryptography/keccak');const {hexToBytes,bytesToHex}=require('ethereum-cryptography/utils');console.log('local:',bytesToHex(keccak256(hexToBytes(b))));"`
- 2) オンチェーンの runtime bytecode ハッシュを取得（eth_getCode）
  - `node -e "require('dotenv/config');(async()=>{const {JsonRpcProvider}=require('ethers');const p=new JsonRpcProvider(process.env.SEPOLIA_RPC_URL);const code=await p.getCode('0xB9b44398952D3F38CB66d9f5bD2bd03B0B809C1A');const {keccak256}=require('ethereum-cryptography/keccak');const {hexToBytes,bytesToHex}=require('ethereum-cryptography/utils');console.log('chain:',bytesToHex(keccak256(hexToBytes(code))));})();"`

### 2.6. ミント検証（サーバ署名経由）
1. `POST /get-signature` に to=受益者EOA を渡し、`nonce/expiry/signature` を取得
2. `mint(to, nonce, expiry, signature)` を送信（Sepolia）
3. 当該 Tx の Logs に ERC721 Transfer が存在し、`to` と `tokenId` を確認
4. `tokenURI(tokenId)` を取得し、Base64 SVG が解釈できることを確認

## 2'. 過去履歴の検証手順

1. CoreScan（または対応するブロックチェーンエクスプローラ）を開く  
2. 上記の各 Transaction Hash を検索  
3. コントラクトページで以下を確認  
   - `Contract Source Code Verified` が表示されていること  
   - コンパイル設定（Solidityバージョン、最適化有無）がローカルと一致していること  
4. ローカルでコンパイルしたバイトコード（`artifacts/contracts/CoreCats.sol/CoreCats.json` 内の `bytecode`）と、エクスプローラ上のバイトコードが一致することを確認  
5. コントラクトアドレスとデプロイ者アドレスが一致していることを確認  

---

## 3. 検証環境

- コントラクトソース: `contracts/CoreCats.sol`  
- コンパイル環境: Hardhat + Solidity (バージョンは `hardhat.config.js` / `hardhat.config.ts` に準拠)  
- アーティファクト: `artifacts/contracts/CoreCats.sol/CoreCats.json`  
- Hardhat: v3 系、Solidity: 0.8.28, Optimizer: enabled, runs=200（再現性確保のため）

---

## 4. 注意事項

- 上記手順は CoreCats コントラクトの信頼性と透明性を確保するために必要です  
- 検証完了後は、README に `Verified` 状態である旨を追記することを推奨します

---

## 5. 変更履歴（本ファイル）
- 追加: カノニカル（Sepolia）情報、`setSigner` Tx の明記、再現ビルドと bytecode 一致検証コマンド（本追記）
