<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T45a Map and environment design

| | |
|---|---|
| Primary agent | **Leo** (A15, Level Design); spawn as `leo-level` |
| Supporting | A23 Nora, A16 Mara, A14 Camila, A28 Petra, A29 Lex |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T44a (Cora, A01), T47 (Nora, A23) |
| Blocks | T45b |
| Reviewer | Mara (A16), Lex (A29) |

## Deliverable

Blueprints (JSON plus diagrams) for the Hall, the back-room template and its Basement variant, the elevator and the infirmary, following section 7: dimensions, anchors, sightlines, lighting zones, camera positions

## Owns (edit only these)

- `roblox/assets/blueprints/`
- `docs/roblox/level/`
- `roblox/tools/lint/blueprints.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/leo-level.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Blueprint JSON validates; lint: anchor names per contract, unobstructed sightline from CameraAnchor to FlyPerch and MonitorScreen; `CHK`

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
