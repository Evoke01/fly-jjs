<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->
# Fly Roulette: agents

Extracted from [DESIGN.md](DESIGN.md) section 9. Definitions: `.claude/agents/<slug>.md`.

### 9.3 The roster: your 39 suggested roles -> 31 named specialists (+ the Lead)

Merged where one specialist naturally does both and the dependency chain is serial anyway. UI copy was in your must-have list but not your role list, so it got its own agent; Ines was added for the meta features. Names are placeholders you can change: rename the file in `.claude/agents/` and the `name` inside it.

| ID | Name | Role | Slug (`subagent_type`) | Covers your suggested roles |
|---|---|---|---|---|
| A00 | Priya | Project Architect (Lead) | `priya-lead` | Project Architect / Lead (main session) |
| A01 | Cora | Contracts & Architecture | `cora-contracts` | Contracts & Architecture |
| A02 | Remy | Rules Engine & RNG | `remy-rules` | Rules Engine, Deterministic RNG |
| A03 | Elena | Economy & Persistence | `elena-economy` | Economy & Debt, Data Persistence |
| A04 | Felix | Fly AI Runtime | `felix-fly-ai` | Fly AI Runtime |
| A05 | Soren | Solver, Balance & Evaluation | `soren-solver` | Solver & Balance, Brain Evaluation |
| A06 | Bea | Connectome & Brain Training | `bea-brain` | Connectome / Brain Training, Python Rules Port |
| A07 | Pax | FlyPack Export | `pax-flypack` | FlyPack Export |
| A08 | Vera | Brain Visualization & Monitor | `vera-brainviz` | Brain Visualization, Brain Monitor |
| A09 | Mateo | Roblox Backend | `mateo-backend` | Roblox Backend, Match/Table/Director, Networking |
| A10 | Sasha | Security / Anti-Exploit | `sasha-security` | Security / Anti-Exploit |
| A11 | Kiran | Client Core | `kiran-client` | Client Core |
| A12 | Uma | UI/UX | `uma-ui` | UI/UX |
| A13 | Theo | Presentation / Sequencer | `theo-sequencer` | Presentation / Sequencer |
| A14 | Camila | Cinematics | `camila-cinematics` | Cinematics |
| A15 | Leo | Level Design | `leo-level` | Level Design |
| A16 | Mara | Environment / Map Builder | `mara-environment` | Environment / Map Builder |
| A17 | Otto | Props / 3D Asset | `otto-props` | Props / 3D Asset |
| A18 | Rigo | Fly Character / Rigging | `rigo-rigging` | Fly Character / Rigging |
| A19 | Anika | Animation | `anika-animation` | Animation |
| A20 | Zara | VFX | `zara-vfx` | VFX |
| A21 | Wren | Sound Design | `wren-sound` | Sound Design |
| A22 | Mika | Music / Dynamic Audio | `mika-music` | Music / Dynamic Audio |
| A23 | Nora | Narrative / Worldbuilding | `nora-narrative` | Narrative / Worldbuilding |
| A24 | Dalia | Dialogue Writing | `dalia-dialogue` | Dialogue Writing |
| A25 | Tessa | UI Copy | `tessa-copy` | (added, from your must-have list) |
| A26 | Toby | Tutorial | `toby-tutorial` | Tutorial |
| A27 | Quinn | QA & Playtest | `quinn-qa` | QA / Automated Testing, Playtest |
| A28 | Petra | Performance | `petra-perf` | Performance |
| A29 | Lex | Compliance & Accessibility | `lex-compliance` | Compliance / Accessibility |
| A30 | Omar | Live-Ops & Telemetry | `omar-liveops` | Telemetry, Publishing / Live-Ops |
| A31 | Ines | Progression & Store | `ines-progression` | (added for the meta features: levels, titles, Buzz, store, inventory) |

### 9.6 Agent Directory

Every agent works only in its owned paths, reads its task brief and its own agent file first, treats contracts as frozen (change requests go to the Lead), and ends each task with the handoff report from 9.1. Waves in parentheses are from 9.7.

**A00 Priya, Project Architect (Lead)** - `priya-lead`, the main session
- Purpose: runs the programme: spawns specialists per wave, enforces gates, rules on change requests, merges PRs, keeps this design canonical.
- Tasks: none as primary; reviewer on T00, T30c, T47, T51, T52a-1, T52a-2, T52b-2; supporting on T22a, T47.
- Owns: D/README.md, D/DESIGN.md, D/TASKS.md, D/AGENTS.md, D/tasks/, D/ccr/, D/check_design.py, .claude/agents/, one-line pointer in README.md.
- May edit: only those; never product code.
- Inputs: this plan, handoff reports, CI results. Outputs: wave spawn lists, gate decisions, change-request rulings, a merged integration branch.
- Handoff when: a gate passes only when the task's checks (9.5) are pasted in the PR and the named reviewer has signed off.

**A01 Cora, Contracts & Architecture** - `cora-contracts`
- Purpose: repo scaffold owner and contract keeper; freezes every interface parallel agents share (2-4 seat types, protocol, schemas, cue/dialogue/string/notice catalogs, asset contract).
- Tasks: primary T00 (W0), T01 (W1), T44a (W2). Reviewer: T52b-1. Supporting: T30c, T44b.
- Owns: R/default.project.json, R/*.toml, R/.luaurc, R/.gitignore, R/scripts/, R/tests/run.luau, R/README.md, R/tools/build/smoke.luau, .github/workflows/roblox-ci.yml, S/Types.luau, S/Net/Protocol.luau, D/CONTRACTS.md, D/schemas/, R/assets/SPEC.md, R/assets/spec/.
- May edit: owned paths; bumps a contract version only after a Lead-approved change request.
- Inputs: this design, the existing repo (`main.py`, `fly_jjs/core/*`), Lune/Rojo/Selene docs. Outputs: `check.sh` and CI, `contracts-v1`, schemas and fixtures, catalogs, `SPEC.md` and `spec/*.json`.
- Handoff when: `CHK` is green in a fresh cloud session and the sign-off files exist.

**A02 Remy, Rules Engine & RNG** - `remy-rules`
- Purpose: game-rules and determinism engineer; implements zapper_v1 for 2-4 seats once in Luau and owns the shared sfc32 RNG in Luau and Python.
- Tasks: primary T02 (W1), T10 (W2). Reviewer: T01, T12, T13, T20. Supporting: T30a.
- Owns: S/Util/Rng.luau, PY/roulette_rng.py, R/vectors/rng_vectors.json, R/tests/rng/, PT/test_roulette_rng.py, S/Rules/, S/Config/Items.luau, S/Config/Rulesets.luau, R/tests/rules/, R/vectors/rules_vectors.json.
- May edit: owned paths; no Roblox APIs in `S/`.
- Inputs: section 2, `Types.luau` (Ruleset, Action, DuelEvent, View). Outputs: RNG in two languages, engine, item logic, redaction, vectors.
- Handoff when: property tests and vectors pass; the vectors PR merges before A06 starts its cross-check; A05 and A06 have signed off.

**A03 Elena, Economy & Persistence** - `elena-economy`
- Purpose: debt-economy and persistence engineer: ledger maths, floors and Basement, the DataStore layer, debt and lobby services, and the Hall wall-board feed.
- Tasks: primary T11 (W2), T31 (W3), T32 (W4). Reviewer: T02, T50, T60. Supporting: T01, T33b, T51.
- Owns: S/Economy/, S/Config/Balance.luau, S/Config/Floors.luau, R/tests/economy/, SV/Services/DataService.luau, SV/vendor/, R/tests/integration/data/, SV/Services/DebtService.luau, SV/Services/LobbyService.luau, R/tests/integration/debt/.
- May edit: owned paths; the numbers in Balance and Floors pass to A05 after T11.
- Inputs: section 3, Ledger and PlayerData types, RNG. Outputs: economy module, config tables, DataService, Debt and Lobby services.
- Handoff when: each task's checks pass and A05 confirms the Monte Carlo reproduction.

**A04 Felix, Fly AI Runtime** - `felix-fly-ai`
- Purpose: opponent-AI engineer: builds the runtime fly (belief, policy lookup, item logic, fear, quirks, director) and the fallback pack.
- Tasks: primary T12 (W3). Reviewer: T22b, T23, T30a, T45d, T50. Supporting: T01, T10, T43, T45e, T45h, T51.
- Owns: S/Fly/, S/Config/Flies.luau, SV/Data/flypacks/fallback.luau, R/tests/fly/.
- May edit: owned paths.
- Inputs: sections 4-5, View, Decision and FlyPack types, the engine. Outputs: FlyAgent, Director, loader, fallback pack, tests.
- Handoff when: tests pass, the fallback plays 1,000 duels per archetype, A05 and A02 have signed off.

**A05 Soren, Solver, Balance & Evaluation** - `soren-solver`
- Purpose: skill-measurement specialist: exact solver, player archetypes, the brain evaluation harness and the balance simulation ("how strong is each fly, how hard is the economy").
- Tasks: primary T13 (W3), T50 (W4 pass 1, W6 pass 2), T22b (W5). Reviewer: T10, T11, T12, T21, T22a, T32.
- Owns: S/Solver/, R/tools/archetypes.luau, R/vectors/solver_table.json, R/tests/solver/, R/tools/balance_sim.luau, D/BALANCE_REPORT.md, PY/roulette_eval.py, PT/test_roulette_eval.py, D/BRAIN_EVAL_REPORT.md; values-only edits to S/Config/Balance.luau and S/Config/Floors.luau after T11 (handoff).
- May edit: owned paths; logic changes in the config modules go through a change request to A03.
- Inputs: engine, ledger, fly runtime, snapshots, FlyPacks. Outputs: solver table, archetypes, eval report, balance report and tuned numbers.
- Handoff when: reports meet the targets or document a justified change, and every run is reproducible by seed.

**A06 Bea, Connectome & Brain Training** - `bea-brain`
- Purpose: Python and neuro-ML engineer: the Python rules port used for training, the connectome-facing RouletteTable, and the trainer that produces the six recipes.
- Tasks: primary T20 (W2), T21 (W3), T22a (W4, real bake on your PC). Reviewer: T02, T10, T22b. Supporting: T01, T12, T13, T23, T24.
- Owns: PY/roulette_rules.py, PT/test_roulette_rules.py, PY/roulette.py, PT/test_roulette_fly.py, PY/roulette_train.py, PT/test_roulette_train.py, main.py (the [R] menu entry only), D/BRAIN_PIPELINE.md, D/bake_logs/.
- May edit: owned paths; reuses but never edits `casino.py`, `slots.py`, `race.py`, `brain.py`, `vision.py`, `dashboard.py`.
- Inputs: sections 4-5, `rules_vectors.json`, `solver_table.json`, existing modules. Outputs: Python port, RouletteTable, trainer, menu, bake logs.
- Handoff when: pytest is green on FakeBrain, the vectors pass, and the PC bake logs are committed.

**A07 Pax, FlyPack Export** - `pax-flypack`
- Purpose: serialization specialist: turns trained snapshots into schema-valid, sharded Luau FlyPacks with provenance.
- Tasks: primary T23 (W4). Reviewer: T22a. Supporting: T12, T21.
- Owns: PY/roulette_export.py, PT/test_roulette_export.py, SV/Data/flypacks/{rookie,panic,cheetah,pro,cheater,collector}.luau (generated).
- May edit: owned paths; never edits `fallback.luau`.
- Inputs: FlyPack schema (T01), snapshots (T22a), loader (T12). Outputs: exporter and six generated packs.
- Handoff when: schema, size and round-trip checks pass and the fly passed T22b.

**A08 Vera, Brain Visualization & Monitor** - `vera-brainviz`
- Purpose: neuro-visualization engineer: bakes neuron layouts, activity clips and sprite sheets in Python and plays them on the in-world monitor in Luau.
- Tasks: primary T43 (W3, placeholder clips until T24), T24 (W4). Supporting: T21, T51, T52b-1, T52b-2.
- Owns: CL/BrainMonitor/, R/tests/client/monitor/, PY/roulette_viz.py, PT/test_roulette_viz.py, R/assets/brain/, D/BRAIN_VIZ.md.
- May edit: owned paths; updates its manifest when you give it uploaded asset ids.
- Inputs: connectome layout via `dashboard.neuron_layout`, RouletteTable hooks, cue catalog. Outputs: layout, clips, sheets, manifest, monitor player.
- Handoff when: texture budget met, manifest valid, monitor tests pass with placeholders and with real sheets.

**A09 Mateo, Roblox Backend** - `mateo-backend`
- Purpose: Roblox server-runtime engineer: platform adapters and boot, the networking layer, and the match, table and director services, including the back-room pool, Hall seating and Quickplay.
- Tasks: primary T30c (W2), T30b (W3), T30a (W4). Reviewer: T01, T32. Supporting: T31, T33a, T40, T46, T51.
- Owns: SV/Main.server.luau, SV/Platform/, R/tests/support/, S/Net/Server.luau, S/Net/Client.luau, R/tests/integration/net/, SV/Services/MatchService.luau, SV/Services/TableService.luau, SV/Services/DirectorService.luau, R/tests/integration/match/.
- May edit: owned paths; `Protocol.luau` changes go through a change request.
- Inputs: Platform and remote types, engine, FlyAgent. Outputs: bootstrap, adapters, fakes, net runtime, the three services.
- Handoff when: the Lune integration suites pass, the grep gate is clean, `rojo build` succeeds.

**A10 Sasha, Security / Anti-Exploit** - `sasha-security`
- Purpose: adversarial reviewer and builder of the validation layer: intent checks, rate limits, leak tests.
- Tasks: primary T33a (W5). Reviewer: T30a, T30b, T31, T60, T61, T62. Supporting: T30c, T33b, T51.
- Owns: SV/Services/Guard.luau, R/tests/security/, D/SECURITY.md.
- May edit: owned paths; reports findings on others' code through the Lead.
- Inputs: net runtime, match service, threat model in this design. Outputs: Guard, adversarial suite, threat model.
- Handoff when: the suite and fuzz pass and no high finding is open.

**A11 Kiran, Client Core** - `kiran-client`
- Purpose: Roblox client architect: Hall and back-room cameras, input across keyboard/mouse, touch and gamepad, and the event-fed state store.
- Tasks: primary T40 (W2). Supporting: T30b, T51.
- Owns: CL/Controllers/, CL/State/, CL/Main.client.luau, R/tests/client/state/.
- May edit: owned paths.
- Inputs: Protocol, cue catalog, focus points in section 7. Outputs: controllers and state store that all other client agents build on.
- Handoff when: reducer and input tests pass and the Studio smoke checklist is done.

**A12 Uma, UI/UX** - `uma-ui`
- Purpose: interface designer-engineer: the Hall HUD, back-room HUD, overhead title tags, wall boards, store, inventory, elevator, settings and credits screens, in the reference's pixel style, mobile-first.
- Tasks: primary T41 (W3). Reviewer: T40, T49. Supporting: T30a, T51, T52a-2, T52b-2, T60, T61, T62.
- Owns: CL/UI/, R/tests/client/ui/, D/ui/.
- May edit: owned paths; reads strings from `Strings.luau` and never hard-codes text.
- Inputs: state store, string keys, accessibility memo. Outputs: screens, view-models, layout lint results.
- Handoff when: tests and layout lint pass and the Studio checklist is done on three input types.

**A13 Theo, Presentation / Sequencer** - `theo-sequencer`
- Purpose: turns the duel event stream into timed presentation: fly state machine, tells, captions and turn banner, cue bus, skip and fast-forward.
- Tasks: primary T42a (W3). Reviewer: T43, T45e, T45g, T45h. Supporting: T45f, T51.
- Owns: CL/Presentation/Sequencer/, R/tests/client/sequencer/.
- May edit: owned paths.
- Inputs: cue catalog (T01), client state, asset contract. Outputs: sequencer other presentation agents plug into.
- Handoff when: fixture timelines are deterministic and every cue id exists in the catalog.

**A14 Camila, Cinematics** - `camila-cinematics`
- Purpose: cutscene director-engineer: storyboards, timelines and the timeline player for all non-duel sequences.
- Tasks: primary T42b (W4). Reviewer: T42a, T45h. Supporting: T45a, T45e, T48.
- Owns: CL/Cinematics/, S/Content/Cinematics.luau, D/cinematics/, R/tests/client/cinematics/.
- May edit: owned paths.
- Inputs: sequencer API, narrative bible, dialogue lines, level camera anchors. Outputs: timelines for the Signing, room entry and return, dossier, Shark call, elevator, Basement drop, revival, KO, credits.
- Handoff when: timeline lint passes and subtitles cover every line.

**A15 Leo, Level Design** - `leo-level`
- Purpose: designs the space from the reference: the Hall, the back-room template and its Basement variant, the elevator and infirmary; sightlines and camera anchors.
- Tasks: primary T45a (W3). Reviewer: T44a, T44b, T45b. Supporting: T42b, T45c.
- Owns: R/assets/blueprints/, D/level/, R/tools/lint/blueprints.luau.
- May edit: owned paths.
- Inputs: asset contract, narrative bible, section 7. Outputs: blueprints (JSON and diagrams).
- Handoff when: blueprint lint passes and A16 confirms it is buildable.

**A16 Mara, Environment / Map Builder** - `mara-environment`
- Purpose: builds the Roblox environment as files: the graybox first, then the final Hall and back room from the blueprints, with felt variants for the store.
- Tasks: primary T44b (W3), T45b (W4). Reviewer: T45a. Supporting: T44a, T52b-2, T62.
- Owns: R/tools/build/graybox/, R/assets/models/graybox/, R/tools/lint/env.luau, R/tools/build/env/, R/assets/models/env/.
- May edit: owned paths.
- Inputs: asset contract, blueprints, props list. Outputs: `.rbxm` environment models and the Studio import checklist.
- Handoff when: env lint passes, builds are reproducible, `rojo build` succeeds.

**A17 Otto, Props / 3D Asset** - `otto-props`
- Purpose: builds props as parametric models: zap racket and its skins, cells, cell tray, charge box, stage lights, Hall tables and wall boards, items, phone and furniture.
- Tasks: primary T45c (W3). Supporting: T44a, T45b, T45f, T52b-2, T62.
- Owns: R/tools/build/props/, R/assets/models/props/, R/tools/lint/props.luau.
- May edit: owned paths.
- Inputs: asset contract, narrative style notes. Outputs: prop models and lint.
- Handoff when: props lint passes and A19 confirms grip attachments.

**A18 Rigo, Fly Character / Rigging** - `rigo-rigging`
- Purpose: designs and rigs the six flies with costumes and tells, the fly's floating forelegs, and the player's floating gloves and glove skins.
- Tasks: primary T45d (W3). Reviewer: T45e. Supporting: T44a, T52b-2, T62.
- Owns: R/tools/build/flies/, R/assets/models/flies/, R/tools/lint/rigs.luau.
- May edit: owned paths.
- Inputs: asset contract, fly bios from the bible, emote and tell ids. Outputs: six rigs and rig lint.
- Handoff when: rig lint passes and A19 can animate every required joint.

**A19 Anika, Animation** - `anika-animation`
- Purpose: motion designer-engineer: data-driven poses and a procedural player for fly states and the floating hands.
- Tasks: primary T45e (W4). Reviewer: T45c, T45d. Supporting: T42a, T42b, T44a.
- Owns: CL/Presentation/Anim/, R/assets/animations/, R/tests/client/anim/.
- May edit: owned paths.
- Inputs: rigs, cue catalog, tell list. Outputs: pose library, player, optional KeyframeSequence export.
- Handoff when: curve and joint tests pass and durations match the catalog.

**A20 Zara, VFX** - `zara-vfx`
- Purpose: effects artist-engineer: presets for zap, fizzle, cell glow, charge-box and stage-light flicker, items, blackout, KO, elevator, phone and monitor, each with a reduced-flash variant.
- Tasks: primary T45f (W3). Reviewer: T42a. Supporting: T44a, T45b, T45c, T52a-2.
- Owns: CL/Presentation/Vfx/, R/assets/vfx/, R/tests/client/vfx/, R/tools/lint/vfx.luau.
- May edit: owned paths.
- Inputs: cue catalog, accessibility memo, particle budgets. Outputs: preset library and lint.
- Handoff when: VFX lint passes and A29 has signed off the flash limits.

**A21 Wren, Sound Design** - `wren-sound`
- Purpose: synthesizes original sound effects in Python and maps them to cues.
- Tasks: primary T45g (W3). Supporting: T42a, T44a, T45b, T52a-2, T52b-2.
- Owns: R/tools/audio/sfx/, R/assets/audio/sfx/, CL/Audio/Sfx/, R/tests/audio/sfx/, R/tools/lint/audio.py.
- May edit: owned paths; the audio lint is shared with A22, who may not edit it.
- Inputs: cue catalog, narrative tone, audio budgets. Outputs: OGG files, cue map, upload manifest.
- Handoff when: audio lint passes and every cue has a file.

**A22 Mika, Music / Dynamic Audio** - `mika-music`
- Purpose: composes synthesized stems and the MusicDirector that mixes them by lives and terror.
- Tasks: primary T45h (W3). Supporting: T42a, T42b, T44a, T52a-2, T52b-2.
- Owns: R/tools/audio/music/, R/assets/audio/music/, CL/Audio/Music/, R/tests/audio/music/.
- May edit: owned paths; runs A21's audio lint.
- Inputs: cue catalog, terror and confidence semantics, narrative tone. Outputs: stems, stingers, MusicDirector.
- Handoff when: gain-function tests and audio lint pass.

**A23 Nora, Narrative / Worldbuilding** - `nora-narrative`
- Purpose: story owner: premise, the Shark and the loan contract, fly names and bios, floors, title and Buzz flavour, tone and taboo list.
- Tasks: primary T47 (W0). Reviewer: T42b, T48. Supporting: T45a, T45d, T46, T52a-2, T60.
- Owns: D/narrative/BIBLE.md, S/Content/Lore.luau.
- May edit: owned paths.
- Inputs: this design, the README honesty statement. Outputs: bible and Lore table that every content agent reads.
- Handoff when: the checklist against this design passes and A29 has cleared tone and policy.

**A24 Dalia, Dialogue Writing** - `dalia-dialogue`
- Purpose: writes in-world speech: Shark calls, typewriter captions, fly barks, announcements, tutorial lines.
- Tasks: primary T48 (W2). Supporting: T32, T42b, T46, T52a-2.
- Owns: S/Content/Dialogue.luau, D/narrative/DIALOGUE.md, R/tools/lint/dialogue.luau.
- May edit: owned paths.
- Inputs: bible, dialogue key catalog (T01), mood table. Outputs: dialogue data and lint.
- Handoff when: dialogue lint passes and A23 confirms the voice.

**A25 Tessa, UI Copy** - `tessa-copy`
- Purpose: writes every interface string: labels, tooltips, item text, quest texts, store items, titles, notices, settings, accessibility labels, credits copy.
- Tasks: primary T49 (W2). Supporting: T41, T46, T48, T52a-2, T60, T61.
- Owns: S/Content/Strings.luau, D/narrative/UI_COPY.md, R/tools/lint/strings.luau.
- May edit: owned paths.
- Inputs: bible, string and notice catalogs (T01), screen list. Outputs: string table and lint.
- Handoff when: strings lint passes and A12 confirms the keys fit the screens.

**A26 Toby, Tutorial** - `toby-tutorial`
- Purpose: teaches the game, from the Signing to the Hall: curriculum, scripted chambers, hints and completion conditions, with the service and UI hooks.
- Tasks: primary T46 (W5). Supporting: T30a, T48, T49, T51.
- Owns: SV/Services/TutorialService.luau, CL/Tutorial/, S/Content/Tutorial.luau, D/tutorial/, R/tests/integration/tutorial/.
- May edit: owned paths.
- Inputs: engine scripted-chamber hook, dialogue and strings, UI and sequencer. Outputs: tutorial service, UI and content.
- Handoff when: the scripted duel test is deterministic and A27 confirms learnability in Studio.

**A27 Quinn, QA & Playtest** - `quinn-qa`
- Purpose: quality owner: bot-driven E2E, playtest plan and evidence, defect log.
- Tasks: primary T51 (W6). Reviewer: T33a, T46. Supporting: T00, T53.
- Owns: R/tests/e2e/, R/tools/bots/, D/PLAYTEST.md, D/QA_REPORT.md.
- May edit: owned paths; files defects against owners through the Lead.
- Inputs: all services and client modules, fakes. Outputs: E2E suite, playtest checklist and evidence, defect log.
- Handoff when: 100 bot loops pass, Studio evidence is recorded, and no blocker is open.

**A28 Petra, Performance** - `petra-perf`
- Purpose: performance owner: budgets first, then verification of every asset and system against them.
- Tasks: primary T52b-1 (W0), T52b-2 (W5). Reviewer: T24, T43, T44a, T45b, T45c, T45f. Supporting: T30a, T41, T45a, T45d, T45g, T45h, T51.
- Owns: D/PERFORMANCE.md (Budgets section), R/assets/budgets.json, D/PERFORMANCE.md, S/Perf/, CL/Perf/, R/tools/lint/budgets.luau.
- May edit: owned paths.
- Inputs: asset manifests, Studio measurements. Outputs: budgets, budget lint, instrumentation, measured report.
- Handoff when: the lint passes on every manifest or waivers are recorded.

**A29 Lex, Compliance & Accessibility** - `lex-compliance`
- Purpose: policy and accessibility owner: verifies current Roblox rules, audits content, assets, the store, quests and codes, and originality against the reference, prepares the questionnaire and credits.
- Tasks: primary T52a-1 (W0), T52a-2 (W6). Reviewer: T24, T33b, T41, T42b, T45a, T45f, T45g, T47, T48, T49, T53, T62. Supporting: T23, T40, T51, T61.
- Owns: D/COMPLIANCE.md (Requirements section), D/ACCESSIBILITY.md (Requirements section), D/COMPLIANCE.md, D/ACCESSIBILITY.md, S/Content/Credits.luau.
- May edit: owned paths; content fixes are requested from the content owners.
- Inputs: live policy pages, all content and assets. Outputs: requirements memo, audit matrix, questionnaire draft, credits.
- Handoff when: the audit matrix is fully passing and the Lead has signed off.

**A30 Omar, Live-Ops & Telemetry** - `omar-liveops`
- Purpose: measurement, quests and launch owner: KPI events, daily quests and redeem codes, dashboards, publish checklist, roadmap.
- Tasks: primary T33b (W5), T61 (W5), T53 (W7). Supporting: T11, T31, T32, T41, T49, T50, T52a-2, T60, T62.
- Owns: SV/Services/Telemetry.luau, R/tests/telemetry/, D/TELEMETRY.md, S/Content/Quests.luau, SV/Services/QuestService.luau, SV/Data/Codes.luau, R/tests/quests/, D/LIVEOPS.md, D/PUBLISH_CHECKLIST.md.
- May edit: owned paths.
- Inputs: event catalog, match and ledger events, ProgressionService, compliance audit. Outputs: emitters, dashboard spec, publish checklist, roadmap.
- Handoff when: every KPI is emitted and verified, and the publish checklist is resolved.

**A31 Ines, Progression & Store** - `ines-progression`
- Purpose: meta-progression and store engineer: XP, levels, titles, the rank badge, the Buzz wallet, the cosmetic catalog, purchases, inventory and equip.
- Tasks: primary T60 (W4), T62 (W5). Reviewer: T61. Supporting: T41, T45b, T45c, T45d, T49, T53.
- Owns: S/Progression/, S/Config/Progression.luau, SV/Services/ProgressionService.luau, R/tests/progression/, S/Content/Catalog.luau, SV/Services/StoreService.luau, R/tests/store/.
- May edit: owned paths; profile-field changes go through a change request to Cora (contracts) and Elena (DataService).
- Inputs: section 7b, the PlayerData v1 meta fields, DataService, match events, the Roblox MarketplaceService docs. Outputs: ProgressionService, StoreService, catalog and title registry.
- Handoff when: each gate passes, receipts are idempotent, and Sasha has signed off.
