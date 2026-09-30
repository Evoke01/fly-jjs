<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T41 UI and HUD

| | |
|---|---|
| Primary agent | **Uma** (A12, UI/UX); spawn as `uma-ui` |
| Supporting | A25 Tessa (strings), A29 Lex (contrast, tap targets), A28 Petra, A31 Ines (progression and store data), A30 Omar (quests panel) |
| Where / size | C+ST / L (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W3 |
| Depends on | T01 (Cora, A01), T40 (Kiran, A11) |
| Blocks | T46, T51, T52a-2, T52b-2 |
| Reviewer | Lex (A29) |

## Deliverable

Hall HUD from section 7 (Quickplay, debt and Buzz counters, level and XP bar, rank badge, quests panel, Inventory, Store, Invite Friends, Redeem Codes), overhead title tags, Hall wall boards, back-room HUD (turn banner and timer, caption box, item bar, Shark popup), charge-box display, store, inventory, elevator, settings and credits screens; pixel-font style; view-model tests

## Owns (edit only these)

- `roblox/src/client/UI/`
- `roblox/tests/client/ui/`
- `docs/roblox/ui/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/uma-ui.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

View-model tests for every Hall and back-room element in section 7; layout lint (safe area, minimum tap target, contrast at least 4.5:1 computed from the palette, no string wider than its box in the pixel font); Studio checklist on desktop, phone and gamepad; `CHK`

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
