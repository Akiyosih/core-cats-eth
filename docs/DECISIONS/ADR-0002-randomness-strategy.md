# ADR-0002: Randomness Strategy for Mint Assignment (Core-first Release Path)

Date: 2026-03-05  
Status: Accepted

## Context
- Project target is Core Blockchain mainnet production.
- Ethereum Sepolia is used as rehearsal/reference, not as a final production chain.
- At this point, official Core production readiness for a native VRF path is not confirmed.
- We need a mint assignment process that is auditable by third parties and can ship without VRF dependency.

## Decision
- Adopt one baseline random assignment strategy for both Sepolia and Core:
  - `commit-reveal + future blockhash + non-repeating draw (lazy Fisher-Yates)`
- Keep randomness implementation behind a `RandomSource` abstraction.
- Do not make Chainlink VRF a required dependency for launch readiness.
- If official Core-native VRF readiness is confirmed later, migration is allowed only as an implementation swap under `RandomSource` without changing NFT semantics.

## Rationale
- Keeps rehearsal behavior aligned with Core production behavior.
- Avoids chain-specific drift between test and release.
- Enables launch even if VRF is unavailable at release time.
- Maintains transparent verification from on-chain events and published scripts.

## Consequences
### Positive
- Clear, chain-aligned release path.
- No hard dependency on external VRF service availability.
- Public can verify assignment process from immutable data.

### Trade-offs
- Commit-reveal is not equivalent to ideal VRF guarantees.
- More careful implementation/testing is required to avoid manipulation windows.
- Additional documentation/scripts are required for third-party verification.

## Guardrails
- Freeze randomness rules before production deployment.
- Emit enough events for full replay verification.
- Publish a verifier script and expected output format in repository docs.
- Keep mint quantity and per-wallet limits enforced independently of random source.

## Follow-up Actions
- Implement commit-reveal random source in contracts.
- Add tests for:
  - reveal timing constraints
  - non-repeating assignment
  - mint quantity handling (1/2/3)
  - reproducibility of assignment from chain data
- Add runbook section for random assignment audit.
