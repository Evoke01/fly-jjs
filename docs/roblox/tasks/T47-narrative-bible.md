<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T47 Narrative bible

| | |
|---|---|
| Primary agent | **Nora** (A23, Narrative / Worldbuilding); spawn as `nora-narrative` |
| Supporting | A29 Lex (tone and policy), A00 Priya |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W0 |
| Depends on | none |
| Blocks | T42b, T45a, T45c, T45d, T45g, T45h, T48, T49 |
| Reviewer | Lex (A29), Priya (A00) |

## Deliverable

Premise, the Shark and the loan contract, six fly bios with the names shown on the charge box, floors and Basement lore, title and Buzz flavour, voice guide, taboo list, glossary, credits text; Lore data table

## Owns (edit only these)

- `docs/roblox/narrative/BIBLE.md`
- `roblox/src/shared/Content/Lore.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/nora-narrative.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Checklist against this design (six flies, floors, mood names, the Shark); policy screen (no self-harm imagery, no gambling promotion); consistent glossary; Lore table lints

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
