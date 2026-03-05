# Core Cats Work Procedure (Core Blockchain Mainnet Goal)

Last updated: 2026-03-05  
Version: v1.0 (post-correction)

## 0. Source Validation Policy (Mandatory)
1. Verify chain-level parameters with official ecosystem sources before editing deployment settings.
2. Do not copy assumptions from unrelated ecosystems.
3. When chain-level parameters are edited, record verified source URLs in docs or commit message.

## 1. Product Goals (Fixed)
1. Full on-chain NFT.
2. Mint price is free.
3. Secondary royalty is zero.
4. Public reproducibility of art and metadata pipeline.
5. Transparent Git history that third parties can audit.

## 2. Current Baseline (Already Completed)
1. Final 1,000-candidate set is fixed as release candidate.
2. Structural validation result exists and is passing.
3. Review-preview vs final-24x24 consistency audit is passing 1000/1000.
4. Status/roadmap/decision docs are published in this repository.

## 3. Phase A - Contract Completion on Ethereum Testnet
1. Replace placeholder `tokenURI` implementation with final metadata/SVG path tied to final manifest logic.
2. Keep signature-based mint gate as baseline policy.
3. Lock contract constants and access-control policy (`max supply`, `mint limit`, signer rotation policy).
4. Add complete tests for:
   - mint success/failure matrix
   - signature expiry/replay prevention
   - supply and per-address limits
   - `tokenURI` integrity and deterministic output
5. Produce deploy/verify/mint runbook and reproducible command set.

## 4. Phase B - UI Delivery (View First, Mint Next)
### B1. Viewer UI (start immediately)
1. Show 1,000-item gallery and detail pages.
2. Show traits (pattern, palette, collar, rarity tier/type).
3. Add filtering and search by trait/token id.
4. Data source: fixed manifest JSON (no chain dependency required).

### B2. Mint/Ownership UI (after contract interfaces stabilize)
1. Wallet connect and network guard.
2. Mint flow (signature retrieval + tx submission).
3. Owner lookup (`ownerOf`) and mint status display.
4. Display token metadata/SVG returned from on-chain `tokenURI`.

## 5. Phase C - Core Blockchain Porting Rehearsal
1. Create a dedicated migration branch for Core Blockchain toolchain adaptation.
2. Validate compiler/runtime compatibility against current contract features.
3. If incompatibility appears, define a compatibility layer without changing NFT semantics.
4. Keep all behavior differences documented (cause, mitigation, test impact).

## 6. Phase D - Core Blockchain Testnet Rehearsal
1. Deploy contract with Core Blockchain-compatible settings.
2. Verify contract on the target explorer in the Core ecosystem.
3. Execute mint flow and UI checks on testnet.
4. Confirm metadata and rendered SVG behavior against manifest expectations.

## 7. Phase E - Mainnet Readiness and Freeze
1. Finalize provenance computation procedure and verify reproducibility.
2. Finalize legal/branding status and document approvals.
3. Freeze immutable parameters and signer/owner operational policy.
4. Prepare launch checklist (rollback boundaries, incident response, communication plan).

## 8. Phase F - Core Blockchain Mainnet Deployment
1. Deploy and verify contract.
2. Validate first mint path and metadata retrieval.
3. Publish final addresses, verification links, and reproducibility artifacts.
4. Mark deployment commit/tag as release baseline.

## 9. Irreversible Boundary Rule
1. The irreversible boundary is provenance lock + production deployment.
2. Any asset/metadata replacement must happen before this boundary.
3. Boundary decision must be explicitly recorded in docs and commit history.

## 10. Definition of Done
1. Anyone can reproduce manifest/validation outputs from repository scripts.
2. Anyone can verify deployed bytecode and contract source linkage.
3. Viewer UI, mint UI, and chain data are consistent.
4. No hidden mutable parameters remain after final freeze.
