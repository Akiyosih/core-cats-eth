// scripts/setSigner_raw.ts  (ESM / ethers v6)
import { JsonRpcProvider, Wallet, Contract } from "ethers";
import fs from "fs";

const CORE_CATS = "0xB9b44398952D3F38CB66d9f5bD2bd03B0B809C1A";
const NEW_SIGNER = "0x0eAA7b9B3Bf05527A609Dc46e2707Ba39439A586";

async function main() {
  const abi = JSON.parse(fs.readFileSync(
    "artifacts/contracts/CoreCats.sol/CoreCats.json","utf8"
  )).abi;

  const provider = new JsonRpcProvider(process.env.SEPOLIA_RPC_URL!);
  const owner    = new Wallet(process.env.PRIVATE_KEY!, provider); // オーナー鍵

  const cc = new Contract(CORE_CATS, abi, owner);

  console.log("owner:", await cc.owner());
  const tx = await cc.setSigner(NEW_SIGNER);
  console.log("tx:", tx.hash);
  await tx.wait();
  console.log("done");
}

main().catch((e)=>{ console.error(e); process.exit(1); });
