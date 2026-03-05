import fs from "node:fs";
import path from "node:path";
import { Buffer } from "node:buffer";
import { BrowserProvider, ContractFactory } from "ethers";
import hre from "hardhat";

function decodeDataUriBase64(uri) {
  const idx = uri.indexOf(",");
  if (idx < 0) throw new Error("invalid data uri");
  return Buffer.from(uri.slice(idx + 1), "base64").toString("utf8");
}

function ensureAttrEqual(actual, expected, tokenId) {
  if (actual.length !== expected.length) {
    throw new Error(`token ${tokenId}: attributes length mismatch ${actual.length} != ${expected.length}`);
  }
  for (let i = 0; i < expected.length; i++) {
    const a = actual[i];
    const e = expected[i];
    if (!a || a.trait_type !== e.trait_type || a.value !== e.value) {
      throw new Error(
        `token ${tokenId}: attr[${i}] mismatch actual=${JSON.stringify(a)} expected=${JSON.stringify(e)}`,
      );
    }
  }
}

function loadArtifact(root, rel) {
  return JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"));
}

async function main() {
  const root = process.cwd();
  const manifestPath = path.join(root, "manifests", "final_1000_manifest_v1.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const items = [...manifest.items].sort((a, b) => a.token_id - b.token_id);

  if (items.length !== 1000) {
    throw new Error(`expected 1000 items, got ${items.length}`);
  }

  const conn = await hre.network.connect();
  const provider = new BrowserProvider(conn.provider);
  const signer = await provider.getSigner();

  const dataArtifact = loadArtifact(root, "artifacts/contracts/CoreCatsOnchainData.sol/CoreCatsOnchainData.json");
  const rendererArtifact = loadArtifact(root, "artifacts/contracts/CoreCatsMetadataRenderer.sol/CoreCatsMetadataRenderer.json");

  const dataFactory = new ContractFactory(dataArtifact.abi, dataArtifact.bytecode, signer);
  const data = await dataFactory.deploy();
  await data.waitForDeployment();

  const rendererFactory = new ContractFactory(rendererArtifact.abi, rendererArtifact.bytecode, signer);
  const renderer = await rendererFactory.deploy(await data.getAddress());
  await renderer.waitForDeployment();

  const started = Date.now();
  for (let i = 0; i < items.length; i++) {
    const tokenId = i + 1;
    const expected = items[i];
    if (expected.token_id !== tokenId) {
      throw new Error(`manifest token order mismatch at index ${i}: token_id=${expected.token_id}`);
    }

    const uri = await renderer.tokenURI(tokenId);
    const jsonText = decodeDataUriBase64(uri);
    const obj = JSON.parse(jsonText);

    const expectedName = `CoreCats #${tokenId}`;
    if (obj.name !== expectedName) {
      throw new Error(`token ${tokenId}: name mismatch ${obj.name} != ${expectedName}`);
    }

    if (typeof obj.image !== "string" || !obj.image.startsWith("data:image/svg+xml;base64,")) {
      throw new Error(`token ${tokenId}: image is not svg data uri`);
    }

    ensureAttrEqual(obj.attributes, expected.attributes, tokenId);

    if (tokenId % 100 === 0) {
      const sec = ((Date.now() - started) / 1000).toFixed(1);
      console.log(`[verify-renderer] checked ${tokenId}/1000 (${sec}s)`);
    }
  }

  console.log("[verify-renderer] PASS: all 1000 token metadata attributes match final_1000_manifest_v1.json");
  console.log(`[verify-renderer] data=${await data.getAddress()}`);
  console.log(`[verify-renderer] renderer=${await renderer.getAddress()}`);

  await conn.close();
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
