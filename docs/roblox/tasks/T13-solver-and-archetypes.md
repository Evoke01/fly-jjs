<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T13 Solver and archetypes

| | |
|---|---|
| Primary agent | **Soren** (A05, Solver, Balance & Evaluation); spawn as `soren-solver` |
| Supporting | A02 Remy (API), A06 Bea (consumes the table) |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T10 (Remy, A02) |
| Blocks | T22a, T22b, T50 |
| Reviewer | Remy (A02) |

## Deliverable

Exact optimal policy and value table for item-less states; player archetypes (novice, median, skilled, optimal) calibrated to average win rates 0.36, 0.57, 0.77 against the fallback pack

## Owns (edit only these)

- `roblox/src/shared/Solver/`
- `roblox/tools/archetypes.luau`
- `roblox/vectors/solver_table.json`
- `roblox/tests/solver/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 2, 4.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/soren-solver.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Solver table equals brute-force enumeration over every chamber order for all states (up to 8 cells); optimal wins 75% or more vs random over 10k seeded duels; archetype win rates within 0.03 of 0.36 / 0.57 / 0.77 vs the fallback mix; `CHK`

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
