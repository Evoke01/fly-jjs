<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T49 UI copy

| | |
|---|---|
| Primary agent | **Tessa** (A25, UI Copy); spawn as `tessa-copy` |
| Supporting | A12 Uma, A29 Lex (plain language, screen-reader labels), A26 Toby, A30 Omar (quest texts), A31 Ines (store and title names) |
| Where / size | C / S (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W2 |
| Depends on | T47 (Nora, A23), T01 (Cora, A01) |
| Blocks | T52a-2 |
| Reviewer | Uma (A12), Lex (A29) |

## Deliverable

Every HUD, menu, item, notice, settings and accessibility string by key, plus quest texts, store item names and descriptions, title and rank names; uppercase pixel-font length limits; credits copy; completeness lint

## Owns (edit only these)

- `roblox/src/shared/Content/Strings.luau`
- `docs/roblox/narrative/UI_COPY.md`
- `roblox/tools/lint/strings.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/tessa-copy.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Strings lint: every Notice code and UI key has a string, length limits, valid placeholders; reading-level and tone check

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
