import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const CoreCatsModule = buildModule("CoreCatsModule", (m) => {
  const coreCats = m.contract("CoreCats");
  return { coreCats };
});

export default CoreCatsModule;
