import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { Buffer } from "node:buffer";
import { BrowserProvider, ContractFactory } from "ethers";
import hre from "hardhat";

function decodeDataUriBase64(uri) {
  const idx = uri.indexOf(",");
  if (idx < 0) throw new Error("invalid data uri");
  return Buffer.from(uri.slice(idx + 1), "base64").toString("utf8");
}

function parsePngRGBA24(filePath) {
  const b = fs.readFileSync(filePath);
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (!b.subarray(0, 8).equals(sig)) throw new Error(`bad png signature: ${filePath}`);

  let i = 8;
  let width = 0;
  let height = 0;
  const idat = [];

  while (i < b.length) {
    const length = b.readUInt32BE(i); i += 4;
    const ctype = b.toString("ascii", i, i + 4); i += 4;
    const data = b.subarray(i, i + length); i += length;
    i += 4; // crc

    if (ctype === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      const bitDepth = data[8];
      const colorType = data[9];
      const comp = data[10];
      const filt = data[11];
      const interlace = data[12];
      if (width !== 24 || height !== 24 || bitDepth !== 8 || colorType !== 6 || comp !== 0 || filt !== 0 || interlace !== 0) {
        throw new Error(`unsupported png format: ${filePath}`);
      }
    } else if (ctype === "IDAT") {
      idat.push(data);
    } else if (ctype === "IEND") {
      break;
    }
  }

  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = width * 4;
  const out = Buffer.alloc(width * height * 4);
  let ptr = 0;
  let prev = Buffer.alloc(stride);

  const paeth = (a, b2, c) => {
    const p = a + b2 - c;
    const pa = Math.abs(p - a);
    const pb = Math.abs(p - b2);
    const pc = Math.abs(p - c);
    if (pa <= pb && pa <= pc) return a;
    if (pb <= pc) return b2;
    return c;
  };

  for (let y = 0; y < height; y++) {
    const filter = raw[ptr++];
    const row = Buffer.from(raw.subarray(ptr, ptr + stride));
    ptr += stride;

    if (filter === 0) {
      // none
    } else if (filter === 1) {
      for (let x = 0; x < stride; x++) {
        const left = x >= 4 ? row[x - 4] : 0;
        row[x] = (row[x] + left) & 0xff;
      }
    } else if (filter === 2) {
      for (let x = 0; x < stride; x++) {
        row[x] = (row[x] + prev[x]) & 0xff;
      }
    } else if (filter === 3) {
      for (let x = 0; x < stride; x++) {
        const left = x >= 4 ? row[x - 4] : 0;
        const up = prev[x];
        row[x] = (row[x] + ((left + up) >> 1)) & 0xff;
      }
    } else if (filter === 4) {
      for (let x = 0; x < stride; x++) {
        const left = x >= 4 ? row[x - 4] : 0;
        const up = prev[x];
        const upLeft = x >= 4 ? prev[x - 4] : 0;
        row[x] = (row[x] + paeth(left, up, upLeft)) & 0xff;
      }
    } else {
      throw new Error(`unsupported png filter=${filter}: ${filePath}`);
    }

    row.copy(out, y * stride);
    prev = row;
  }

  return out;
}

function hexToRgb(hex) {
  const s = hex.startsWith("#") ? hex.slice(1) : hex;
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
}

function renderSvgRects(svg) {
  const pixels = Buffer.alloc(24 * 24 * 4); // transparent init
  const re = /<rect x="(\d+)" y="(\d+)" width="(\d+)" height="1" fill="(#?[0-9a-fA-F]{6})"\/>/g;
  let m;
  while ((m = re.exec(svg)) !== null) {
    const x = Number(m[1]);
    const y = Number(m[2]);
    const w = Number(m[3]);
    const [r, g, b] = hexToRgb(m[4]);
    for (let dx = 0; dx < w; dx++) {
      const xx = x + dx;
      if (xx < 0 || xx >= 24 || y < 0 || y >= 24) continue;
      const off = (y * 24 + xx) * 4;
      pixels[off] = r;
      pixels[off + 1] = g;
      pixels[off + 2] = b;
      pixels[off + 3] = 255;
    }
  }
  return pixels;
}

function loadArtifact(root, rel) {
  return JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"));
}

async function main() {
  const root = process.cwd();
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifests", "final_1000_manifest_v1.json"), "utf8"));
  const items = [...manifest.items].sort((a, b) => a.token_id - b.token_id);

  const expectedPng = new Map();
  for (const it of items) {
    expectedPng.set(it.token_id, parsePngRGBA24(path.join(root, it.final_png_24)));
  }

  const conn = await hre.network.connect();
  const provider = new BrowserProvider(conn.provider);
  const signer = await provider.getSigner();

  const dataArtifact = loadArtifact(root, "artifacts/contracts/CoreCatsOnchainData.sol/CoreCatsOnchainData.json");
  const rendererArtifact = loadArtifact(root, "artifacts/contracts/CoreCatsMetadataRenderer.sol/CoreCatsMetadataRenderer.json");

  const data = await new ContractFactory(dataArtifact.abi, dataArtifact.bytecode, signer).deploy();
  await data.waitForDeployment();
  const renderer = await new ContractFactory(rendererArtifact.abi, rendererArtifact.bytecode, signer).deploy(await data.getAddress());
  await renderer.waitForDeployment();

  const started = Date.now();
  for (let tokenId = 1; tokenId <= 1000; tokenId++) {
    const uri = await renderer.tokenURI(tokenId);
    const jsonObj = JSON.parse(decodeDataUriBase64(uri));
    const svg = decodeDataUriBase64(jsonObj.image);
    const actual = renderSvgRects(svg);
    const expected = expectedPng.get(tokenId);

    if (!expected || !actual.equals(expected)) {
      throw new Error(`pixel mismatch at token ${tokenId}`);
    }

    if (tokenId % 100 === 0) {
      const sec = ((Date.now() - started) / 1000).toFixed(1);
      console.log(`[verify-pixels] checked ${tokenId}/1000 (${sec}s)`);
    }
  }

  console.log("[verify-pixels] PASS: 1000/1000 rendered SVG pixels match final png24 outputs");
  await conn.close();
}

main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
