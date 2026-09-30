<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T51 Integration, E2E and playtest

| | |
|---|---|
| Primary agent | **Quinn** (A27, QA & Playtest); spawn as `quinn-qa` |
| Supporting | A03 Elena, A04 Felix, A08 Vera, A09 Mateo, A10 Sasha, A11 Kiran, A12 Uma, A13 Theo (each fixes defects in its own modules), A26 Toby, A28 Petra, A29 Lex |
| Where / size | C+ST / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W6 |
| Depends on | T30a (Mateo, A09), T30b (Mateo, A09), T30c (Mateo, A09), T31 (Elena, A03), T32 (Elena, A03), T33a (Sasha, A10), T33b (Omar, A30), T40 (Kiran, A11), T41 (Uma, A12), T42a (Theo, A13), T43 (Vera, A08), T60 (Ines, A31), T61 (Omar, A30), T62 (Ines, A31) |
| Blocks | nothing (end of a chain) |
| Reviewer | Priya (A00) |

## Deliverable

Bot-driven E2E of the full loop with fakes (incl. a quest claim, a Buzz purchase, equip and rejoin), Studio playtest checklist and evidence, defect log

## Owns (edit only these)

- `roblox/tests/e2e/`
- `roblox/tools/bots/`
- `docs/roblox/PLAYTEST.md`
- `docs/roblox/QA_REPORT.md`

## Read first

- [DESIGN.md](../DESIGN.md), sections 1, 7b, 10.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/quinn-qa.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

E2E bots finish 100 full loops (join, tutorial, duels, interest, Freed or Basement, rejoin) with zero contract violations; Studio playtest evidence recorded; defect log has no open blocker; `CHK`

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
