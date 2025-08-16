const go = async () => {
  const H = await import("hardhat");
  console.log("module keys:", Object.keys(H).sort());      // ← ここに 'ethers','viem' が来る
  console.log("has ethers (module):", !!(H as any).ethers);
  console.log("has viem   (module):", !!(H as any).viem);

  const hre = (H as any).default;
  console.log("hre keys:", Object.keys(hre).sort());       // ← hre はタスク/ネットワーク等が載る
};
go();
