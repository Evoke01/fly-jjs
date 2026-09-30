<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T48 Dialogue and barks

| | |
|---|---|
| Primary agent | **Dalia** (A24, Dialogue Writing); spawn as `dalia-dialogue` |
| Supporting | A23 Nora, A25 Tessa, A26 Toby, A14 Camila, A29 Lex |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W2 |
| Depends on | T47 (Nora, A23), T01 (Cora, A01) |
| Blocks | T52a-2 |
| Reviewer | Nora (A23), Lex (A29) |

## Deliverable

Shark calls per mood (6+ variants each), typewriter captions ("THE CELLS ENTER", load and turn lines), fly barks per fly and situation, elevator, foreclosure, revival and freedom lines, tutorial lines; ids, speakers, tags, length limits

## Owns (edit only these)

- `roblox/src/shared/Content/Dialogue.luau`
- `docs/roblox/narrative/DIALOGUE.md`
- `roblox/tools/lint/dialogue.luau`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/dalia-dialogue.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Dialogue lint: unique ids, every required id from the T01 catalog present, length limits, valid placeholders, banned terms; tone review against the bible

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
