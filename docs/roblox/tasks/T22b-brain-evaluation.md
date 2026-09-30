<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T22b Brain evaluation

| | |
|---|---|
| Primary agent | **Soren** (A05, Solver, Balance & Evaluation); spawn as `soren-solver` |
| Supporting | A06 Bea, A04 Felix (recipe expectations) |
| Where / size | C+PC / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W5 |
| Depends on | T22a (Bea, A06), T13 (Soren, A05) |
| Blocks | nothing (end of a chain) |
| Reviewer | Bea (A06), Felix (A04) |

## Deliverable

Eval harness (agreement with the solver, win rate vs archetypes, decision entropy, fear response) with per-recipe pass bands, plus the report on real snapshots

## Owns (edit only these)

- `fly_jjs/core/roulette_eval.py`
- `tests/test_roulette_eval.py`
- `docs/roblox/BRAIN_EVAL_REPORT.md`

## Read first

- [DESIGN.md](../DESIGN.md), sections 4, 5.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/soren-solver.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

`PYT test_roulette_eval.py` on FakeBrain snapshots; on real snapshots the report meets starting bands (solver agreement: Rookie 55-70%, Cheetah 65-80%, Pro 90% or more, Cheater 90% or more with peek, Collector 93% or more; Panic within 5 points of Pro when ahead and at least 10 points lower when behind); a fly outside its band blocks its real export

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
