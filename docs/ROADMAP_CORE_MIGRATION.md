# Core Cats - ETH to Core Blockchain Migration Roadmap

Last updated: 2026-03-05

## Objective
Build and validate the full on-chain NFT release flow in stages:
1. Ethereum testnet (reference implementation and rapid iteration)
2. Core Blockchain testnet rehearsal (toolchain/runtime migration)
3. Core Blockchain mainnet production release

## Stage 1: Ethereum Testnet (Reference Completion)
### Deliverables
- Production-shape ERC-721 behavior
- Full on-chain SVG + metadata (`tokenURI`) verification
- Mint flow rehearsal (signature gate + commit-reveal random assignment baseline)
- Read-only UI + mint UI rehearsal

### Exit Criteria
- Deploy/verify/mint runbook is complete and repeatable
- Contract tests and runtime checks pass
- Final 1,000-art manifest pipeline is reproducible
- Random assignment is fully verifiable from on-chain data and published scripts

## Stage 2: Core Blockchain Testnet Rehearsal
### Deliverables
- Compile/deploy path validated with Core Blockchain toolchain constraints
- Runtime behavior parity vs ETH reference
- Explorer verification and operation runbook for Core environment
- Same random assignment model as Stage 1 (no algorithm drift between rehearsal and production)

### Exit Criteria
- Deploy/verify/mint succeeds on Core Blockchain testnet
- Metadata rendering and trait outputs match manifest expectations
- Operational checklist (keys, signer rotation, incident handling) validated
- Random assignment verification results match ETH-stage behavior model

## Stage 3: Core Blockchain Mainnet Production
### Deliverables
- Final contract deployment package
- Provenance and immutable parameters fixed
- Production monitoring and incident-response checklist ready

### Exit Criteria
- Final legal/branding approvals complete
- Final freeze decision recorded
- Mainnet deployment and verification completed

## Cross-cutting Policy
- Keep KYC gate logic modular so final integration path can be swapped without changing NFT core logic.
- Keep `core-cats-eth` as implementation source of truth until Core Blockchain production deployment is complete.
- Treat provenance lock as the irreversible boundary.
- Record source URLs for every Core-chain setting change.
- Keep one random architecture across Sepolia/Core (`commit-reveal + future blockhash + lazy Fisher-Yates`) unless official Core-native VRF readiness is confirmed.
- Keep randomness module abstracted (`RandomSource`) so VRF can be introduced later without changing metadata/trait semantics.
