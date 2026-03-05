import hre from "hardhat";

async function main() {
  const CoreCatsOnchainData = await hre.ethers.getContractFactory("CoreCatsOnchainData");
  const data = await CoreCatsOnchainData.deploy();
  await data.waitForDeployment();

  const CoreCatsMetadataRenderer = await hre.ethers.getContractFactory("CoreCatsMetadataRenderer");
  const renderer = await CoreCatsMetadataRenderer.deploy(await data.getAddress());
  await renderer.waitForDeployment();

  const CoreCats = await hre.ethers.getContractFactory("CoreCats");
  const coreCats = await CoreCats.deploy();
  await coreCats.waitForDeployment();

  await (await coreCats.setMetadataRenderer(await renderer.getAddress())).wait();

  console.log("CoreCatsOnchainData deployed to:", await data.getAddress());
  console.log("CoreCatsMetadataRenderer deployed to:", await renderer.getAddress());
  console.log("CoreCats deployed to:", await coreCats.getAddress());
}

main().catch((e) => { console.error(e); process.exitCode = 1; });
