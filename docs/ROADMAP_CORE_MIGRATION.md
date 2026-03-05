# Core Cats - ETH to Core Migration Roadmap

Last updated: 2026-03-05

## Objective
Build and validate the full on-chain NFT release flow in stages:
1. Ethereum testnet (reference implementation)
2. Core testnet (migration rehearsal)
3. Core mainnet (production release)

## Stage 1: Ethereum Testnet (Reference Completion)
### Deliverables
- Production-shape ERC-721 contract behavior
- Full on-chain SVG + metadata (`tokenURI`) verification
- Mint flow rehearsal including gated mint path (signature-based)

### Exit Criteria
- Deploy/verify/mint runbook is complete and repeatable
- Contract tests and runtime checks pass
- Final 1,000-art manifest pipeline is reproducible

## Stage 2: Core Testnet (Migration Rehearsal)
### Deliverables
- Same functional behavior as ETH rehearsal
- Core-compatible compile/deploy settings validated
- Operational runbook for Core deployment/verification

### Exit Criteria
- Deploy/verify/mint succeeds on Core testnet
- Metadata rendering and trait outputs match manifest expectations
- Gas and runtime constraints are within acceptable range

## Stage 3: Core Mainnet (Production)
### Deliverables
- Final contract deployment package
- Provenance and immutable parameters fixed
- Operational and incident-response checklist ready

### Exit Criteria
- Final approval for legal/branding and launch policy
- Final freeze decision recorded
- Mainnet deployment and verification completed

## Cross-cutting Policy
- Keep KYC gate logic modular (default: signature gate) so CorePass integration can be swapped without breaking NFT core logic.
- Keep `core-cats-eth` as implementation source of truth until Core production deployment is complete.
- Treat provenance lock as the irreversible boundary.
