# Core Cats ETH - Project Status

Last updated: 2026-03-06

## Scope
- This repository is the implementation source of truth for the current build pipeline and deployment rehearsal.
- Goal: complete end-to-end full on-chain NFT flow on Ethereum testnet first, then migrate to Core testnet/mainnet.

## Current State
- `final_1000_manifest_v1` is generated and fixed as the current release candidate.
- Validation is passing (`final_1000_validation_v1.json`).
- Review-preview vs final-24x24 consistency audit is passing 1000/1000 (`final_1000_preview_consistency_v1.json`).
- Preview image is published in README (`docs/assets/core_cats_preview_grid.png`).
- Phase A-1 is implemented:
  - `CoreCats` now delegates `tokenURI` to a dedicated renderer (`metadataRenderer`).
  - `CoreCatsOnchainData` + `CoreCatsMetadataRenderer` now generate full on-chain SVG + attributes from `final_1000_manifest_v1`.
  - Metadata attribute parity check passed for 1000/1000.
  - Pixel-level check (renderer SVG -> 24x24 raster vs `art/final/final1000_v1/png24`) passed for 1000/1000.

## Fixed Artifacts
- `manifests/final_1000_manifest_v1.json`
- `manifests/final_1000_validation_v1.json`
- `manifests/final_1000_trait_summary_v1.json`
- `manifests/final_1000_preview_consistency_v1.json`

## Open Items
- KYC-gated mint integration path for Core production is not finalized.
- Branding/logo permission replies are pending.
- Provenance hash is not locked on-chain yet (intentional, to keep replaceability before final freeze).

## Next Milestones
1. Ethereum testnet release rehearsal:
   - deploy contract
   - verify contract
   - mint test flow
   - production-network tokenURI/full on-chain rendering checks
2. Add/expand contract tests around mint/signature/security matrix.
3. Core testnet rehearsal with equivalent behavior.
4. Mainnet go-live checklist and production deployment.

## Go/No-Go Gate for Final Freeze
- Smart contract behavior stable on ETH and Core testnets.
- Provenance calculation script fixed and reproducible.
- Final legal/branding approvals received.
- Final parameters frozen and signed off.
