# 🐱 Core Cats - Fully On-chain NFT Project (Ethereum Testnet)

## English

### Overview
Core Cats is a **fully on-chain NFT collection** originally designed for Core Blockchain and now being implemented on the **Ethereum Testnet** for development and testing.  
It features **24×24 pixel generative cats**, inspired by CryptoPunks, each with unique patterns, eye colors, and poses.  
All NFTs are **fully generated and stored on-chain**—no off-chain metadata.

- **Total Supply:** 1,000 unique cats (testnet version for now)
- **Mint Type:** Free Mint
- **License:** MIT
- **Blockchain:** Ethereum Testnet (Goerli/Sepolia planned)

---

### Objectives
- Complete functional deployment on Ethereum Testnet before mainnet migration.
- Maintain **fully open and transparent** development.
- Ensure **full on-chain storage** of SVG images and metadata.
- Use lessons from testnet deployment to prepare for Ethereum Mainnet and future Core Blockchain deployment.
- Preserve CryptoPunks-inspired design with original cat personalities.

---

### Roadmap
1. **Local Development Setup**
   - Initialize Hardhat project
   - Configure `.gitignore` to protect sensitive files
   - Prepare test accounts with faucet ETH

2. **Smart Contract Development**
   - Implement minimal ERC-721-compatible contract
   - Store SVG image data fully on-chain
   - Add random trait generation logic

3. **Testnet Deployment**
   - Deploy to Ethereum Testnet (Goerli/Sepolia)
   - Run minting and metadata retrieval tests
   - Verify contract on Etherscan

4. **Mainnet & Core Blockchain Migration**
   - Deploy to Ethereum Mainnet
   - Adapt code for Core Blockchain deployment
   - Verify and publish both versions

5. **Launch & Community**
   - Open minting for the public (mainnet stage)
   - Community showcase and documentation release

---

### Tech Stack
- **Smart Contracts:** Solidity (ERC-721)
- **Dev Tools:** Hardhat, OpenZeppelin, Ethers.js
- **Frontend:** Static site (GitHub Pages / Vercel)
- **Node:** Ethereum Testnet RPC providers

---

### License
MIT License - Free to use, modify, and distribute.

---

## 日本語

### 概要
Core Catsは、もともとCore Blockchain向けに設計された**フルオンチェーンNFTコレクション**で、現在は**Ethereumテストネット**上で開発・検証を行っています。  
**24×24ピクセルのジェネラティブ猫アート**を特徴とし、模様・目の色・ポーズがすべてランダム生成されます。  
すべてのNFTが**完全にオンチェーンに保存**され、オフチェーンのメタデータは一切使用しません。

- **発行総数:** 1,000匹（現状はテストネット版）
- **ミント形式:** フリーミント
- **ライセンス:** MIT
- **ブロックチェーン:** Ethereumテストネット（Goerli / Sepolia予定）

---

### 目的
- Ethereumテストネットでの完全動作を達成し、メインネット移行に備える。
- **オープンで透明な**開発を継続。
- SVG画像とメタデータを**完全オンチェーン**で保存。
- テストネットで得た知見をEthereumメインネットと将来のCore Blockchainデプロイに活用。
- クリプトパンクスを参考にしつつ、独自の猫キャラクターを創造。

---

### ロードマップ
1. **ローカル開発環境構築**
   - Hardhatプロジェクト初期化
   - `.gitignore`で秘匿情報を保護
   - テストアカウントにFaucet ETHを取得

2. **スマートコントラクト開発**
   - 最小限のERC-721互換コントラクト実装
   - SVG画像を完全オンチェーン化
   - ランダム属性生成ロジック構築

3. **テストネットデプロイ**
   - Ethereumテストネット（Goerli / Sepolia）にデプロイ
   - ミントやメタデータ取得のテスト
   - Etherscanでコントラクト検証

4. **メインネット & Core Blockchain移行**
   - Ethereumメインネットにデプロイ
   - Core Blockchain対応コードに適応
   - 両方のバージョンを検証・公開

5. **ローンチ & コミュニティ**
   - メインネットで一般ユーザー向けにミント開放
   - コミュニティ展示とドキュメント公開

---

### 技術スタック
- **スマートコントラクト:** Solidity (ERC-721)
- **開発ツール:** Hardhat, OpenZeppelin, Ethers.js
- **フロントエンド:** 静的サイト（GitHub Pages / Vercel）
- **ノード:** EthereumテストネットRPCプロバイダ

---

### ライセンス
MITライセンス - 自由に利用・改変可能
