<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T46 Tutorial and onboarding

| | |
|---|---|
| Primary agent | **Toby** (A26, Tutorial); spawn as `toby-tutorial` |
| Supporting | A24 Dalia, A25 Tessa, A23 Nora, A09 Mateo (forced chamber), A27 Quinn (learnability) |
| Where / size | C+ST / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W5 |
| Depends on | T30a (Mateo, A09), T41 (Uma, A12), T42a (Theo, A13) |
| Blocks | T52a-2 |
| Reviewer | Quinn (A27) |

## Deliverable

Curriculum (the Signing, rules, counting, self-test, items, debt and interest, then Quickplay and the quests panel in the Hall), scripted chambers, hint triggers, completion conditions, service and UI

## Owns (edit only these)

- `roblox/src/server/Services/TutorialService.luau`
- `roblox/src/client/Tutorial/`
- `roblox/src/shared/Content/Tutorial.luau`
- `docs/roblox/tutorial/`
- `roblox/tests/integration/tutorial/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/toby-tutorial.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Scripted duel test is deterministic; every teaching beat has a completion condition; curriculum covers the Signing, rules, items, debt and interest, Quickplay and quests; learnability check in Studio (A27); `CHK`

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
