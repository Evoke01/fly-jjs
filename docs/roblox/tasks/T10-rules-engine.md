<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T10 Rules engine

| | |
|---|---|
| Primary agent | **Remy** (A02, Rules Engine & RNG); spawn as `remy-rules` |
| Supporting | A05 Soren (API), A06 Bea (vector consumer), A04 Felix (View consumer) |
| Where / size | C / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W2 |
| Depends on | T01 (Cora, A01), T02 (Remy, A02) |
| Blocks | T12, T13, T30a, T50 |
| Reviewer | Soren (A05), Bea (A06) |

## Deliverable

zapper_v1 reducer for 2-4 seats (the MVP ruleset uses 2): loads, turns, 5 MVP items, redacted views, events, replay, scripted-chamber hook for the tutorial; vectors merged first

## Owns (edit only these)

- `roblox/src/shared/Rules/`
- `roblox/src/shared/Config/Items.luau`
- `roblox/src/shared/Config/Rulesets.luau`
- `roblox/tests/rules/`
- `roblox/vectors/rules_vectors.json`

## Read first

- [DESIGN.md](../DESIGN.md), sections 2, 6.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/remy-rules.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Property tests (lives within 0..max, chamber counts, turn rules, View never reveals an unrevealed cell); `rules_vectors.json` green; replay determinism; `CHK`

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
