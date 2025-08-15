// scripts/mint_with_ethers.ts
import "dotenv/config";
import { JsonRpcProvider, Wallet, Contract, solidityPackedKeccak256, getBytes } from "ethers";
// CoreCats ABI のパスは Hardhat の生成物（artifacts）を使用
import CoreCatsArtifact from "../artifacts/contracts/CoreCats.sol/CoreCats.json" assert { type: "json" };

async function main() {
  const addr = "0x97f310A189C48d7C918853A28CF921DB54190790"; // デプロイ済みCoreCats
  const rpc = process.env.SEPOLIA_RPC_URL!;
  const pk  = process.env.PRIVATE_KEY!; // 0x付き

  const provider = new JsonRpcProvider(rpc);
  const wallet   = new Wallet(pk, provider);
  const to       = await wallet.getAddress();

  const nonce  = BigInt(Date.now());
  const expiry = BigInt(Math.floor(Date.now() / 1000) + 3600);
  const { chainId } = await provider.getNetwork();

  const message = solidityPackedKeccak256(
    ["address","uint256","uint256","uint256","address"],
    [to, nonce, expiry, BigInt(chainId.toString()), addr]
  );
  const signature = await wallet.signMessage(getBytes(message));

  const cc = new Contract(addr, CoreCatsArtifact.abi, wallet);
  const tx = await cc.mint(to, nonce, expiry, signature);
  const receipt = await tx.wait();

  console.log("status:", receipt?.status);
  const total = await cc.totalSupply();
  console.log("totalSupply:", total.toString());
  if (total > 0n) {
    console.log("tokenURI(1):", await cc.tokenURI(1));
  }
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
