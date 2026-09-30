<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T45d Fly models and rigs

| | |
|---|---|
| Primary agent | **Rigo** (A18, Fly Character / Rigging); spawn as `rigo-rigging` |
| Supporting | A19 Anika, A04 Felix (emote and tell ids), A23 Nora (designs), A28 Petra, A31 Ines (glove skins) |
| Where / size | C+ST / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T44a (Cora, A01), T47 (Nora, A23) |
| Blocks | T45e, T52b-2 |
| Reviewer | Anika (A19), Felix (A04) |

## Deliverable

Six fly rigs (Rookie, Panic, Cheetah, Pro, Cheater, Collector) with costumes, wings, glowing eyes and visible tell parts; the fly's floating forelegs; the player's floating gloves and glove skins; joints and attachments per contract; lint-clean

## Owns (edit only these)

- `roblox/tools/build/flies/`
- `roblox/assets/models/flies/`
- `roblox/tools/lint/rigs.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/rigo-rigging.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Rig lint (joints, hierarchy, symmetry, part budget, attachments, tell parts); reproducible build; `CHK`

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
