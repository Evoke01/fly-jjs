<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T52a-1 Policy and accessibility requirements memo

| | |
|---|---|
| Primary agent | **Lex** (A29, Compliance & Accessibility); spawn as `lex-compliance` |
| Supporting | A00 Priya |
| Where / size | C / S (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W0 |
| Depends on | none |
| Blocks | nothing (end of a chain) |
| Reviewer | Priya (A00) |

## Deliverable

Verified current policy requirements (URLs and dates) for gambling, self-harm, violence and fear labels, audio originality, flashing; accessibility checklist for UI, VFX and audio; questionnaire outline

## Owns (edit only these)

- `docs/roblox/COMPLIANCE.md`
- `docs/roblox/ACCESSIBILITY.md`

Also: Requirements section; Requirements section.

## Read first

- [DESIGN.md](../DESIGN.md), sections 7, 7b, 8.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/lex-compliance.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Memo cites the live policy pages (URL and retrieval date) and lists concrete rules for each downstream agent

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
