<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# T44a Asset contract

| | |
|---|---|
| Primary agent | **Cora** (A01, Contracts & Architecture); spawn as `cora-contracts` |
| Supporting | A28 Petra (budgets); A15 Leo, A16 Mara, A17 Otto, A18 Rigo, A19 Anika, A20 Zara, A21 Wren, A22 Mika (consulted, each signs off) |
| Where / size | C / M (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | W2 |
| Depends on | T01 (Cora, A01) |
| Blocks | T42a, T42b, T44b, T45a, T45c, T45d, T45e, T45f, T45g, T45h |
| Reviewer | Petra (A28), Leo (A15) |

## Deliverable

Naming, attachments, joints, folders, budgets link, formats (models, textures, OGG audio), cue-id mapping, Hall and back-room anchors (seats, fly chair, charge box, cell tray, monitor, lights, camera), hand rigs, skin-variant rules, machine-readable lint expectations

## Owns (edit only these)

- `roblox/assets/SPEC.md`
- `roblox/assets/spec/`

## Read first

- [DESIGN.md](../DESIGN.md), sections 6, 7.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/cora-contracts.md`.
- The team handbook `docs/roblox/people/HANDBOOK.md`, once Hana has written it (T63).
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

Spec JSON validates against its schema; each asset agent signs off in `docs/roblox/ccr/asset-contract-v1-signoff.md`; budgets referenced from `roblox/assets/budgets.json`

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
