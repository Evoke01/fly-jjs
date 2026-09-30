# Fly Roulette: System Design v0.3 (working title)

> **v0.3 = v0.2 + your reference screenshots + human agent names.** New since v0.2: section 7 now specifies the look and feel from your screenshots (the Hall lobby, private back rooms, charge box, floating hands, captions, turn banner, HUD); new section 7b covers the meta features you picked (levels, XP and titles; daily quests and codes; a cosmetic store and inventory); the rules engine supports 2-4 seats from day one while the MVP stays solo; the weapon stays a zap racket; every agent now has a human first name and a `name-role` slug; one specialist (Ines) and three work items (T60-T62) were added for the meta features. The duel rules and economy (sections 2-5) are unchanged apart from a 60 s turn timer and the Buzz rule in section 3.

## Context

`fly-jjs` already holds the fly: a simulated fruit-fly brain (MaleCNS connectome, 166,700 neurons, `flybrain` package) that plays Roblox JJS from screen capture, plus `fly_jjs/core/casino.py`, a Higher-or-Lower death match where the fly learns from dopamine (PAM/PPL1 neurons), is afraid through a measured fear circuit (LC4/LPLC2/PPL1 -> giant fibre DNp01) and gets "shot" if it ends behind.

The new project is a Roblox game in the style of Buckshot Roulette starring that fly. You owe $1,000,000, the debt grows by random interest, and you pay it off by winning duels against randomly drawn fly types (3 lives each). This document is the system design, cut into 27 tasks (49 work items after splitting them for ownership and adding the three meta features you picked) that named specialist subagents build. **No game code is written in this session.** After approval I only write the design, the agent definitions and the task briefs into the repo (last section).

## Decisions

Locked by your answers:

| Topic | Decision | What it means |
|---|---|---|
| Fly brain | **Baked from the real connectome** | Python trains one fly per type offline and exports decision tables plus brain recordings. The Roblox game runs alone: no server, no HTTP. A live bridge can be added later behind the same interface. |
| Up & down | **Floors + debt spiral** | Clear the debt -> go up a floor (new creditor, bigger debt, tougher flies). Debt balloons -> dragged into the **Basement** zone (harsher flies, pays more) until you climb out. |
| Interest | **Hybrid clock** | Random interest roll after every duel, plus a slow drip only while idle in the Hall. Time is frozen during a duel. |
| Ship target | **Public Roblox, policy-safe** | No wagers, nothing staked or lost on chance, no Robux-to-cash. Bug-zapper skin, not a gun. |
| Look and feel | **Your reference screenshots** | A shared Hall lobby with octagonal tables and Quickplay; each duel in a private brick back room with stage lights, a green-felt table, a charge box with lightning bolts, floating hands, typewriter captions and a turn banner (section 7). |
| Seating | **Solo now, 2-4 seats later** | The MVP is one player vs the fly. Contracts and the rules engine take a list of 2-4 seats from day one, so a shared table can ship later without a rewrite. |
| Meta features | **Levels, XP and titles; daily quests and codes; cosmetic store and inventory** | Rewards are XP and Buzz, a cosmetic-only currency that never touches the debt. Trading waits until after launch (section 7b). |
| Table weapon | **Zap racket** | An electric fly-swatter racket loaded with glowing charged or dud cells. It fills the shotgun's spot and its lightning-bolt charge box from your reference. |

Assumptions I made (tell me if any is wrong):

1. Code lives in this repo under `roblox/` (Rojo project). Cloud agents cannot run Roblox Studio, so the asset agents generate files (models via Lune, data-driven animation and VFX, synthesized audio) and you do the Studio imports and uploads. A human artist can replace any asset later because the asset contract keeps replacements drop-in.
2. One player per duel, in a private back room; everyone shares the **Hall** lobby, and friends can watch a duel from there.
3. A **duel** is one match to zero lives (3 vs 3). The player moves first on Floor 1.
4. Six flies: Rookie, Panic (terrified), Cheetah (fast), Pro, Cheater, Collector (boss). I read "cheetah" and "cheater" as two different flies and kept both.
5. Dying = blackout and revival at the Infirmary. Debt persists (one loss must not erase an hour of progress). Interest still rolls, the payout is missed.
6. MVP = Floor 1 + Basement, 5 items, all 6 flies. Floors 2-4, 4 more items and the Queen boss are post-MVP.
7. Every number below is a starting guess; the balance sim (T50) tunes it.
8. "Test on your glove" replaces "shoot yourself" (placeholder wording).
9. You get one extra interest roll if you return after 12+ hours away (at most one per 24 h). Remove it if you'd rather not punish returning players.
10. QA and playtesting share one agent, and telemetry shares one with live-ops. With Ines added for the meta features the roster is 31 specialists plus the Lead (section 9.3 shows every merge).
11. Every agent has a human first name, which you can change. Its slug is `name-role` (for example `remy-rules`), so "spawn Remy" is unambiguous.
12. Your reference shows 5 bolts per player. The fly game keeps your 3 lives, so its charge box shows 3 bolts per side.

## 1. The game on one page

**Premise.** You owe the Shark $1,000,000. His champion is a fly. Beat it, get paid, clear the debt, before the interest eats you.

**Pillars.** (1) Buckshot tension: hidden information, odds, reading your opponent. (2) Every fly is a real recorded connectome brain; you can watch it think and get scared. (3) The debt clock always ticks but never during a decision. (4) Policy-safe by construction. (5) A pure, testable core so agents can build in parallel.

**Loops.** Turn (10-30 s) -> Duel (3-6 min) -> Night (30-90 min) -> Climb (days).

**Glossary.** *Cell* = one chamber slot, *charged* (live) or *dud* (blank). *Load* = one fill of the chamber. *Hall* = the shared lobby. *Back room* = the private room where one duel is played. *Charge box* = the display of both sides' lives as lightning bolts. *Shark* = creditor NPC on the phone. *Hall of Freedom* = leaderboard of players who cleared a floor (fastest, highest). *Buzz* = cosmetic currency. *FlyPack* = a baked fly brain.

**Gameplay phases (server state machine per table):**

```
HALL (drip ticks; quests, store, wall boards) --Quickplay or sit at a Hall table--> ROOM (camera moves into a free back room, first-person)
ROOM --> REQUEST: server draws floor/zone + fly (Director) --> DOSSIER (Shark's file flips to reveal the fly)
DOSSIER --> LOAD n: announce "3 charged / 3 dud", deal items (from load 2)
LOAD n --> TURN(player) <-> TURN(fly): items* then fire(target) --> RESOLVE
RESOLVE: chamber empty --> LOAD n+1     RESOLVE: someone at 0 lives --> VERDICT
VERDICT: win = fly KO'd | loss = blackout --> SETTLE
SETTLE (phone call): interest roll -> payout -> floor/zone checks --> (Freed: elevator offer | Foreclosed: Basement drop)
      -> XP, Buzz, quest progress and titles update --> HALL (back through the door)
```

## 2. Duel rules (`zapper_v1`)

Engine uses neutral ids (`charged`/`dud`, `fire(target)`); the skin is data. A match holds an ordered list of 2-4 seats and `target` names a seat; the MVP ruleset uses two seats (you and the fly). With more seats, turns go clockwise and targeted items (Web, later Espresso) name a seat.

| Rule | Default |
|---|---|
| Lives ("charges") | 3 each, max 3 |
| Load | 2-8 cells, balanced (even total = equal charged/dud, odd = differ by one), order hidden and uniformly random, counts announced |
| Turn | Use any items, then **Zap the Fly** or **Test on your glove** (self) |
| Charged cell | target loses 1 life (2 with Overcharge); turn passes |
| Dud on the fly | nothing; turn passes |
| Dud on self | nothing; **you keep the turn** |
| Charged on self | lose 1 life; turn passes |
| First mover per load | player on F1; alternate/coin-flip on higher floors (config) |
| Reload | when the chamber empties; lives persist |
| Items | none in load 1; 2-4 per side from load 2; 6 slots |
| End | a side at 0 lives loses; no draws |
| Turn timer | 60 s, shown as "EVOKE'S TURN 59" like your reference (Cheetah: 15 s); timeout = auto Zap the Fly |

MVP items: **Magnifier** (peek at current cell), **Vent** (eject current cell, reveal it), **Sugar** (+1 life), **Web** (opponent skips next turn), **Overcharge** (next charged cell does 2). Post-MVP: Burner phone (reveal a later cell), Inverter (flip current cell), Espresso (steal an item and use it), Rotten fruit (50% +2 lives, 50% -1). Mechanics are inspired by Buckshot Roulette; names, art and audio must be original.

## 3. Debt and economy

**Ledger state:** `{floor, zone: normal|basement, debt, lossRun, hiRun, lastSeen, lastAwayRoll}`.

**Settle (server, atomic, after every duel):**
1. `rate = rollInterest(floor, zone)` from the Shark's-mood table. Pity guard: after 2 Hungry/Spike rolls in a row, the next comes from Calm/Normal.
2. `debt = min(3 x opening, round(debt x (1 + rate)))`.
3. On a win: `debt -= payout`, where `payout = basePayout[floor] x flyMult x livesBonus[livesLeft] x zoneMult`.
4. Transitions: `debt <= 0` -> **Freed** (ascend offer or cash out to the Hall of Freedom). `debt >= 1.5 x opening` -> **Basement**. In the Basement, `debt <= 1.15 x opening` -> back to normal.
5. One DataStore write, then push `Ledger` and `Notice` events.

**Starting numbers (Floor 1 "Intake", opening $1,000,000):**

| Item | Value |
|---|---|
| Shark's mood (per duel) | Calm 1.0-2.5% (w35), Normal 2.5-4.5% (w35), Hungry 4.5-7.5% (w22), Spike 7.5-12% (w8); mean about 3.9%. Basement adds +1.5 points |
| Lobby drip | 0.08% per 30 s idle in the Hall; paused in duels, menus, cutscenes |
| Away roll | one roll if away 12 h or more, at most one per 24 h |
| Base payout | $100,000 |
| Fly multiplier | Rookie 0.8, Panic 1.1, Cheetah 1.3, Pro 1.6, Cheater 2.0, Collector 3.0 |
| Lives bonus (lives left 1/2/3) | 1.00 / 1.15 / 1.30 |
| Basement | payout x1.5, harder fly weights, Sugar not dealt |
| Later floors | F2 Lounge $5M, F3 Penthouse $25M, F4 Roof $125M (Queen); payouts scale with the opening debt |

**Death and pressure.** Death = blackout -> Infirmary (skippable 6-10 s cinematic). Debt is unchanged except the normal interest roll. Streak resets, consumed items are lost. **Mercy rule:** after 2 losses in a row the next fly is drawn from the two easiest types. Nothing is ever staked; there is no revival fee, no double-or-nothing, no cash-out gamble.

**Debt and Buzz never mix.** The debt changes only through duels and interest. Buzz (quests, level-ups, codes, duel participation) buys cosmetics only, and Robux buys cosmetics only. Nothing sold or earned outside a duel changes the debt, lives, items or odds, so there is no pay-to-win and T50's balance numbers stay valid.

**MVP dead-end guard.** With only Floor 1 shipped, *Freed* plays the credits sequence, adds a Hall of Freedom entry and a badge, then issues a new Intake loan ($1M again) until Floor 2 exists.

**First-pass simulation** (Monte Carlo, 12,000 players per skill, 200-duel cap, includes Mercy and 0.1% drip per duel):

| Player (avg win rate) | Frees Floor 1 | Duels to free (median, p10-p90) | Touches Basement within 40 duels |
|---|---|---|---|
| Skilled (0.77) | 100% | 12 (9-17) | 0% |
| Median (0.57) | 100% | 20 (13-31) | 0.2% |
| Novice (0.36) | 77% by duel 200 | 45 (25-86) | 18% (27% ever) |

**Balance targets for T50:** skilled 10-14 duels, median 16-24, novice about 45 with 15-25% visiting the Basement. Basement always escapable for a win rate of 0.4 or better. Dial for "hard mode": shift the mood table +1 point (novices then visit the Basement 41% within 40 duels).

## 4. The flies

| Fly | Stars | Personality | Brain recipe (Python) | Runtime quirk and tell | Pay |
|---|---|---|---|---|---|
| **Rookie** | 1 | Fumbles odds, wastes items | Early snapshot (~150 decisions), high exploration | eps 0.35, slow, wobbly hands | 0.8 |
| **Panic** | 2 | Fine ahead, falls apart behind | Trained with fear x2 (terrified) | Terror meter on its monitor; flinch chance ~ terror^2 (random or defensive move); sweat drops | 1.1 |
| **Cheetah** | 2 | Reckless speed | Short look (few brain steps, noisier), damage reward x1.5, self-damage x0.7 | Acts in ~0.4 s and imposes a 15 s shot clock on you; motion blur | 1.3 |
| **Pro** | 3 | Calm, near-optimal | ~6,000 decisions, fear 1.0, eps 0.03 | Full item logic, no tells | 1.6 |
| **Cheater** | 4 | Peeks and steals | Pro recipe, trained with X-ray (sees the true cell) | Peeks at ~50% of turns with a telegraphed glint and tick; swipes one item at load start | 2.0 |
| **Collector** | 5 (boss) | Top-hat debt collector | Best Pro + Cheater traits, one extra item per load | Basement only (15% draw) plus every 10th win | 3.0 |

Draw weights, Floor 1 normal: Rookie 30, Panic 22, Cheetah 22, Pro 16, Cheater 10. Basement: Rookie 5, Panic 10, Cheetah 20, Pro 30, Cheater 25, Collector 10. Guards: no fly 3 times in a row, Mercy rule above.

**Runtime AI stack (Luau, server, deterministic from a seed):**

```
FlyAgent
 |- Belief     counts, revealed cells, own peeks (built ONLY from the redacted View, never MatchState)
 |- Policy     FlyPack Q-table -> softmax(q / T) + eps exploration
 |- ItemLogic  rules per personality (dealer-style: use Sugar only when hurt, Web always, Magnifier when unsure)
 |- Fear       danger -> terror curve (baked); drives Panic flinch, monitor clip, music
 |- Quirks     Cheater peek/swipe, Cheetah speed, Rookie noise
 '- Output     {action, thinkMs, terror, confidence, clip, emote}
```

The **confidence** shown on the monitor is the real margin between the two Q-values the fly acted on, so the player can read when it is guessing.

## 5. Brain pipeline (Python on your PC -> Roblox)

```
roulette_rules.py (port of zapper_v1, golden vectors)
        |
RouletteTable(Table): table picture -> FlyEyes -> connectome (166,700) -> readout (~59k) -> Mind "roulette" (value per choice)
        |    dopamine PAM/PPL1 = prediction error, Fear circuit = danger (reuse casino.py)
Trainer (per fly: budget, reward shaping, fear, look steps) --> snapshots + eval report (vs solver)
        |
Exporter --> FlyPack (Q-table, temperature, fear curve, think times, item personality)
        |        --> roblox/src/server/Data/flypacks/<fly>.luau  (sharded, size-checked)
BrainViz baker --> ~3k-point neuron layout + activity clips --> sprite sheets (PNG) + manifest.json
                       --> uploaded once as Roblox images, played on the in-world monitor
```

**Policy state** (about 1,200 states, tiny): `(chargedLeft, cellsLeft)` exact pairs x `livesSelf` x `livesOpp` x `knownCurrent {unknown, charged, dud}`. The brain sees this as a picture (lit cell slots, life bolts, a known-cell marker), exactly like the casino's 13-slot board. Items are handled by rule-based logic, not learned.

**Reuse, do not rewrite: the roulette is one more casino game.** `Table` (`fly_jjs/core/casino.py:540`) gives every game the fly, brain time, fear, the dashboard, the gun and the jackpot; `SlotTable` (`slots.py:107`) and `RaceTable` (`race.py:113`) show how a game plugs in. `RouletteTable(Table)` in `fly_jjs/core/roulette.py` gets its own `Mind` from `CasinoFly.mind("roulette", ("opponent", "self"))` (`casino.py:375, 316`), so the fly keeps one brain and one fear circuit (`Fear`, `casino.py:224`) across all its games and `ChoiceValues` (`casino.py:291`) does the dopamine learning. It never touches the casino `Wallet`, because nothing is bet. Also reuse `FlyBody` (`brain.py:68`), `FlyEyes` (`vision.py:60`), `circuit_members` and `neuron_layout` (`dashboard.py:95, 133`), `fake_components` (`tests/fakes.py:84`) so everything is unit-testable without the 260 MB connectome, `casino_menu()` (`main.py:235`) as the template for a new `[R] Roulette` entry, and `USER_DIR` (`storage.py:6`) for snapshot paths.

**Honesty statement (also shown in the credits):** the game does not simulate neurons. A FlyPack is a distillation of a fly trained on the real connectome; monitor clips are recordings from the same connectome under matching situations. "Fear" is the activity of the threat/escape circuit in a simulation, not a claim about what a fly feels. Credit MaleCNS and `flybrain`; confirm their license terms before shipping derived data.

## 6. Roblox architecture

**Repo layout** (monorepo; Rojo). Folder names are the ownership boundaries used in section 9:

```
roblox/
  default.project.json  rokit.toml  selene.toml  stylua.toml  .luaurc  .gitignore
  src/shared/   Rules/ Solver/ Economy/ Progression/ Fly/ Net/ Config/ Content/ Util/ Perf/   <- pure Luau, NO Roblox APIs
  src/server/   Services/ Platform/ Data/{flypacks/,Codes.luau} vendor/ Main.server.luau
  src/client/   Controllers/ State/ UI/ Presentation/{Sequencer,Anim,Vfx}/ Cinematics/
                BrainMonitor/ Tutorial/ Audio/{Sfx,Music}/ Perf/ Main.client.luau
  tests/        rng/ rules/ solver/ economy/ progression/ quests/ store/ fly/ integration/{net,match,data,debt,tutorial}/ security/
                telemetry/ client/{state,ui,sequencer,cinematics,monitor,anim,vfx}/ audio/{sfx,music}/
                e2e/ support/ run.luau                                                    (Lune)
  vectors/      rng_vectors.json rules_vectors.json solver_table.json                    (shared with Python)
  tools/        archetypes.luau balance_sim.luau bots/ build/{smoke.luau,graybox,env,props,flies}/ lint/ audio/{sfx,music}/
  assets/       SPEC.md spec/ budgets.json blueprints/ models/{graybox,env,props,flies}/ animations/ vfx/ brain/ audio/{sfx,music}/
  scripts/      check.sh
fly_jjs/core/   roulette_rng.py roulette_rules.py roulette.py roulette_train.py roulette_eval.py roulette_export.py roulette_viz.py
tests/          test_roulette_*.py                                                       (Python, pytest)
docs/roblox/    README DESIGN CONTRACTS TASKS AGENTS  tasks/ ccr/ schemas/  + one doc per area (see section 9.4)
.claude/agents/ one <slug>.md per specialist (section 9.3)
```

**Architecture rules:**
- `shared/` is pure Luau (`--!strict`), so Lune can test it and run Monte Carlo sims. Deterministic RNG = **sfc32** (32-bit adds, xor, shifts only), identical in Luau and Python; Roblox's `Random` is used only at the boundary to make seeds.
- Engine is a reducer: `Engine.new(ruleset, seed)`, `Engine.legal`, `Engine.apply(state, side, action) -> state, events`, `Engine.view(state, viewer)` (redacted).
- Services get Roblox dependencies as constructor arguments (`platform = {now, net, datastore, players, analytics}`), so Lune tests inject fakes. Only `Main.*.luau` and `Platform/` call `game:GetService`.
- Config-driven content: `Config/{Balance,Floors,Flies,Items,Rulesets}.luau`; writing and catalogs live in `Content/{Lore,Dialogue,Strings,Tutorial,Cinematics,Credits,Quests,Catalog}.luau` as plain data. Redeem codes live server-side only, in `server/Data/Codes.luau`.
- Vendor single-file third-party modules (ProfileStore) with pinned version and license.

**Server services:** `MatchService` (one duel runner per back room), `TableService` (Hall tables, back-room pool, Quickplay, watchers), `DirectorService` (floor/zone/fly draw), `DataService` (ProfileStore, migrations, autosave), `DebtService` (settle, drip, away roll, transitions), `LobbyService` (Hall wall boards, leaderboards), `ProgressionService` (XP, levels, titles, rank badge, Buzz wallet), `QuestService` (daily quests, codes), `StoreService` (catalog, purchases, inventory, equip), `Guard` (validation, rate limits), `Telemetry`, `TutorialService`.

**Network** (server-authoritative; clients only send intents):

| Remote | Dir | Payload sketch |
|---|---|---|
| `Intent` | C->S | `{seq, kind (fire, item or ready), target?, slot?}` |
| `Event` | S->C | `{seq, matchId, ev}`: public events, or private ones addressed to one viewer |
| `Snapshot` | S->C | redacted `View` for resync/spectators joining |
| `Ledger` | S->C | `{debt, floor, zone, rate?, delta, reason}` |
| `Notice` | S->C | `{code, args}` (forfeit, mercy, timeout, errors) |
| `MetaIntent` | C->S | `{seq, kind (quickplay, sit, watch, leave, claim, redeem, buy, equip), arg?}` |
| `Meta` | S->C | `{xp, level, buzz, titles, rank, quests, owned, equipped}` (only the parts that changed) |

Duel events: `LoadStarted{charged,dud}`, `ItemsDealt`, `TurnStarted`, `ItemUsed`, `Fired{shooter,target,result,damage}`, `LivesChanged`, `TurnSkipped`, `FlyThinking{clip,terror,confidence,ms}`, `MatchEnded{winner}`. T01 freezes the exact types and the shared **cue catalog** (event -> animation, VFX, SFX and music cue ids) that the presentation agents build against.

**PlayerData v1** (ProfileStore, session-locked, versioned migrations): `{v, debt, floor, zone, duelsWon, duelsLost, lossRun, hiRun, lastSeen, lastAwayRoll, freedCount, bestFloor, seenFlies, tutorialDone, settings, xp, level, buzz, titles, equippedTitle, rageQuitUntil, quests{day, ids, progress, claimed}, redeemedCodes, owned, equipped, receipts}`. The meta fields are in v1 from the start, so the meta features need no migration.

**Security:** validate seat, turn, legality and rate on every intent; chamber order and RNG state never leave the server; a Magnifier reveal is a private event to its owner only; FlyPacks live in `ServerStorage` (not replicated); all money math is server-side; leaving mid-duel = forfeit (loss) plus the RAGE QUITTER title for 10 minutes, but a server shutdown restores the duel instead of punishing. XP, Buzz, quest progress and titles are granted only by the server from match events; Robux purchases go through `ProcessReceipt`, recorded by receipt id in the profile so a receipt is granted once; redeem codes never reach the client.

**Hall and back rooms:** the Hall has octagonal tables, wall boards and Quickplay. Sitting at a Hall table or pressing Quickplay gives you a back room: a copy of the room template placed in a far-off part of the same server (no teleport). A room holds 4 seats (1 used in the MVP), the fly's chair, the charge box, the Brain Monitor and the cell tray. The pool has one room per server player slot. The server runs the authoritative state and publishes public stats (lives, cells fired, items used) as attributes that feed the Hall wall boards. The seated client and any watchers run the full presentation from the event stream; watching moves only the camera, never the character.

**Toolchain:** Rojo, Lune (tests, sims, and headless `.rbxm` model building through Lune's Roblox library), StyLua, Selene, `luau-lsp` analyze. In this cloud sandbox GitHub releases return 403, so Rokit/Aftman downloads fail; crates.io index, npm, PyPI and raw.githubusercontent.com work, so use `cargo install lune stylua selene rojo --locked` here and Rokit locally/CI. T00 must prove both: the tools build, and a `.rbxm` can be written and read back (the asset agents depend on it). Python: `python -m pytest` with `FakeBrain`.

## 7. Look and feel (from your reference screenshots)

Your four screenshots are the reference. Each element maps to the fly game as below; the owners are the agents in section 9.3.

**The Hall (shared lobby, third person)**

| In your reference | In the fly game | Owners |
|---|---|---|
| Dim concrete hall, pillars, octagonal green-felt tables | The Shark's Hall. Sitting at a table, or pressing Quickplay, takes you to your back room | Leo, Mara, Otto |
| Chalkboard wall boards: LIVE SHELLS / BLANK SHELLS / UTILITIES USED per seat | Wall boards for each running duel (player, fly, bolts left, charged and dud cells fired, items used), plus the Shark's Board (lowest debts) and the Hall of Freedom | Uma, Elena |
| CHAMPION and RAGE QUITTER titles over heads | Same: earned titles, and RAGE QUITTER for 10 minutes after leaving a duel | Ines, Uma, Nora, Tessa |
| UNRANKED badge with a bar, top centre | Rank badge = your floor (FLOOR 1 · INTAKE); the bar is the share of the opening debt repaid | Ines, Uma |
| Inventory, Trade, Store, Invite Friends buttons on the left | Inventory, Store, Invite Friends (Trade after launch) | Uma, Ines |
| Daily Quests panel with 3 quests and rewards | Same; rewards are XP and Buzz | Omar, Uma |
| QUICKPLAY and the money counter, bottom centre | QUICKPLAY, the debt counter (red) and the Buzz counter | Uma, Mateo |
| Level 1 and an XP bar, bottom left | Same | Ines, Uma |
| Redeem Codes button | Same | Omar, Uma |
| Pixel-font UI, chunky coloured buttons | Same style: a pixel font (Press Start 2P or Arcade) for UI and a monospace font for captions; colour-blind-safe pairs; contrast at least 4.5:1 | Uma, Lex |

**The back room (first person, where the duel happens)**

| In your reference | In the fly game | Owners |
|---|---|---|
| Brick walls, cables, two hanging stage lights | Same; the lights flicker on every zap and turn red in the Basement | Leo, Mara, Otto, Zara |
| Green felt with white lines (centre circle, boxes) | Same markings: the racket rests in the centre circle, items sit in each side's box, and the cell tray on the halfway line shows each load | Leo, Otto |
| Masked dealer with bat wings across the table | The fly as the dealer: human-sized, glowing compound eyes, fly wings, a costume per type (Rookie cap, Panic sweat, Cheetah goggles, Pro suit, Cheater visor, Collector top hat) | Rigo, Nora |
| Floating white hands holding the gun | Your floating white gloves; the fly's floating black bristly forelegs | Rigo, Anika |
| Shotgun in the middle | The zap racket (an electric fly-swatter racket) | Otto, Anika, Zara, Wren |
| Shells on the table | Glowing charged cells (yellow) and grey duds on the cell tray, then loaded | Otto, Zara |
| Charge box "EVOKE / CHARLES" with lightning bolts | Charge box "EVOKE / <fly name>" with 3 bolts each; a lost charge flickers out | Otto, Uma, Zara |
| Dot-matrix box on the right | The Brain Monitor CRT, in the same spot | Vera |
| Stack of papers | The Shark's loan contract: first-time players sign it in the intro, which is where the $1,000,000 debt comes from | Camila, Nora, Toby |
| Caption box: "THE SHELLS ENTER", "ROUND 1" | Typewriter captions: "THE CELLS ENTER", "LOAD 2", "THE SHARK IS CALLING"; they double as subtitles | Dalia, Theo, Uma |
| "CHARLES'S TURN 59" at the top | "ROOKIE'S TURN 59" and "YOUR TURN 59" | Uma, Theo |

- **Camera and controls:** third person in the Hall; first person and seated in the back room, with a short look-around and three focus points (the fly, the table, the Brain Monitor). Mouse and keyboard, touch and gamepad from day one (Kiran).
- **HUD in the back room:** turn banner and timer at the top, caption box at the bottom, item bar, and the Shark's call popup with the rolled rate. The charge box and the cell tray are in-world, so the screen stays clear, like the reference. Charged and dud icons are colour-blind-safe; a reduced-flash option exists.
- **Beat of a turn:** the gloves pick up the racket -> charge whine -> choice -> arc flash (charged) or fizzle (dud) -> a bolt flickers out -> reaction. Heartbeat and music layers follow lives and terror.
- **Brain Monitor (signature feature):** in-world CRT on the right of the table, showing the fly's 3D brain. MVP plays pre-rendered sprite-sheet clips chosen by (situation, terror, confidence): idle, think, fear low/high, dopamine reward/punish, looming (zapper approaches), escape. On defeat the brain goes grey and silent (as in the casino). Texture budget about 40 MB. Upgrade path: draw live from baked spike rasters with `EditableImage` (check availability).
- **Assets and writing** (owners in section 9): the Hall, the back-room template and its Basement variant, octagonal tables, wall boards, stage lights, charge box, cell tray, zap racket and its skins, cells, 9 items, loan papers, phone, elevator, infirmary; 6 fly rigs with costumes and floating forelegs, floating gloves and their skins, with idle/think/zap/hurt/KO/celebrate/tell animations; VFX presets; original SFX (buzz loops, zap, fizzle, item sounds, light hum, typewriter ticks, phone, elevator, heartbeat) and 3 music layers; lore, dialogue, captions, UI copy, tutorial and cutscenes. Cloud agents produce them as files (stylized primitive models and rigs via Lune, animation and VFX as data plus procedural players, audio synthesized in Python to OGG) and linters enforce the asset contract. You import and upload (human gates H1-H3). Death and KO are cartoon (blackout, stars), never gore. Flashing follows the WCAG limit of 3 flashes per second, with a reduced-flash setting.

## 7b. Meta features (levels, quests, store)

- **XP and levels (Ines, T60):** XP for every duel, more for a win, with bonuses for bolts left and the fly's difficulty. Each level rewards Buzz, and some levels unlock a cosmetic or a title.
- **Titles (Ines, T60; names by Nora and Tessa):** shown over your head in the Hall. Earned examples: DEBT FREE (freed a floor), CHAMPION (5 wins in a row), FLY WHISPERER (beat all six flies), BASEMENT DWELLER (10 duels in the Basement), COLLECTOR'S BANE (beat the Collector). RAGE QUITTER is applied for 10 minutes after leaving a duel. You pick which earned title to show.
- **Rank badge (Ines, T60):** your floor plus a bar for how much of the opening debt you have repaid; red while you are in the Basement.
- **Daily quests (Omar, T61):** 3 a day from a pool of 20 or more, such as "Use 3 Magnifiers", "Beat a Cheetah", "Win with 3 bolts left" or "Test on your glove twice". They reset at 00:00 UTC and reward XP and Buzz when claimed in the panel. Weekly quests can come later.
- **Redeem codes (Omar, T61):** a server-side list; each code works once per player, can expire, rewards Buzz or a cosmetic, and never needs a purchase.
- **Store and inventory (Ines, T62; skins by Otto, Rigo and Mara):** racket skins, glove skins, felt colours for your back room and title plates. Fixed prices in Buzz, a few premium items for Robux. No random boxes, no Buzz packs in the MVP, and nothing that changes debt, lives, items or odds (section 3). Equipped items show in your back room and to watchers.
- **Starting Buzz targets (T62 tunes them):** about 150 Buzz per hour for a median player (a few Buzz per duel, 50-100 per quest, 100 per level-up); common skins 300-800 Buzz, rare ones 1,500-3,000.
- **Trading:** after launch. Ines would own it with Sasha reviewing, once the store's ownership records have held up in live play.

## 8. Compliance and risks

| Risk | Mitigation |
|---|---|
| **Gambling policy.** Roblox docs: experiences "cannot contain playable gambling content, including simulated gambling"; gambling = exchanging Robux, real money or in-experience items of value for a game of chance. The docs state no age or label exception. | No wager, stake, forfeiture on chance, double-or-nothing, loot box or Robux-to-cash path. Payouts are fixed by fly and lives left. Answer the Maturity questionnaire truthfully; no playable casino props. Re-read the live policy in T52a-1 (early) and T52a-2 (audit). |
| **Self-harm / gun imagery** (Buckshot's core act) | Zapper skin, "test on your glove", charges not health, cartoon blackout. Skin is data: swap to another prop if flagged. Verify current Community Standards in T52a-1. |
| Python and Luau rules drift | Shared golden vectors and RNG vectors run by both suites (T02, T10, T20); the spec, not either implementation, is the truth. |
| Real-brain training is slow | Runs on your PC (H2); `--quick` FakeBrain mode for CI; snapshots resume. |
| Roblox script/string size limits | Shard FlyPacks (target under 100 KB each) and verify limits in T23. |
| Cloud agents cannot run Studio | Asset agents emit files and linters enforce the contract (T44a). Expect stylized primitives and a human polish pass. If the T00 smoke test shows Lune cannot write `.rbxm`, fall back to Studio-run Luau build scripts checked by the same lints. |
| Balance | Sim first (T50), telemetry later (T33b); numbers live in config. |
| Licensing and attribution | MaleCNS and `flybrain` credits in-game (T52a-2); original names, art and audio, not Buckshot's. |
| Exploits | Server-authoritative, intent-only clients, redaction tests, rate limits (T33a). |
| Store purchases granted twice or lost | `ProcessReceipt` records each receipt id in the profile before confirming; Buzz spends are atomic; T62's gate tests duplicates and failed saves (Sasha reviews). |
| Paid random items or pay-to-win | Fixed prices only, no random boxes, Robux and Buzz never touch debt, lives, items or odds (sections 3 and 7b); Lex audits in T52a-2. |
| Copying the reference game | Borrow the genre's staging only (brick room, lights, charge box, captions). Every name, model, sound and piece of UI art is original; nothing is taken from the reference Roblox game or from Buckshot Roulette (Lex checks in T52a-2). |
| Back rooms cost memory | One room per player slot, built from one template; Petra sets per-room budgets in T52b-1 and measures them in T52b-2. |
| Agent collisions | Path ownership (9.4 and 9.6), one worktree and branch per work item, change requests for anything outside your paths. |
| Too much parallelism | Wave 3 has 15 ready items; run 6-8 at a time, critical path first (9.7). |
| Custom subagents not loaded in a running session | Restart the session or check `/agents`; fall back to `general-purpose` with the agent file pasted in. |

## 9. Work plan: specialist agents

### 9.1 Operating model

- **The Lead (A00 Priya, Project Architect) is the main Claude Code session.** The Lead never writes product code. It reads `docs/roblox/TASKS.md`, spawns the primary agent of every ready work item (manifest in 9.7), checks the handoff gate (9.5), merges, and starts the next wave.
- **31 specialists (A01-A31)**, each with a human first name, are defined as project subagents in `.claude/agents/<slug>.md` (frontmatter `name`, `description`, `tools`; body = role, owned paths, rules, definition of done, handoff report). The slug is `name-role` (for example `remy-rules`) and is the `subagent_type` to spawn, so "spawn Remy for T10" means `subagent_type = remy-rules`. Confirm the file format with `/agents` after restarting the session.
- **Spawn recipe:** `subagent_type = <slug>`, `isolation = "worktree"`, run in the background, prompt = `Do <ID> exactly as written in docs/roblox/tasks/<ID>-<title>.md`. Follow-ups, fixes and later tasks for the same specialist go through SendMessage so it keeps its context.
- **Paste-ready instruction for the main session:** `Read docs/roblox/README.md and docs/roblox/TASKS.md. Execute Wave <n>: for every work item listed, spawn its primary specialist as described in 9.1, in the background. When they finish, run the handoff gates in TASKS.md, merge passing PRs into the integration branch, and stop at the wave gate.`
- **One branch and one PR per work item** (`claude/fr-<ID>-<slug>` into the integration branch). Supporting agents do not edit the primary's paths: they review the PR (comment sign-off) or answer questions through the Lead.
- **Ownership is by path.** Anything an agent needs changed outside its paths goes through a change request `docs/roblox/ccr/CCR-<n>.md` (who, what, why, impacted tasks). The Lead rules; the owner applies it.
- **Handoff report** (required in every PR description): task and agent; files changed (all inside owned paths); each acceptance check as command -> result; open risks; next consumers.
- **Concurrency:** up to 15 items are ready at once. Run 6-8 at a time, critical-path items first: `T00 > T01 > T10 > T12 > T30a > T33a > T52a-2 > T53` (and `> T51`).

### 9.2 What changed from the 27-task list

| v0.1 task | Now | Why |
|---|---|---|
| T00-T02, T10-T13, T20, T21, T23, T24, T31, T32, T40, T41, T43, T46, T50, T51, T53 | same IDs and scope | unchanged |
| T22 | T22a Trainer and bake run, T22b Brain evaluation | training and evaluation are different specialties |
| T30 | T30a Match/Table/Director, T30b Networking runtime, T30c Server bootstrap and platform | the net runtime and the boot layer had no owner |
| T33 | T33a Security, T33b Telemetry | different specialties |
| T42 | T42a Sequencer, T42b Cinematics | cutscene content is its own craft |
| T44 | T44a Asset contract, T44b Graybox build | contract versus build |
| T45 | T45a-T45h: map design, environment build, props, fly rigs, animation, VFX, SFX, music | too broad for one owner |
| T52 | T52a-1/-2 Compliance and accessibility, T52b-1/-2 Performance | separate specialties; -1 is an early requirements memo, -2 the final audit |
| new | T47 Narrative bible, T48 Dialogue and barks, T49 UI copy | required specialists had no task |
| new (v0.3) | T60 Progression core, T61 Daily quests and codes, T62 Cosmetic store and inventory | the meta features you picked from your reference |
| T01, T10, T30a, T41, T44a, T45a-d | same IDs, wider scope | 2-4 seat contracts and engine, the Hall and back rooms, the reference look (section 7) |

Dependencies: split tasks inherit their parent's. The only edits to existing edges are (a) T43 starts from T01 and T40 with placeholder clips and takes the final clips from T24 (v0.1 already said "placeholders first"), and (b) edges added by the new tasks, all visible in the table below.

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

### 9.4 Assignment table: every work item, one primary agent

**Legend.** Paths: `R/` = `roblox/`, `S/` = `roblox/src/shared/`, `SV/` = `roblox/src/server/`, `CL/` = `roblox/src/client/`, `PY/` = `fly_jjs/core/`, `PT/` = `tests/`, `D/` = `docs/roblox/`. Where: **C** cloud agent builds and verifies, **PC** needs your machine (real connectome), **ST** needs a Roblox Studio step (human). Size S/M/L. Each row is written as (Where; Size). `-1`/`-2` rows of one task share an owner.

| Task | Primary Agent | Supporting Agents | Owns | Depends On | Deliverable |
|---|---|---|---|---|---|
| **T00** Toolchain and scaffold (C; S) | A01 Cora | A27 Quinn (CI expectations) | R/default.project.json, R/*.toml, R/.luaurc, R/.gitignore, R/scripts/, R/tests/run.luau, R/README.md, R/tools/build/smoke.luau, .github/workflows/roblox-ci.yml | none | Rojo skeleton; `check.sh` (StyLua, Selene, Lune tests, every lint in R/tools/lint/, `rojo build`); cloud (cargo) and local (Rokit) install notes; CI; Lune `.rbxm` write-and-read smoke test |
| **T01** Contracts and schemas (C; M) | A01 Cora | A02 Remy, A03 Elena, A04 Felix, A06 Bea, A09 Mateo (each reviews the types they consume) | S/Types.luau, S/Net/Protocol.luau, D/CONTRACTS.md, D/schemas/ | T00 (A01) | Frozen types for 2-4 seats (Ruleset, Seat, Action, DuelEvent, View, Ledger, FlyPack, PlayerData v1 with the meta fields, Platform, the 7 remotes incl. MetaIntent and Meta), cue/caption/dialogue/string/notice/title/quest-event key catalogs, JSON schemas with fixtures, tag `contracts-v1` |
| **T02** Deterministic RNG (C; S) | A02 Remy | A06 Bea (Python user), A03 Elena (Luau user) | S/Util/Rng.luau, PY/roulette_rng.py, R/vectors/rng_vectors.json, R/tests/rng/, PT/test_roulette_rng.py | T00 (A01) | sfc32 with unbiased nextInt, nextFloat, shuffle, fork; identical outputs in Luau and Python; vectors for 20+ seeds |
| **T10** Rules engine (C; L) | A02 Remy | A05 Soren (API), A06 Bea (vector consumer), A04 Felix (View consumer) | S/Rules/, S/Config/Items.luau, S/Config/Rulesets.luau, R/tests/rules/, R/vectors/rules_vectors.json | T01 (A01), T02 (A02) | zapper_v1 reducer for 2-4 seats (the MVP ruleset uses 2): loads, turns, 5 MVP items, redacted views, events, replay, scripted-chamber hook for the tutorial; vectors merged first |
| **T11** Economy core (C; M) | A03 Elena | A05 Soren (targets), A30 Omar (KPI needs) | S/Economy/, S/Config/Balance.luau, S/Config/Floors.luau, R/tests/economy/ | T01 (A01), T02 (A02) | Ledger.settle, drip, awayRoll, floor and zone transitions, mood table, payouts, caps, pity and Mercy state; config-driven |
| **T12** Fly AI runtime (C; L) | A04 Felix | A05 Soren (archetypes), A06 Bea (pack semantics), A07 Pax (loader and schema), A02 Remy (View) | S/Fly/, S/Config/Flies.luau, SV/Data/flypacks/fallback.luau, R/tests/fly/ | T01 (A01), T10 (A02) | FlyAgent (Belief, Policy, ItemLogic, Fear, Quirks), Director.pick, pack loader, heuristic fallback pack |
| **T13** Solver and archetypes (C; M) | A05 Soren | A02 Remy (API), A06 Bea (consumes the table) | S/Solver/, R/tools/archetypes.luau, R/vectors/solver_table.json, R/tests/solver/ | T10 (A02) | Exact optimal policy and value table for item-less states; player archetypes (novice, median, skilled, optimal) calibrated to average win rates 0.36, 0.57, 0.77 against the fallback pack |
| **T20** Python rules port (C; M) | A06 Bea | A02 Remy (spec questions) | PY/roulette_rules.py, PT/test_roulette_rules.py | T01 (A01), T02 (A02) | Independent Python implementation of zapper_v1 (2 seats, which is all training needs) on `roulette_rng`; must pass the 2-seat shared vectors at the M1 gate |
| **T21** RouletteTable (C; L) | A06 Bea | A08 Vera (activity hooks), A07 Pax (readout access), A05 Soren (metrics) | PY/roulette.py, PT/test_roulette_fly.py | T20 (A06) | `RouletteTable(Table)` in the casino's game pattern (section 5): the table picture, a `roulette` Mind on the shared `CasinoFly` (opponent/self values), fear and dopamine through `Table`, no wallet or bets, save/load in the casino memory, FakeBrain tests |
| **T22a** Trainer and bake run (C+PC; L) | A06 Bea | A05 Soren (grading), A07 Pax, A00 Priya (schedules the PC run) | PY/roulette_train.py, PT/test_roulette_train.py, main.py (the [R] menu entry only), D/BRAIN_PIPELINE.md, D/bake_logs/ | T21 (A06), T13 (A05) | Trainer for the six recipes with `--quick` FakeBrain mode and resumable snapshots (kept out of git); `[R]` menu; documented PC bake with logs (seed, git sha, snapshot hashes) |
| **T22b** Brain evaluation (C+PC; M) | A05 Soren | A06 Bea, A04 Felix (recipe expectations) | PY/roulette_eval.py, PT/test_roulette_eval.py, D/BRAIN_EVAL_REPORT.md | T22a (A06), T13 (A05) | Eval harness (agreement with the solver, win rate vs archetypes, decision entropy, fear response) with per-recipe pass bands, plus the report on real snapshots |
| **T23** FlyPack exporter (C+PC; M) | A07 Pax | A06 Bea (snapshots), A04 Felix (loader), A29 Lex (attribution metadata) | PY/roulette_export.py, PT/test_roulette_export.py, SV/Data/flypacks/{rookie,panic,cheetah,pro,cheater,collector}.luau (generated) | T01 (A01), T21 (A06) | Q-tables, temperature, fear curve, think times, item personality -> schema-valid sharded Luau packs with provenance; a real export runs only after that fly passes T22b |
| **T24** Brain-viz baker (C+PC; L) | A08 Vera | A06 Bea (activity hooks), A28 Petra (texture budget), A29 Lex (attribution) | PY/roulette_viz.py, PT/test_roulette_viz.py, R/assets/brain/, D/BRAIN_VIZ.md | T01 (A01), T21 (A06) | About 3k-point neuron layout (fear circuit included), situation clips, sprite sheets, manifest with asset-id placeholders, upload notes |
| **T30a** Match, Table and Director services (C; L) | A09 Mateo | A04 Felix, A02 Remy, A26 Toby (forced-chamber hook), A10 Sasha, A12 Uma (wall-board data), A28 Petra (room pool) | SV/Services/MatchService.luau, SV/Services/TableService.luau, SV/Services/DirectorService.luau, R/tests/integration/match/ | T01 (A01), T10 (A02), T12 (A04), T30b (A09), T30c (A09) | Server-authoritative duel runner (60 s turn timer, forfeit, watchers, event log); back-room pool (copy the template per duel, seat the player, return to the Hall); Hall table seating and Quickplay; public room stats for the Hall wall boards; fly draw |
| **T30b** Networking runtime (C; M) | A09 Mateo | A10 Sasha (validation hooks), A11 Kiran (client half) | S/Net/Server.luau, S/Net/Client.luau, R/tests/integration/net/ | T01 (A01), T30c (A09) | Remotes built from Protocol; sequence numbers, dedupe, snapshot resync, per-viewer filtering, spectator subscription |
| **T30c** Server bootstrap and platform (C; M) | A09 Mateo | A01 Cora (Platform type), A10 Sasha | SV/Main.server.luau, SV/Platform/, R/tests/support/ | T00 (A01), T01 (A01) | Boot order, real Roblox adapters behind the platform interface, BindToClose restore, Roblox fakes for Lune (remotes, datastore, players, clock) |
| **T31** DataService (C; M) | A03 Elena | A09 Mateo (adapter), A10 Sasha (validation), A30 Omar (retention fields) | SV/Services/DataService.luau, SV/vendor/, R/tests/integration/data/ | T01 (A01), T11 (A03) | Session-locked ProfileStore with PlayerData v1, migrations, autosave, retry, Studio mock |
| **T32** Debt and Lobby services (C; M) | A03 Elena | A09 Mateo (Ledger and Notice events), A24 Dalia (Shark call ids), A30 Omar | SV/Services/DebtService.luau, SV/Services/LobbyService.luau, R/tests/integration/debt/ | T11 (A03), T31 (A03) | Settle -> persist -> events, drip with pause rules, away roll, floor and zone transitions; leaderboards and the Hall wall-board feed (Shark's Board, Hall of Freedom, live rooms) |
| **T33a** Security and anti-exploit (C; M) | A10 Sasha | A09 Mateo (net hooks), A27 Quinn | SV/Services/Guard.luau, R/tests/security/, D/SECURITY.md | T30a (A09), T30b (A09) | Intent validation, rate limits, replay and duplicate protection, private-event leak tests, threat model, adversarial suite |
| **T33b** Telemetry (C; S) | A30 Omar | A03 Elena (ledger events), A10 Sasha (privacy), A29 Lex (data minimization) | SV/Services/Telemetry.luau, R/tests/telemetry/, D/TELEMETRY.md | T30a (A09) | KPI event schema and emitters (funnel, duel outcomes per fly, debt curve, spiral rate, quest completion, store views and purchases), volume estimate |
| **T40** Client core (C+ST; M) | A11 Kiran | A09 Mateo (client Net), A12 Uma, A29 Lex (input and accessibility) | CL/Controllers/, CL/State/, CL/Main.client.luau, R/tests/client/state/ | T01 (A01) | Hall third-person and back-room first-person cameras with transitions and focus points, the watch camera, seat and Quickplay prompts, input (keyboard/mouse, touch, gamepad), event-fed state store |
| **T41** UI and HUD (C+ST; L) | A12 Uma | A25 Tessa (strings), A29 Lex (contrast, tap targets), A28 Petra, A31 Ines (progression and store data), A30 Omar (quests panel) | CL/UI/, R/tests/client/ui/, D/ui/ | T01 (A01), T40 (A11) | Hall HUD from section 7 (Quickplay, debt and Buzz counters, level and XP bar, rank badge, quests panel, Inventory, Store, Invite Friends, Redeem Codes), overhead title tags, Hall wall boards, back-room HUD (turn banner and timer, caption box, item bar, Shark popup), charge-box display, store, inventory, elevator, settings and credits screens; pixel-font style; view-model tests |
| **T42a** Presentation sequencer (C+ST; L) | A13 Theo | A19 Anika, A20 Zara, A21 Wren, A22 Mika, A14 Camila | CL/Presentation/Sequencer/, R/tests/client/sequencer/ | T01 (A01), T40 (A11), T44a (A01) | Event -> timeline sequencer over the cue catalog, fly state machine and tells, caption track and turn-banner cues, skip and fast-forward, audio cue bus |
| **T42b** Cinematics (C+ST; M) | A14 Camila | A23 Nora, A24 Dalia, A15 Leo (camera anchors), A22 Mika, A19 Anika | CL/Cinematics/, S/Content/Cinematics.luau, D/cinematics/, R/tests/client/cinematics/ | T42a (A13), T44a (A01), T47 (A23) | Storyboards, timeline data and player: the Signing (first-join loan contract), Hall-to-back-room entry and return, dossier flip, Shark call, elevator, Basement drop, blackout and revival, fly KO, Freed credits |
| **T43** Brain Monitor (C+ST; M) | A08 Vera | A13 Theo, A04 Felix (terror and confidence), A28 Petra | CL/BrainMonitor/, R/tests/client/monitor/ | T01 (A01), T40 (A11); final clips from T24 (A08) | Sprite-sheet clip player, clip selection by situation, terror and confidence, meters, dopamine flashes, silent state; placeholder sheets until T24 |
| **T44a** Asset contract (C; M) | A01 Cora | A28 Petra (budgets); A15 Leo, A16 Mara, A17 Otto, A18 Rigo, A19 Anika, A20 Zara, A21 Wren, A22 Mika (consulted, each signs off) | R/assets/SPEC.md, R/assets/spec/ | T01 (A01) | Naming, attachments, joints, folders, budgets link, formats (models, textures, OGG audio), cue-id mapping, Hall and back-room anchors (seats, fly chair, charge box, cell tray, monitor, lights, camera), hand rigs, skin-variant rules, machine-readable lint expectations |
| **T44b** Graybox build (C+ST; M) | A16 Mara | A15 Leo, A01 Cora | R/tools/build/graybox/, R/assets/models/graybox/, R/tools/lint/env.luau | T44a (A01) | Lune script producing `graybox.rbxm` (the Hall with octagonal tables and wall-board parts, and one back-room template with all anchors and the monitor screen part) and the environment lint; opens in Studio |
| **T45a** Map and environment design (C; M) | A15 Leo | A23 Nora, A16 Mara, A14 Camila, A28 Petra, A29 Lex | R/assets/blueprints/, D/level/, R/tools/lint/blueprints.luau | T44a (A01), T47 (A23) | Blueprints (JSON plus diagrams) for the Hall, the back-room template and its Basement variant, the elevator and the infirmary, following section 7: dimensions, anchors, sightlines, lighting zones, camera positions |
| **T45b** Studio environment build (C+ST; L) | A16 Mara | A15 Leo, A17 Otto, A20 Zara (lights), A21 Wren (emitters), A28 Petra, A31 Ines (felt skins) | R/tools/build/env/, R/assets/models/env/ | T45a (A15), T44b (A16) | Final Hall and back-room models built from the blueprints, with felt-colour variants for the store, lint-clean, plus the Studio import checklist |
| **T45c** Props and 3D assets (C+ST; L) | A17 Otto | A15 Leo, A19 Anika (grip attachments), A20 Zara (emitter points), A28 Petra, A31 Ines (racket skins) | R/tools/build/props/, R/assets/models/props/, R/tools/lint/props.luau | T44a (A01), T47 (A23) | Zap racket and its skins, charged and dud cells, cell tray, charge box, stage lights, octagonal Hall tables, chalkboard wall boards, Brain Monitor housing, loan papers, 9 items, phone, chairs, elevator, infirmary bed, dossier folder as parametric models; lint-clean |
| **T45d** Fly models and rigs (C+ST; L) | A18 Rigo | A19 Anika, A04 Felix (emote and tell ids), A23 Nora (designs), A28 Petra, A31 Ines (glove skins) | R/tools/build/flies/, R/assets/models/flies/, R/tools/lint/rigs.luau | T44a (A01), T47 (A23) | Six fly rigs (Rookie, Panic, Cheetah, Pro, Cheater, Collector) with costumes, wings, glowing eyes and visible tell parts; the fly's floating forelegs; the player's floating gloves and glove skins; joints and attachments per contract; lint-clean |
| **T45e** Animation (C+ST; L) | A19 Anika | A13 Theo, A18 Rigo, A04 Felix (tells), A14 Camila | CL/Presentation/Anim/, R/assets/animations/, R/tests/client/anim/ | T44a (A01), T45d (A18) | Data-driven pose library plus procedural player for fly states x 6 flies and the floating hands (idle, think, pick up and aim the racket, zap, test on glove, load cells, use items, hurt, KO, celebrate, tell); optional KeyframeSequence export |
| **T45f** VFX (C+ST; M) | A20 Zara | A13 Theo, A29 Lex (flash limits), A28 Petra, A17 Otto (attach points) | CL/Presentation/Vfx/, R/assets/vfx/, R/tests/client/vfx/, R/tools/lint/vfx.luau | T44a (A01) | Preset library (zap arc, fizzle, cell glow, charge-box bolt flicker, stage-light flicker, item effects, blackout, KO stars, elevator, phone glow, monitor static) with reduced-flash variants; lint enforces flash and particle limits |
| **T45g** Sound effects (C+ST; M) | A21 Wren | A13 Theo, A28 Petra, A29 Lex (originality, captions) | R/tools/audio/sfx/, R/assets/audio/sfx/, CL/Audio/Sfx/, R/tests/audio/sfx/, R/tools/lint/audio.py | T44a (A01), T47 (A23) | Synthesized original SFX (OGG): buzz loops per fly, zap, fizzle, cell clicks, light hum, typewriter ticks for captions, item sounds, UI, phone, elevator, heartbeat; cue map module; upload manifest; audio lint |
| **T45h** Music and dynamic audio (C+ST; M) | A22 Mika | A13 Theo, A14 Camila (stingers), A04 Felix (terror and confidence signals), A28 Petra | R/tools/audio/music/, R/assets/audio/music/, CL/Audio/Music/, R/tests/audio/music/ | T44a (A01), T47 (A23) | Three synthesized stems plus stingers; MusicDirector (state -> layer gains and crossfades) with tests |
| **T46** Tutorial and onboarding (C+ST; M) | A26 Toby | A24 Dalia, A25 Tessa, A23 Nora, A09 Mateo (forced chamber), A27 Quinn (learnability) | SV/Services/TutorialService.luau, CL/Tutorial/, S/Content/Tutorial.luau, D/tutorial/, R/tests/integration/tutorial/ | T30a (A09), T41 (A12), T42a (A13) | Curriculum (the Signing, rules, counting, self-test, items, debt and interest, then Quickplay and the quests panel in the Hall), scripted chambers, hint triggers, completion conditions, service and UI |
| **T47** Narrative bible (C; M) | A23 Nora | A29 Lex (tone and policy), A00 Priya | D/narrative/BIBLE.md, S/Content/Lore.luau | none | Premise, the Shark and the loan contract, six fly bios with the names shown on the charge box, floors and Basement lore, title and Buzz flavour, voice guide, taboo list, glossary, credits text; Lore data table |
| **T48** Dialogue and barks (C; M) | A24 Dalia | A23 Nora, A25 Tessa, A26 Toby, A14 Camila, A29 Lex | S/Content/Dialogue.luau, D/narrative/DIALOGUE.md, R/tools/lint/dialogue.luau | T47 (A23), T01 (A01) | Shark calls per mood (6+ variants each), typewriter captions ("THE CELLS ENTER", load and turn lines), fly barks per fly and situation, elevator, foreclosure, revival and freedom lines, tutorial lines; ids, speakers, tags, length limits |
| **T49** UI copy (C; S) | A25 Tessa | A12 Uma, A29 Lex (plain language, screen-reader labels), A26 Toby, A30 Omar (quest texts), A31 Ines (store and title names) | S/Content/Strings.luau, D/narrative/UI_COPY.md, R/tools/lint/strings.luau | T47 (A23), T01 (A01) | Every HUD, menu, item, notice, settings and accessibility string by key, plus quest texts, store item names and descriptions, title and rank names; uppercase pixel-font length limits; credits copy; completeness lint |
| **T50** Balance sim and tuning (C; M) | A05 Soren | A03 Elena, A04 Felix, A30 Omar (real data later) | R/tools/balance_sim.luau, D/BALANCE_REPORT.md; values-only edits to S/Config/Balance.luau and S/Config/Floors.luau after T11 (handoff) | T10 (A02), T11 (A03), T12 (A04), T13 (A05); pass 2 also T23 (A07), T22b (A05) | Monte Carlo across archetypes x flies x zone; report vs targets; tuned numbers; pass 2 with real packs |
| **T51** Integration, E2E and playtest (C+ST; L) | A27 Quinn | A03 Elena, A04 Felix, A08 Vera, A09 Mateo, A10 Sasha, A11 Kiran, A12 Uma, A13 Theo (each fixes defects in its own modules), A26 Toby, A28 Petra, A29 Lex | R/tests/e2e/, R/tools/bots/, D/PLAYTEST.md, D/QA_REPORT.md | T30a-c (A09), T31 (A03), T32 (A03), T33a (A10), T33b (A30), T40 (A11), T41 (A12), T42a (A13), T43 (A08), T60 (A31), T61 (A30), T62 (A31) | Bot-driven E2E of the full loop with fakes (incl. a quest claim, a Buzz purchase, equip and rejoin), Studio playtest checklist and evidence, defect log |
| **T52a-1** Policy and accessibility requirements memo (C; S) | A29 Lex | A00 Priya | D/COMPLIANCE.md (Requirements section), D/ACCESSIBILITY.md (Requirements section) | none | Verified current policy requirements (URLs and dates) for gambling, self-harm, violence and fear labels, audio originality, flashing; accessibility checklist for UI, VFX and audio; questionnaire outline |
| **T52a-2** Compliance and accessibility audit (C+ST; M) | A29 Lex | A23 Nora, A24 Dalia, A25 Tessa (content fixes), A20 Zara, A12 Uma, A21 Wren, A22 Mika, A30 Omar | D/COMPLIANCE.md, D/ACCESSIBILITY.md, S/Content/Credits.luau | T33a (A10), T33b (A30), T41 (A12), T42b (A14), T46 (A26), T48 (A24), T49 (A25), T45f (A20), T45g (A21), T45h (A22), T61 (A30), T62 (A31) | Content scan, flash, contrast, tap-target and caption audit, store/quest/code policy check, originality check against the reference game, questionnaire answers, credits (MaleCNS, flybrain, honesty statement), sign-off matrix |
| **T52b-1** Performance budgets memo (C; S) | A28 Petra | A01 Cora, A08 Vera | D/PERFORMANCE.md (Budgets section), R/assets/budgets.json | none | Numeric, machine-readable budgets: instances and parts per back room and for the Hall, rooms per server, texture and audio MB, particles, remote bytes per second, server cost per duel; measurement method |
| **T52b-2** Performance verification (C+ST; M) | A28 Petra | A08 Vera, A16 Mara, A17 Otto, A18 Rigo, A21 Wren, A22 Mika, A12 Uma (fixes) | D/PERFORMANCE.md, S/Perf/, CL/Perf/, R/tools/lint/budgets.luau | T24 (A08), T41 (A12), T42a (A13), T43 (A08), T45b (A16), T45c (A17), T45d (A18), T45g (A21), T45h (A22) | Budget lint over all models, textures and audio manifests; instrumentation (frame time, memory, remote bytes); measured report vs budgets |
| **T53** Publish and live-ops (human + C; S) | A30 Omar | A29 Lex, A27 Quinn, A31 Ines (store setup) | D/LIVEOPS.md, D/PUBLISH_CHECKLIST.md | T52a-2 (A29) | Publish checklist (questionnaire, icon and thumbnail specs, store and developer-product setup, launch codes, monetization policy check), dashboard spec from the T33b KPIs, event calendar, roadmap (Floors 2-4, items 6-9, Queen) |
| **T60** Progression core (C; M) | A31 Ines | A03 Elena (profile fields), A10 Sasha (grant validation), A12 Uma (HUD), A23 Nora and A25 Tessa (title names), A30 Omar (rewards telemetry) | S/Progression/, S/Config/Progression.luau, SV/Services/ProgressionService.luau, R/tests/progression/ | T01 (A01), T31 (A03) | XP curve and level rewards, title registry with unlock rules (incl. RAGE QUITTER for 10 minutes), rank badge view-model (floor + debt repaid), Buzz wallet with an idempotent transaction log, `Meta` updates to the client |
| **T61** Daily quests and codes (C; M) | A30 Omar | A31 Ines (rewards), A25 Tessa (quest texts), A12 Uma (panel), A10 Sasha (code abuse), A29 Lex (no purchase required) | S/Content/Quests.luau, SV/Services/QuestService.luau, SV/Data/Codes.luau, R/tests/quests/ | T60 (A31), T30a (A09) | Quest engine over match events, a pool of 20 or more quests, a daily rotation of 3 seeded by player and UTC day, claims, redeem codes (one use per player, expiry) |
| **T62** Cosmetic store and inventory (C+ST; M) | A31 Ines | A10 Sasha (receipts), A12 Uma (screens), A17 Otto, A18 Rigo and A16 Mara (skin variants), A29 Lex (pricing policy), A30 Omar (catalog telemetry) | S/Content/Catalog.luau, SV/Services/StoreService.luau, R/tests/store/ | T01 (A01), T31 (A03), T60 (A31) | Catalog (racket, glove, felt and title-plate skins) at fixed Buzz or Robux prices; Buzz purchases; Robux developer products via idempotent `ProcessReceipt`; inventory, equip and ownership checks; equipped cosmetics sent to back rooms and watchers |

### 9.5 Handoff gates: how each item is verified before handoff

`CHK` = `bash roblox/scripts/check.sh` (StyLua check, Selene, `lune run tests/run`, every lint in `R/tools/lint/`, `rojo build`). `PYT f` = `python -m pytest tests/f`. The reviewer signs off in the PR; the Lead merges only when the listed output is pasted in the handoff report.

| Task | Verified before handoff | Reviewer |
|---|---|---|
| T00 | `CHK` green on the empty project in a fresh cloud session; the Lune smoke test writes and re-reads a `.rbxm`; workflow YAML parses | A00 Priya |
| T01 | Types compile (Selene, luau-lsp where available); JSON schemas validate their fixtures (`python -m jsonschema`); consumer sign-offs recorded in `D/ccr/contracts-v1-signoff.md`; tag `contracts-v1` | A02 Remy, A09 Mateo |
| T02 | Same 20 seeds x 10k draws identical from `lune run tests/run rng` and `PYT test_roulette_rng.py`; chi-square unbiasedness test; shuffle vectors | A06 Bea, A03 Elena |
| T10 | Property tests (lives within 0..max, chamber counts, turn rules, View never reveals an unrevealed cell); `rules_vectors.json` green; replay determinism; `CHK` | A05 Soren, A06 Bea |
| T11 | Unit tests; Monte Carlo reproduction: median duels-to-free for win rates 0.36 / 0.57 / 0.77 within 20% of 45 / 20 / 12; `CHK` | A05 Soren |
| T12 | Belief built from View only (redaction test); deterministic by seed; quirk tests (Cheater peek rate, Panic flinch scaling with terror, Cheetah timing); fallback pack plays 1,000 illegal-action-free duels per archetype; `CHK` | A05 Soren, A02 Remy |
| T13 | Solver table equals brute-force enumeration over every chamber order for all states (up to 8 cells); optimal wins 75% or more vs random over 10k seeded duels; archetype win rates within 0.03 of 0.36 / 0.57 / 0.77 vs the fallback mix; `CHK` | A02 Remy |
| T20 | `PYT test_roulette_rules.py` incl. all of `rules_vectors.json`; property tests mirror T10's invariants; no import of any Luau-derived data other than the vectors | A02 Remy |
| T21 | `PYT test_roulette_fly.py` with `fake_components()`: picture encoder, value heads learn the toy task above 80% in 300 rounds (the pattern of `test_the_fly_learns_higher_or_lower` in `tests/test_casino.py`), fear and dopamine hooks, dashboard attach; no connectome needed | A05 Soren |
| T22a | `PYT test_roulette_train.py` (quick mode deterministic by seed; resume works); scripted-stdin smoke of the `[R]` menu; on PC: bake logs for all six recipes in `D/bake_logs/` with seed, git sha, snapshot hashes | A05 Soren, A07 Pax |
| T22b | `PYT test_roulette_eval.py` on FakeBrain snapshots; on real snapshots the report meets starting bands (solver agreement: Rookie 55-70%, Cheetah 65-80%, Pro 90% or more, Cheater 90% or more with peek, Collector 93% or more; Panic within 5 points of Pro when ahead and at least 10 points lower when behind); a fly outside its band blocks its real export | A06 Bea, A04 Felix |
| T23 | `PYT test_roulette_export.py`: schema-valid, every shard under 100 KB, deterministic bytes; the T12 Lune loader reads every generated pack and reproduces Python decisions on 200 sampled states; provenance present | A04 Felix |
| T24 | `PYT test_roulette_viz.py` on FakeBrain: layout counts and region proportions, all fear-circuit neurons present, sheet dimensions, total textures 40 MB or less, manifest validates, deterministic; attribution file present | A28 Petra, A29 Lex |
| T30c | Lune boot test with fakes (ordered start, BindToClose restore); `rojo build`; grep gate: no `game:GetService` outside `Main.*` and `Platform/`; `CHK` | A00 Priya |
| T30b | Lune tests: sequencing, dedupe, resync, viewer filtering, spectator isolation; malformed-payload fuzz; `CHK` | A10 Sasha |
| T30a | Lune integration: full duel vs the fallback pack, timeout, forfeit, disconnect, a watcher sees only public events, seed determinism; back-room pool never hands one room to two duels and returns rooms after every exit path; Quickplay seats into a free room; grep gate; `CHK` | A04 Felix, A10 Sasha |
| T31 | Mock-store tests: migration v0 to v1, session-lock contention, autosave, retry and backoff, corrupt data rejected by the PlayerData schema; `CHK` | A10 Sasha |
| T32 | Integration: settle -> persist -> events; drip pauses in duel, menu and cutscene; away roll only after 12 h and at most once per 24 h; transitions; leaderboard write; `CHK` | A05 Soren, A09 Mateo |
| T33a | Adversarial suite (spoof, replay, flood, wrong turn, private-event leak) and 10k-case redaction fuzz pass; threat model documented; no open high finding; `CHK` | A27 Quinn |
| T33b | Every KPI event fires with a schema-valid payload in a simulated duel and settlement; no personal data fields; events per minute estimate documented; `CHK` | A29 Lex |
| T40 | Lune tests for reducers and input maps; Studio smoke checklist (camera, touch, gamepad); `CHK` | A12 Uma |
| T41 | View-model tests for every Hall and back-room element in section 7; layout lint (safe area, minimum tap target, contrast at least 4.5:1 computed from the palette, no string wider than its box in the pixel font); Studio checklist on desktop, phone and gamepad; `CHK` | A29 Lex |
| T42a | Deterministic timelines from event fixtures; every cue id in the catalog; skip and fast-forward; no orphan cues; Studio checklist; `CHK` | A14 Camila, A20 Zara |
| T42b | Timeline lint (durations, skippable after 1 s, cue ids valid, subtitles for every line, flash-safe); Lune timeline-player tests; Studio checklist; `CHK` | A23 Nora, A29 Lex |
| T43 | Clip-selection table and frame-math tests; texture budget check; Studio checklist with placeholder and then real sheets; `CHK` | A13 Theo, A28 Petra |
| T44a | Spec JSON validates against its schema; each asset agent signs off in `D/ccr/asset-contract-v1-signoff.md`; budgets referenced from `R/assets/budgets.json` | A28 Petra, A15 Leo |
| T44b | `lune run tools/build/graybox` then the env lint passes (Hall table count, back-room anchors, monitor part, collision groups); `rojo build`; `CHK` | A15 Leo |
| T45a | Blueprint JSON validates; lint: anchor names per contract, unobstructed sightline from CameraAnchor to FlyPerch and MonitorScreen; `CHK` | A16 Mara, A29 Lex |
| T45b | Env lint (counts within budgets, anchors, PrimaryParts, collision groups); rebuild is byte-reproducible; Studio import checklist; `CHK` | A15 Leo, A28 Petra |
| T45c | Props lint (bounds, budgets, names, attachments, PrimaryPart); reproducible build; `CHK` | A19 Anika, A28 Petra |
| T45d | Rig lint (joints, hierarchy, symmetry, part budget, attachments, tell parts); reproducible build; `CHK` | A19 Anika, A04 Felix |
| T45e | Curves sampled within bounds, loops close, durations match the cue catalog, joint names are a subset of the rig-lint output; Studio checklist; `CHK` | A18 Rigo, A13 Theo |
| T45f | VFX lint (at most 3 flashes per second, luminance delta cap, particle budget, a reduced-flash variant for every preset, ids cover the catalog); unit tests; `CHK` | A29 Lex, A28 Petra |
| T45g | `python roblox/tools/lint/audio.py`: peak at or below -1 dBFS, no clipping, loop seams, loudness window, size budget, at least one file per cue; deterministic build; `CHK` | A29 Lex, A13 Theo |
| T45h | Gain-function tests (monotonic in lives and terror, bounded, no discontinuities); stems phase-aligned; audio lint; `CHK` | A13 Theo, A14 Camila |
| T46 | Scripted duel test is deterministic; every teaching beat has a completion condition; curriculum covers the Signing, rules, items, debt and interest, Quickplay and quests; learnability check in Studio (A27); `CHK` | A27 Quinn |
| T47 | Checklist against this design (six flies, floors, mood names, the Shark); policy screen (no self-harm imagery, no gambling promotion); consistent glossary; Lore table lints | A29 Lex, A00 Priya |
| T48 | Dialogue lint: unique ids, every required id from the T01 catalog present, length limits, valid placeholders, banned terms; tone review against the bible | A23 Nora, A29 Lex |
| T49 | Strings lint: every Notice code and UI key has a string, length limits, valid placeholders; reading-level and tone check | A12 Uma, A29 Lex |
| T50 | Sim reproducible by seed; report meets targets (skilled 10-14, median 16-24, novice about 45 with 15-25% in the Basement) or documents a justified change; pass 2 re-run with real packs; only values changed; `CHK` | A03 Elena, A04 Felix |
| T51 | E2E bots finish 100 full loops (join, tutorial, duels, interest, Freed or Basement, rejoin) with zero contract violations; Studio playtest evidence recorded; defect log has no open blocker; `CHK` | A00 Priya |
| T52a-1 | Memo cites the live policy pages (URL and retrieval date) and lists concrete rules for each downstream agent | A00 Priya |
| T52a-2 | Content scan clean; audit matrix (flash, contrast, tap targets, captions, originality) all pass; questionnaire draft complete | A00 Priya |
| T52b-1 | Budgets are numeric and machine-readable; A01 references them in T44a | A01 Cora |
| T52b-2 | Budget lint passes on every asset manifest; Studio measurements recorded within budget or a waiver with an owner | A00 Priya |
| T53 | Publish checklist fully resolved; dashboard spec covers every KPI in T33b; roadmap lists Floors 2-4, items 6-9 and the Queen | A29 Lex |
| T60 | Unit tests: XP curve increasing, level rewards granted once, title unlocks from event fixtures, RAGE QUITTER applied on a mid-duel leave and gone after 10 minutes, Buzz log idempotent under duplicate grant ids, rank badge matches the ledger; `CHK` | A03 Elena, A10 Sasha |
| T61 | Rotation deterministic by player and UTC day; progress counted from event fixtures; claim idempotent; codes case-insensitive, one use per player, expiry honoured, never sent to the client; no quest needs a purchase; `CHK` | A31 Ines, A10 Sasha |
| T62 | Duplicate receipt ids grant once; a failed save returns NotProcessedYet; Buzz purchase is atomic; equip requires ownership; catalog lint (price, category, asset ids for every item, no chance-based item); `CHK` | A10 Sasha, A29 Lex |

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

### 9.7 Execution waves and spawn manifest

Earliest-start schedule from the dependency graph (49 items, 8 waves, at most 15 in parallel). Each entry is `slug->item`; the slug is the `subagent_type` to spawn.

```
W0  cora-contracts->T00 | nora-narrative->T47 | lex-compliance->T52a-1 | petra-perf->T52b-1
W1  cora-contracts->T01 | remy-rules->T02                                                                       gate M0
W2  remy-rules->T10 | elena-economy->T11 | bea-brain->T20 | mateo-backend->T30c | kiran-client->T40 |
    cora-contracts->T44a | dalia-dialogue->T48 | tessa-copy->T49
W3  felix-fly-ai->T12 | soren-solver->T13 | bea-brain->T21 | mateo-backend->T30b | elena-economy->T31 |
    uma-ui->T41 | theo-sequencer->T42a | vera-brainviz->T43 | mara-environment->T44b | leo-level->T45a |
    otto-props->T45c | rigo-rigging->T45d | zara-vfx->T45f | wren-sound->T45g | mika-music->T45h                gate M1
W4  bea-brain->T22a | pax-flypack->T23 | vera-brainviz->T24 | mateo-backend->T30a | elena-economy->T32 |
    camila-cinematics->T42b | mara-environment->T45b | anika-animation->T45e | soren-solver->T50 (pass 1) |
    ines-progression->T60
W5  soren-solver->T22b | sasha-security->T33a | omar-liveops->T33b | toby-tutorial->T46 | petra-perf->T52b-2 |
    omar-liveops->T61 | ines-progression->T62                                                                   gates M2, M3
W6  quinn-qa->T51 | lex-compliance->T52a-2 | soren-solver->T50 (pass 2)                                         gate M4
W7  omar-liveops->T53                                                                                           gate M5
```

| Wave | Items | Agents busy | Human gates in this wave |
|---|---|---|---|
| W0 | 4 | Cora, Nora, Lex, Petra | none |
| W1 | 2 | Cora, Remy | none |
| W2 | 8 | Remy, Elena, Bea, Mateo, Kiran, Cora, Dalia, Tessa | none |
| W3 | 15 | Felix, Soren, Bea, Mateo, Elena, Uma, Theo, Vera, Mara, Leo, Otto, Rigo, Zara, Wren, Mika | H1 starts as props, rigs and audio land |
| W4 | 10 | Bea, Pax, Vera, Mateo, Elena, Camila, Mara, Anika, Soren, Ines | H2 (real bake) starts; H1 continues |
| W5 | 7 | Soren, Sasha, Omar, Toby, Petra, Ines | H2 finishes; H3 Studio checks for the graybox |
| W6 | 3 | Quinn, Lex, Soren | H3 playtests; H4 credentials before publishing |
| W7 | 1 | Omar | H5 publish |

Where one agent has two items in a wave (Omar: T33b and T61 in W5), the Lead runs them back to back, T33b first.

**Milestones.** M0 after W1: `CHK` green, `contracts-v1`, RNG vectors. M1 after W3: engine, fly runtime and solver merged; the fallback pack plays 1,000 duels per fly in Lune. M2 after W5: six real FlyPacks and clips committed, all inside their evaluation bands. M3 after W5: playable graybox in Studio (Hall, Quickplay, a back room, services, client, monitor with placeholder or real clips, levels, quests and the store). M4 after W6: vertical slice: all six flies, five items, hybrid clock, Basement, tutorial, real monitor clips, meta features, E2E and audits passing. M5 after W7: public beta.

**If you throttle to 6-8 agents,** start each wave in this order: critical path (Felix T12, Mateo T30b/T30a, Sasha T33a, Lex T52a-2), then the Python chain (Bea T21, T22a), then services and client (Elena T31, Ines T60, Uma T41, Theo T42a), then content and assets. Toby can pre-draft the tutorial curriculum from W2 without blocking anything.

### 9.8 Human gates (only you can do these)

- **H1 Asset import and upload:** import the `.rbxm` files, upload OGG audio and the sprite sheets in Studio or via Open Cloud, and give the asset ids to the producing agent, who updates its manifest.
- **H2 Real brain bake on your PC:** run the T22a, T23 and T24 commands from `D/BRAIN_PIPELINE.md`; commit the generated packs and sheets (or hand them to Pax and Vera).
- **H3 Studio checks:** run the Studio checklists in the T40-T46, T45b and T51 briefs and paste the evidence.
- **H4 Credentials:** Roblox universe and place ids, and any Open Cloud key, are supplied outside git.
- **H5 Publish:** submit the questionnaire and publish using `D/PUBLISH_CHECKLIST.md`.

### 9.9 Key interfaces (T01 freezes exact types)

```lua
Engine.new(ruleset, seed, opts?) -> MatchState
Engine.legal(state, side) -> {Action}
Engine.apply(state, side, action) -> (MatchState, {DuelEvent})
Engine.view(state, viewer) -> View                    -- redacted; the only thing Fly and clients see
Ledger.settle(ledger, result, rng) -> (Ledger, {LedgerEvent})
Ledger.drip(ledger, dtSeconds, rng) / Ledger.awayRoll(ledger, now, rng)
FlyAgent.new(id, pack, seed); agent:observe(event); agent:decide(view) -> Decision
Director.pick(ctx, rng) -> flyId
```

## 10. Verification

For the design deliverable (this session, after approval), one script checks:
- every work item has exactly one primary agent from the roster, each agent's task and owned-path lists in `AGENTS.md` equal this table, and every agent has at least one primary item;
- every dependency exists, the graph has no cycle, and the waves recomputed from the dependencies equal the manifest in 9.7;
- no two agents own overlapping paths (the T50 values-only handoff and the `-1`/`-2` pairs of one owner are the documented exceptions);
- every work item has a brief `docs/roblox/tasks/<ID>-*.md` that names its agent, lists its owned paths and contains its 9.5 handoff checks;
- 32 agent files exist in `.claude/agents/` (31 specialists and Priya) with `name` equal to the file name and a non-empty description, and the names match the roster in 9.3;
- all relative links resolve; and the economy Monte Carlo, re-run from the doc's numbers, reproduces the table in section 3.

For the later phases (each brief's Acceptance section makes these concrete): `CHK` for Luau, shared RNG and rules vectors in both `lune` and `python -m pytest`, FakeBrain pytest in CI plus the real-brain evaluation on your PC, the T50 balance report against section 3, and the Studio playtest loop (join -> tutorial -> duels -> interest call -> Freed or Basement -> rejoin with saved debt) on desktop, phone and gamepad.

**Non-goals:** PvP, wagering of any kind, live neuron simulation on Roblox, user-made flies, voice chat, Floors 2-4 in the MVP.

## 11. Files in this folder

| File | What it is |
|---|---|
| `README.md` | Start here: how the Lead runs the waves, the paste-ready instruction, human gates |
| `DESIGN.md` | This document; the source of truth |
| `CONTRACTS.md` | Draft of the shared types, remotes, saved data and catalogs; Cora freezes it in T01 |
| `TASKS.md` | Work items, handoff gates, waves (generated from this document) |
| `AGENTS.md` | Roster and agent directory (generated from this document) |
| `tasks/<ID>-<slug>.md` | One brief per work item (generated) |
| `ccr/` | Change requests to frozen contracts |
| `check_design.py` | Regenerates the generated files (`--write`) and checks everything is consistent (default) |

Agent definitions live in `.claude/agents/<slug>.md` (generated).
