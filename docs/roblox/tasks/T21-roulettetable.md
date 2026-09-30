<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T21 RouletteTable

| | |
|---|---|
| Primary agent | **Bea** (A06, Connectome & Brain Training); spawn as `bea-brain` |
| Supporting | A08 Vera (activity hooks), A07 Pax (readout access), A05 Soren (metrics) |
| Where / size | C / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T20 (Bea, A06) |
| Blocks | T22a, T23, T24 |
| Reviewer | Soren (A05) |

## Deliverable

`RouletteTable(Table)` in the casino's game pattern (section 5): the table picture, a `roulette` Mind on the shared `CasinoFly` (opponent/self values), fear and dopamine through `Table`, no wallet or bets, save/load in the casino memory, FakeBrain tests

## Owns (edit only these)

- `fly_jjs/core/roulette.py`
- `tests/test_roulette_fly.py`

## Read first

- [DESIGN.md](../DESIGN.md), sections 4, 5.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/bea-brain.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

`PYT test_roulette_fly.py` with `fake_components()`: picture encoder, value heads learn the toy task above 80% in 300 rounds (the pattern of `test_the_fly_learns_higher_or_lower` in `tests/test_casino.py`), fear and dopamine hooks, dashboard attach; no connectome needed

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
