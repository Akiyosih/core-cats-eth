# Critical Chain Rule (Do Not Mix Networks)

## Absolute Rule
- For this project, **Core Blockchain** refers to the `core-coin` ecosystem.
- **Core Blockchain and CoreDAO are different ecosystems.**
- Any design, implementation, or deployment decision must avoid mixing these two.

## Allowed Reference Family for Core Migration
- https://coreblockchain.net/
- https://foxar.dev/intro/
- https://github.com/core-coin
- https://github.com/core-coin/ylem
- https://github.com/bchainhub
- (When available) official Core Blockchain/CIP documents linked from the ecosystem above

## Explicitly Disallowed as Core-Chain Reference
- CoreDAO documentation/network assumptions (example: `docs.coredao.org` references)

## Operational Safety Rule
- If chain assumptions are unclear, stop and verify before proceeding.
- Do not infer chain IDs, explorers, or deployment settings from unrelated ecosystems.
- Record verified source URLs in commit messages or docs when chain-level settings are changed.
