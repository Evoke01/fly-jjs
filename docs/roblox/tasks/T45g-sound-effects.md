<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T45g Sound effects

| | |
|---|---|
| Primary agent | **Wren** (A21, Sound Design); spawn as `wren-sound` |
| Supporting | A13 Theo, A28 Petra, A29 Lex (originality, captions) |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T44a (Cora, A01), T47 (Nora, A23) |
| Blocks | T52a-2, T52b-2 |
| Reviewer | Lex (A29), Theo (A13) |

## Deliverable

Synthesized original SFX (OGG): buzz loops per fly, zap, fizzle, cell clicks, light hum, typewriter ticks for captions, item sounds, UI, phone, elevator, heartbeat; cue map module; upload manifest; audio lint

## Owns (edit only these)

- `roblox/tools/audio/sfx/`
- `roblox/assets/audio/sfx/`
- `roblox/src/client/Audio/Sfx/`
- `roblox/tests/audio/sfx/`
- `roblox/tools/lint/audio.py`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/wren-sound.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

`python roblox/tools/lint/audio.py`: peak at or below -1 dBFS, no clipping, loop seams, loudness window, size budget, at least one file per cue; deterministic build; `CHK`

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
