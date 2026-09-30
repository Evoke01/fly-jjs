<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T45b Studio environment build

| | |
|---|---|
| Primary agent | **Mara** (A16, Environment / Map Builder); spawn as `mara-environment` |
| Supporting | A15 Leo, A17 Otto, A20 Zara (lights), A21 Wren (emitters), A28 Petra, A31 Ines (felt skins) |
| Where / size | C+ST / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T45a (Leo, A15), T44b (Mara, A16) |
| Blocks | T52b-2 |
| Reviewer | Leo (A15), Petra (A28) |

## Deliverable

Final Hall and back-room models built from the blueprints, with felt-colour variants for the store, lint-clean, plus the Studio import checklist

## Owns (edit only these)

- `roblox/tools/build/env/`
- `roblox/assets/models/env/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/mara-environment.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Env lint (counts within budgets, anchors, PrimaryParts, collision groups); rebuild is byte-reproducible; Studio import checklist; `CHK`

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
