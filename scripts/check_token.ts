// scripts/check_token.ts
import "dotenv/config";
import { JsonRpcProvider, Wallet, Contract } from "ethers";
import fs from "node:fs";
import CoreCatsArtifact from "../artifacts/contracts/CoreCats.sol/CoreCats.json" assert { type: "json" };

async function main() {
  const addr = "0x97f310A189C48d7C918853A28CF921DB54190790";
  const provider = new JsonRpcProvider(process.env.SEPOLIA_RPC_URL!);
  const wallet   = new Wallet(process.env.PRIVATE_KEY!, provider);
  const cc = new Contract(addr, CoreCatsArtifact.abi, wallet);

  const owner = await cc.ownerOf(1);
  console.log("ownerOf(1):", owner);

  const uri = await cc.tokenURI(1);
  console.log("tokenURI(1):", uri.slice(0, 80) + "...");

  const metaJson = Buffer.from(uri.split(",")[1], "base64").toString();
  console.log("metadata:", metaJson);

  const image = JSON.parse(metaJson).image as string;
  const svg   = Buffer.from(image.split(",")[1], "base64").toString();
  fs.writeFileSync("corecat-1.svg", svg);
  console.log("wrote corecat-1.svg");
}
main().catch(e => (console.error(e), process.exitCode = 1));
