<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T62 Cosmetic store and inventory

| | |
|---|---|
| Primary agent | **Ines** (A31, Progression & Store); spawn as `ines-progression` |
| Supporting | A10 Sasha (receipts), A12 Uma (screens), A17 Otto, A18 Rigo and A16 Mara (skin variants), A29 Lex (pricing policy), A30 Omar (catalog telemetry) |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W5 |
| Depends on | T01 (Cora, A01), T31 (Elena, A03), T60 (Ines, A31) |
| Blocks | T51, T52a-2 |
| Reviewer | Sasha (A10), Lex (A29) |

## Deliverable

Catalog (racket, glove, felt and title-plate skins) at fixed Buzz or Robux prices; Buzz purchases; Robux developer products via idempotent `ProcessReceipt`; inventory, equip and ownership checks; equipped cosmetics sent to back rooms and watchers

## Owns (edit only these)

- `roblox/src/shared/Content/Catalog.luau`
- `roblox/src/server/Services/StoreService.luau`
- `roblox/tests/store/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 3, 6, 7b.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/ines-progression.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Duplicate receipt ids grant once; a failed save returns NotProcessedYet; Buzz purchase is atomic; equip requires ownership; catalog lint (price, category, asset ids for every item, no chance-based item); `CHK`

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
