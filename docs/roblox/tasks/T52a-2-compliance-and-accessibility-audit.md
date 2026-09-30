<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T52a-2 Compliance and accessibility audit

| | |
|---|---|
| Primary agent | **Lex** (A29, Compliance & Accessibility); spawn as `lex-compliance` |
| Supporting | A23 Nora, A24 Dalia, A25 Tessa (content fixes), A20 Zara, A12 Uma, A21 Wren, A22 Mika, A30 Omar |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W6 |
| Depends on | T33a (Sasha, A10), T33b (Omar, A30), T41 (Uma, A12), T42b (Camila, A14), T46 (Toby, A26), T48 (Dalia, A24), T49 (Tessa, A25), T45f (Zara, A20), T45g (Wren, A21), T45h (Mika, A22), T61 (Omar, A30), T62 (Ines, A31) |
| Blocks | T53 |
| Reviewer | Priya (A00) |

## Deliverable

Content scan, flash, contrast, tap-target and caption audit, store/quest/code policy check, originality check against the reference game, questionnaire answers, credits (MaleCNS, flybrain, honesty statement), sign-off matrix

## Owns (edit only these)

- `docs/roblox/COMPLIANCE.md`
- `docs/roblox/ACCESSIBILITY.md`
- `roblox/src/shared/Content/Credits.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 7, 7b, 8.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/lex-compliance.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Content scan clean; audit matrix (flash, contrast, tap targets, captions, originality) all pass; questionnaire draft complete

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
