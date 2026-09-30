<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T32 Debt and Lobby services

| | |
|---|---|
| Primary agent | **Elena** (A03, Economy & Persistence); spawn as `elena-economy` |
| Supporting | A09 Mateo (Ledger and Notice events), A24 Dalia (Shark call ids), A30 Omar |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T11 (Elena, A03), T31 (Elena, A03) |
| Blocks | T51 |
| Reviewer | Soren (A05), Mateo (A09) |

## Deliverable

Settle -> persist -> events, drip with pause rules, away roll, floor and zone transitions; leaderboards and the Hall wall-board feed (Shark's Board, Hall of Freedom, live rooms)

## Owns (edit only these)

- `roblox/src/server/Services/DebtService.luau`
- `roblox/src/server/Services/LobbyService.luau`
- `roblox/tests/integration/debt/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 3, 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/elena-economy.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Integration: settle -> persist -> events; drip pauses in duel, menu and cutscene; away roll only after 12 h and at most once per 24 h; transitions; leaderboard write; `CHK`

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
