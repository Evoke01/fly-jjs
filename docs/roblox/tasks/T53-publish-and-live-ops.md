<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T53 Publish and live-ops

| | |
|---|---|
| Primary agent | **Omar** (A30, Live-Ops & Telemetry); spawn as `omar-liveops` |
| Supporting | A29 Lex, A27 Quinn, A31 Ines (store setup) |
| Where / size | human + C / S (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W7 |
| Depends on | T52a-2 (Lex, A29) |
| Blocks | nothing (end of a chain) |
| Reviewer | Lex (A29) |

## Deliverable

Publish checklist (questionnaire, icon and thumbnail specs, store and developer-product setup, launch codes, monetization policy check), dashboard spec from the T33b KPIs, event calendar, roadmap (Floors 2-4, items 6-9, Queen)

## Owns (edit only these)

- `docs/roblox/LIVEOPS.md`
- `docs/roblox/PUBLISH_CHECKLIST.md`

## Read first

- [DESIGN.md](../DESIGN.md), sections 7b, 8.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/omar-liveops.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Publish checklist fully resolved; dashboard spec covers every KPI in T33b; roadmap lists Floors 2-4, items 6-9 and the Queen

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
