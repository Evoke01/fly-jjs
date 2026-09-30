<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T60 Progression core

| | |
|---|---|
| Primary agent | **Ines** (A31, Progression & Store); spawn as `ines-progression` |
| Supporting | A03 Elena (profile fields), A10 Sasha (grant validation), A12 Uma (HUD), A23 Nora and A25 Tessa (title names), A30 Omar (rewards telemetry) |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T01 (Cora, A01), T31 (Elena, A03) |
| Blocks | T51, T61, T62 |
| Reviewer | Elena (A03), Sasha (A10) |

## Deliverable

XP curve and level rewards, title registry with unlock rules (incl. RAGE QUITTER for 10 minutes), rank badge view-model (floor + debt repaid), Buzz wallet with an idempotent transaction log, `Meta` updates to the client

## Owns (edit only these)

- `roblox/src/shared/Progression/`
- `roblox/src/shared/Config/Progression.luau`
- `roblox/src/server/Services/ProgressionService.luau`
- `roblox/tests/progression/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 3, 6, 7b.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/ines-progression.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Unit tests: XP curve increasing, level rewards granted once, title unlocks from event fixtures, RAGE QUITTER applied on a mid-duel leave and gone after 10 minutes, Buzz log idempotent under duplicate grant ids, rank badge matches the ledger; `CHK`

`CHK` = `bash roblox/scripts/check.sh` (StyLua check, Selene, `lune run tests/run`, every lint in `roblox/tools/lint/`, `rojo build`). `PYT f` = `python -m pytest tests/f`.

The reviewer signs off in the PR; the Lead merges only with this output pasted.

## Rules

- Edit only the paths you own. Anything else goes through a change request in `docs/roblox/ccr/CCR-<n>.md`; the Lead rules on it and the owner applies it.
- Contracts (`CONTRACTS.md`, `Types.luau`, `Net/Protocol.luau`, `docs/roblox/schemas/`) are frozen once `contracts-v1` is tagged.
- `--!strict` Luau. No Roblox APIs in `roblox/src/shared/`; only `Main.*.luau` and `roblox/src/server/Platform/` call `game:GetService`.
- Run `bash roblox/scripts/check.sh` (and `python -m pytest` for Python work) before pushing, and paste the output in the PR.
- One branch and one PR per work item: `claude/fr-<ID>-<slug>` into the integration branch.
- No secrets and no connectome data in git. No names, art or audio from Buckshot Roulette or from the reference Roblox game.
- Nothing outside a duel may change the debt, lives, items or odds (DESIGN.md sections 3 and 7b).

## Handoff report (PR description)

1. Work item and agent.
2. Files changed (all inside your owned paths).
3. Each handoff check above as `command -> result`.
4. Open risks and follow-ups.
5. Who consumes this next (see "Blocks").
