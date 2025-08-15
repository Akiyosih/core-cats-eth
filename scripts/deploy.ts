import hre from "hardhat";

async function main() {
  const CoreCats = await hre.ethers.getContractFactory("CoreCats");
  const coreCats = await CoreCats.deploy();
  await coreCats.waitForDeployment();
  console.log("CoreCats deployed to:", await coreCats.getAddress());
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
