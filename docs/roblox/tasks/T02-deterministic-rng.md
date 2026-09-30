<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T02 Deterministic RNG

| | |
|---|---|
| Primary agent | **Remy** (A02, Rules Engine & RNG); spawn as `remy-rules` |
| Supporting | A06 Bea (Python user), A03 Elena (Luau user) |
| Where / size | C / S (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W1 |
| Depends on | T00 (Cora, A01) |
| Blocks | T10, T11, T20 |
| Reviewer | Bea (A06), Elena (A03) |

## Deliverable

sfc32 with unbiased nextInt, nextFloat, shuffle, fork; identical outputs in Luau and Python; vectors for 20+ seeds

## Owns (edit only these)

- `roblox/src/shared/Util/Rng.luau`
- `fly_jjs/core/roulette_rng.py`
- `roblox/vectors/rng_vectors.json`
- `roblox/tests/rng/`
- `tests/test_roulette_rng.py`

## Read first

- [DESIGN.md](../DESIGN.md), sections 2, 6.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/remy-rules.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Same 20 seeds x 10k draws identical from `lune run tests/run rng` and `PYT test_roulette_rng.py`; chi-square unbiasedness test; shuffle vectors

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
