# Fly Roulette (Roblox): design and delegation

A Buckshot-Roulette-style Roblox game starring the fly from this repo. You owe the Shark $1,000,000, the debt grows with random interest, and you pay it off by beating randomly drawn flies (Rookie, Panic, Cheetah, Pro, Cheater, Collector) in a zap-racket duel, 3 charges each. Each fly's decisions come from a brain trained offline on the real connectome, and its brain plays on a monitor beside the table. The look follows your reference screenshots: a shared Hall lobby, private brick back rooms, a charge box with lightning bolts, floating hands and typewriter captions.

**Status:** design only. No game code exists yet; the work items below build it.

| Read | For |
|---|---|
| [DESIGN.md](DESIGN.md) | The whole design; the source of truth |
| [CONTRACTS.md](CONTRACTS.md) | Draft shared types, remotes, saved data and catalogs (frozen in T01) |
| [TASKS.md](TASKS.md) | 49 work items: owner, dependencies, deliverable, handoff gate, waves |
| [AGENTS.md](AGENTS.md) | The 31 named specialists and the Lead: what each owns and delivers |
| [tasks/](tasks/) | One brief per work item, the prompt a specialist works from |
| [ccr/](ccr/) | Change requests to frozen contracts |

## How the build runs

1. The main Claude Code session is the Lead, **Priya**. The specialists are project subagents in `.claude/agents/`; restart the session once so they load, and check them with `/agents`.
2. Work goes in waves (TASKS.md, section 9.7). For every item in a wave, the Lead spawns its primary specialist (`subagent_type` = the slug, such as `remy-rules`) in a worktree, in the background, with the prompt `Do <ID> exactly as written in docs/roblox/tasks/<brief>.md`.
3. Each specialist edits only its own paths, opens one PR per item and pastes its handoff checks. The named reviewer signs off, then the Lead merges.
4. Run 6-8 specialists at a time, critical path first: T00 > T01 > T10 > T12 > T30a > T33a > T52a-2 > T53.

Paste this into the main session to start a wave:

```
Read docs/roblox/README.md and docs/roblox/TASKS.md. Execute Wave 0: for every work item listed,
spawn its primary specialist in a worktree, in the background, with the prompt
"Do <ID> exactly as written in docs/roblox/tasks/<brief>.md". When they finish, run the handoff
gates in TASKS.md, merge passing PRs into the integration branch, and stop at the wave gate.
```

## What only you can do

- **H1** Import the generated `.rbxm` models and upload audio and sprite sheets in Studio or Open Cloud; give the asset ids back to the agent that made them.
- **H2** Run the real brain bake on your PC (T22a, T23, T24), since it needs the 260 MB connectome.
- **H3** Run the Studio checklists in the briefs and paste the evidence.
- **H4** Keep Roblox universe and place ids and any Open Cloud key outside git.
- **H5** Fill in the maturity questionnaire and publish, using the publish checklist from T53.

## Changing the plan

Edit [DESIGN.md](DESIGN.md), then regenerate and check everything derived from it:

```
python docs/roblox/check_design.py --write
python docs/roblox/check_design.py
```

The check fails on unknown or unowned work, dependency cycles, waves that no longer match the dependencies, two agents owning the same path, reviewers reviewing their own work, stale briefs or agent files, and broken links.
