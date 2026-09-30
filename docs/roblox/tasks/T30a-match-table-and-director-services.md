<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T30a Match, Table and Director services

| | |
|---|---|
| Primary agent | **Mateo** (A09, Roblox Backend); spawn as `mateo-backend` |
| Supporting | A04 Felix, A02 Remy, A26 Toby (forced-chamber hook), A10 Sasha, A12 Uma (wall-board data), A28 Petra (room pool) |
| Where / size | C / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T01 (Cora, A01), T10 (Remy, A02), T12 (Felix, A04), T30b (Mateo, A09), T30c (Mateo, A09) |
| Blocks | T33a, T33b, T46, T51, T61 |
| Reviewer | Felix (A04), Sasha (A10) |

## Deliverable

Server-authoritative duel runner (60 s turn timer, forfeit, watchers, event log); back-room pool (copy the template per duel, seat the player, return to the Hall); Hall table seating and Quickplay; public room stats for the Hall wall boards; fly draw

## Owns (edit only these)

- `roblox/src/server/Services/MatchService.luau`
- `roblox/src/server/Services/TableService.luau`
- `roblox/src/server/Services/DirectorService.luau`
- `roblox/tests/integration/match/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/mateo-backend.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Lune integration: full duel vs the fallback pack, timeout, forfeit, disconnect, a watcher sees only public events, seed determinism; back-room pool never hands one room to two duels and returns rooms after every exit path; Quickplay seats into a free room; grep gate; `CHK`

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
