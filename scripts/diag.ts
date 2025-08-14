import hre from "hardhat";

async function main() {
  const { ethers, viem } = (await hre.network.connect()) as any;
  console.log("ethers in hre:", typeof ethers !== "undefined");
  if (ethers?.provider) {
    console.log("ethers block:", await ethers.provider.getBlockNumber());
  } else {
    console.log("ethers.provider is undefined");
  }
  if (viem?.getPublicClient) {
    const client = await viem.getPublicClient();
    console.log("viem block:", await client.getBlockNumber());
  } else {
    console.log("viem.getPublicClient is undefined");
  }
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
