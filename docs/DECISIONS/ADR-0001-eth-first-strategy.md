# ADR-0001: ETH-first Strategy for Core Cats

Date: 2026-03-05  
Status: Accepted

## Context
- Initial plan was direct Core Blockchain development using Foxer/ylem toolchain.
- Solidity compatibility gaps in ylem blocked practical ERC-721 development flow.
- Continuing only in that environment would stall core features (mint flow, tokenURI, on-chain SVG delivery, tests).

## Decision
- Use Ethereum testnet as the primary implementation track (`core-cats-eth`) to finish the target product behavior first.
- Keep Core-specific features (including KYC gating integration details) modular and migration-ready.
- After ETH flow is stable, migrate and validate on Core testnet, then move to Core mainnet.
- Core migration references must follow `core-coin` ecosystem sources only (see `CRITICAL_CHAIN_RULE.md`).

## Rationale
- Preserves delivery momentum.
- Separates product correctness from chain-specific tooling constraints.
- Creates a reusable, testable reference implementation before Core production deployment.

## Consequences
### Positive
- Faster iteration and clearer debugging surface.
- Better reproducibility for art pipeline and metadata logic.
- Reduced uncertainty for final deployment runbooks.

### Trade-offs
- Temporary dual-repo and migration overhead.
- Need explicit governance to keep ETH and Core behavior aligned.
- KYC gate must be abstracted to avoid lock-in to unknown/unstable integration paths.

## Follow-up Actions
- Maintain status and roadmap docs in this repository.
- Keep final manifest and validation artifacts up to date.
- Freeze provenance only after Core deployment readiness is confirmed.
