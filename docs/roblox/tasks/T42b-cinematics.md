<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T42b Cinematics

| | |
|---|---|
| Primary agent | **Camila** (A14, Cinematics); spawn as `camila-cinematics` |
| Supporting | A23 Nora, A24 Dalia, A15 Leo (camera anchors), A22 Mika, A19 Anika |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T42a (Theo, A13), T44a (Cora, A01), T47 (Nora, A23) |
| Blocks | T52a-2 |
| Reviewer | Nora (A23), Lex (A29) |

## Deliverable

Storyboards, timeline data and player: the Signing (first-join loan contract), Hall-to-back-room entry and return, dossier flip, Shark call, elevator, Basement drop, blackout and revival, fly KO, Freed credits

## Owns (edit only these)

- `roblox/src/client/Cinematics/`
- `roblox/src/shared/Content/Cinematics.luau`
- `docs/roblox/cinematics/`
- `roblox/tests/client/cinematics/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/camila-cinematics.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Timeline lint (durations, skippable after 1 s, cue ids valid, subtitles for every line, flash-safe); Lune timeline-player tests; Studio checklist; `CHK`

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
