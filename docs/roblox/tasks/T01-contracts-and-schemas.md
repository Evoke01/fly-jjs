<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T01 Contracts and schemas

| | |
|---|---|
| Primary agent | **Cora** (A01, Contracts & Architecture); spawn as `cora-contracts` |
| Supporting | A02 Remy, A03 Elena, A04 Felix, A06 Bea, A09 Mateo (each reviews the types they consume) |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W1 |
| Depends on | T00 (Cora, A01) |
| Blocks | T10, T11, T12, T20, T23, T24, T30a, T30b, T30c, T31, T40, T41, T42a, T43, T44a, T48, T49, T60, T62 |
| Reviewer | Remy (A02), Mateo (A09) |

## Deliverable

Frozen types for 2-4 seats (Ruleset, Seat, Action, DuelEvent, View, Ledger, FlyPack, PlayerData v1 with the meta fields, Platform, the 7 remotes incl. MetaIntent and Meta), cue/caption/dialogue/string/notice/title/quest-event key catalogs, JSON schemas with fixtures, tag `contracts-v1`

## Owns (edit only these)

- `roblox/src/shared/Types.luau`
- `roblox/src/shared/Net/Protocol.luau`
- `docs/roblox/CONTRACTS.md`
- `docs/roblox/schemas/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 2, 3, 6, 7b.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/cora-contracts.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Types compile (Selene, luau-lsp where available); JSON schemas validate their fixtures (`python -m jsonschema`); consumer sign-offs recorded in `docs/roblox/ccr/contracts-v1-signoff.md`; tag `contracts-v1`

`CHK` = `bash roblox/scripts/check.sh` (StyLua check, Selene, `lune run tests/run`, every lint in `roblox/tools/lint/`, `rojo build`). `PYT f` = `python -m pytest tests/f`.

The reviewer signs off in the PR; the Lead merges only with this output pasted.

## Rules

- Edit only the paths you own. Anything else goes through a change request in `docs/roblox/ccr/CCR-<n>.md`; the Lead rules on it and the owner applies it.
- Contracts (`CONTRACTS.md`, `Types.luau`, `Net/Protocol.luau`, `docs/roblox/schemas/`) are frozen once `contracts-v1` is tagged.
- `--!strict` Luau. No Roblox APIs in `roblox/src/shared/`; only `Main.*.luau` and `roblox/src/server/Platform/` call `game:GetService`.
- Run `bash roblox/scripts/check.sh` (and `python -m pytest` for Python work) before pushing, and paste the output in the PR.
- One branch and one PR per work item: `claude/fr-<ID>-<slug>` into the integration branch `fly-roulette`.
- No secrets and no connectome data in git. No names, art or audio from Buckshot Roulette or from the reference Roblox game.
- Nothing outside a duel may change the debt, lives, items or odds (DESIGN.md sections 3 and 7b).

## Handoff report (PR description)

1. Work item and agent.
2. Files changed (all inside your owned paths).
3. Each handoff check above as `command -> result`.
4. Open risks and follow-ups.
5. Who consumes this next (see "Blocks").
