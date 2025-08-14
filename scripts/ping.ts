import hre from "hardhat";

async function main() {
  // Hardhat v3: 接続済み HRE を取得してから ethers/viem を使う
  const { ethers, viem } = (await hre.network.connect()) as any;

  const n = await ethers.provider.getBlockNumber();
  console.log("Sepolia block:", n);

  // 参考: viem でも確認（任意）
  if (viem?.getPublicClient) {
    const client = await viem.getPublicClient();
    console.log("Viem block:", await client.getBlockNumber());
  }
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
