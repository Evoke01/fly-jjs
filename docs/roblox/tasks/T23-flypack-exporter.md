<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T23 FlyPack exporter

| | |
|---|---|
| Primary agent | **Pax** (A07, FlyPack Export); spawn as `pax-flypack` |
| Supporting | A06 Bea (snapshots), A04 Felix (loader), A29 Lex (attribution metadata) |
| Where / size | C+PC / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W4 |
| Depends on | T01 (Cora, A01), T21 (Bea, A06) |
| Blocks | nothing (end of a chain) |
| Reviewer | Felix (A04) |

## Deliverable

Q-tables, temperature, fear curve, think times, item personality -> schema-valid sharded Luau packs with provenance; a real export runs only after that fly passes T22b

## Owns (edit only these)

- `fly_jjs/core/roulette_export.py`
- `tests/test_roulette_export.py`
- `roblox/src/server/Data/flypacks/rookie.luau`
- `roblox/src/server/Data/flypacks/panic.luau`
- `roblox/src/server/Data/flypacks/cheetah.luau`
- `roblox/src/server/Data/flypacks/pro.luau`
- `roblox/src/server/Data/flypacks/cheater.luau`
- `roblox/src/server/Data/flypacks/collector.luau`

Also: generated.

## Read first

- [DESIGN.md](../DESIGN.md), sections 4, 5.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/pax-flypack.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

`PYT test_roulette_export.py`: schema-valid, every shard under 100 KB, deterministic bytes; the T12 Lune loader reads every generated pack and reproduces Python decisions on 200 sampled states; provenance present

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
