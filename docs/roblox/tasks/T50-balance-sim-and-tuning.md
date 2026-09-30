<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T50 Balance sim and tuning

| | |
|---|---|
| Primary agent | **Soren** (A05, Solver, Balance & Evaluation); spawn as `soren-solver` |
| Supporting | A03 Elena, A04 Felix, A30 Omar (real data later) |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 pass 1, W6 pass 2 |
| Depends on | T10 (Remy, A02), T11 (Elena, A03), T12 (Felix, A04), T13 (Soren, A05); pass 2 also T23 (A07), T22b (A05) |
| Blocks | nothing (end of a chain) |
| Reviewer | Elena (A03), Felix (A04) |

## Deliverable

Monte Carlo across archetypes x flies x zone; report vs targets; tuned numbers; pass 2 with real packs

## Owns (edit only these)

- `roblox/tools/balance_sim.luau`
- `docs/roblox/BALANCE_REPORT.md`

Also: values-only edits to roblox/src/shared/Config/Balance.luau and roblox/src/shared/Config/Floors.luau after T11 (handoff).

## Read first

- [DESIGN.md](../DESIGN.md), sections 3, 4.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/soren-solver.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Sim reproducible by seed; report meets targets (skilled 10-14, median 16-24, novice about 45 with 15-25% in the Basement) or documents a justified change; pass 2 re-run with real packs; only values changed; `CHK`

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
