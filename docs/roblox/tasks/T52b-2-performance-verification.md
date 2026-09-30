<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T52b-2 Performance verification

| | |
|---|---|
| Primary agent | **Petra** (A28, Performance); spawn as `petra-perf` |
| Supporting | A08 Vera, A16 Mara, A17 Otto, A18 Rigo, A21 Wren, A22 Mika, A12 Uma (fixes) |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W5 |
| Depends on | T24 (Vera, A08), T41 (Uma, A12), T42a (Theo, A13), T43 (Vera, A08), T45b (Mara, A16), T45c (Otto, A17), T45d (Rigo, A18), T45g (Wren, A21), T45h (Mika, A22) |
| Blocks | nothing (end of a chain) |
| Reviewer | Priya (A00) |

## Deliverable

Budget lint over all models, textures and audio manifests; instrumentation (frame time, memory, remote bytes); measured report vs budgets

## Owns (edit only these)

- `docs/roblox/PERFORMANCE.md`
- `roblox/src/shared/Perf/`
- `roblox/src/client/Perf/`
- `roblox/tools/lint/budgets.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 7, 7b, 8.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/petra-perf.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Budget lint passes on every asset manifest; Studio measurements recorded within budget or a waiver with an owner

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
