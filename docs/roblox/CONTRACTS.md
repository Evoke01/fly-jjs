# Fly Roulette: contracts (draft)

**Status: draft for T01.** Cora (A01) turns this into `roblox/src/shared/Types.luau`, `roblox/src/shared/Net/Protocol.luau` and the JSON schemas in `docs/roblox/schemas/`, collects sign-offs, and tags `contracts-v1`. After that, changes go through a change request in [ccr/](ccr/). Names and fields here are proposals; the rules in [DESIGN.md](DESIGN.md) sections 2-7b are not.

## Conventions

- Luau `--!strict`. Everything in `roblox/src/shared/` is pure data and functions, with no Roblox APIs, so Lune can test it.
- Ids are lowercase strings (`"magnifier"`, `"rookie"`); display text lives in `Content/Strings.luau` by key, never in code.
- Money is an integer number of dollars. Rates are fractions (`0.035` = 3.5%).
- Seats are numbered 1..n in turn order. In the MVP, seat 1 is the player and seat 2 is the fly.
- Randomness only through `Util/Rng.luau` (sfc32), seeded by the server. The same seed and the same actions give the same match, in Luau and in Python.

## Duel (rules engine, T10)

```lua
export type SeatKind = "player" | "fly"
export type Seat = { kind: SeatKind, id: string, lives: number, maxLives: number, items: {string}, skipNext: boolean }

export type Ruleset = {
    id: string,                     -- "zapper_v1"
    seats: number,                  -- 2..4 (MVP: 2)
    lives: number,                  -- 3
    loadMin: number, loadMax: number,           -- 2, 8
    itemsFromLoad: number,          -- 2 (no items in load 1)
    itemsPerLoad: { min: number, max: number }, -- 2..4
    itemSlots: number,              -- 6
    itemPool: {string},             -- MVP: magnifier, vent, sugar, web, overcharge
    turnSeconds: number,            -- 60 (Cheetah: 15)
    firstMover: "player" | "alternate" | "coin",
}

export type CellKind = "charged" | "dud"
export type Action =
      { kind: "fire", target: number }                  -- target seat; your own seat = "test on your glove"
    | { kind: "item", item: string, target: number? }   -- target for Web and later Espresso

export type DuelEvent =
      { kind: "LoadStarted", load: number, charged: number, dud: number }
    | { kind: "ItemsDealt", seat: number, items: {string} }
    | { kind: "TurnStarted", seat: number, deadline: number }
    | { kind: "ItemUsed", seat: number, item: string, target: number? }
    | { kind: "CellRevealed", seat: number, cell: CellKind, private: boolean }  -- Magnifier: private to the user
    | { kind: "CellEjected", cell: CellKind }                                  -- Vent: public
    | { kind: "Fired", shooter: number, target: number, cell: CellKind, damage: number }
    | { kind: "LivesChanged", seat: number, lives: number }
    | { kind: "TurnSkipped", seat: number }
    | { kind: "FlyThinking", seat: number, clip: string, terror: number, confidence: number, ms: number }
    | { kind: "MatchEnded", winner: number, reason: "lives" | "forfeit" | "timeout" }

-- What one viewer may know. The fly's Belief and every client are built from this only.
export type View = {
    viewer: number?,                -- nil for a watcher
    load: number, cellsLeft: number, chargedLeft: number,
    knownCurrent: CellKind?,        -- only if this viewer revealed it
    seats: {Seat}, turn: number, deadline: number,
}
```

Engine API (pure, deterministic):

```lua
Engine.new(ruleset: Ruleset, seed: number, opts: { seats: {Seat}, scriptedChamber: {CellKind}? }?): MatchState
Engine.legal(state: MatchState, seat: number): {Action}
Engine.apply(state: MatchState, seat: number, action: Action): (MatchState, {DuelEvent})
Engine.view(state: MatchState, viewer: number?): View
```

`scriptedChamber` fixes the cell order for the tutorial (T46). `MatchState` is opaque outside `Rules/` and never leaves the server.

## Economy (T11) and saved data (T31)

```lua
export type Zone = "normal" | "basement"
export type Ledger = { floor: number, zone: Zone, debt: number, lossRun: number, hiRun: number,
                       lastSeen: number, lastAwayRoll: number }
export type DuelResult = { won: boolean, flyId: string, livesLeft: number, forfeit: boolean }
export type LedgerEvent =
      { kind: "InterestRolled", mood: "calm" | "normal" | "hungry" | "spike", rate: number, debtBefore: number, debtAfter: number }
    | { kind: "PaidDown", amount: number, debtAfter: number }
    | { kind: "ZoneChanged", zone: Zone }
    | { kind: "Freed", floor: number }

Ledger.settle(ledger: Ledger, result: DuelResult, rng: Rng): (Ledger, {LedgerEvent})
Ledger.drip(ledger: Ledger, dtSeconds: number, rng: Rng): (Ledger, {LedgerEvent})
Ledger.awayRoll(ledger: Ledger, now: number, rng: Rng): (Ledger, {LedgerEvent})
```

PlayerData v1 (ProfileStore, session-locked). The meta fields are in v1 from the start, so T60-T62 need no migration.

```lua
export type PlayerData = {
    v: number,                                  -- 1
    debt: number, floor: number, zone: Zone, duelsWon: number, duelsLost: number,
    lossRun: number, hiRun: number, lastSeen: number, lastAwayRoll: number,
    freedCount: number, bestFloor: number, seenFlies: {string}, tutorialDone: boolean,
    settings: { reducedFlash: boolean, captions: boolean, music: number, sfx: number },
    xp: number, level: number, buzz: number,
    titles: {string}, equippedTitle: string?, rageQuitUntil: number,
    quests: { day: number, ids: {string}, progress: {number}, claimed: {boolean} },
    redeemedCodes: {string},
    owned: {string}, equipped: { racket: string?, gloves: string?, felt: string?, plate: string? },
    receipts: {string},                         -- processed Robux receipt ids, newest last, capped
}
```

## Fly (T12, T23)

```lua
export type FlyPack = {
    id: string, version: number,
    provenance: { seed: number, gitSha: string, snapshot: string, trainedDecisions: number },
    q: { [string]: {number} },    -- state key -> {value(fire at opponent), value(fire at self)}
    temperature: number, epsilon: number,
    fearCurve: {number},          -- danger 0..1 in 11 steps -> terror 0..1
    thinkMs: { min: number, max: number },
    items: string,                -- item personality id used by ItemLogic
}
export type Decision = { action: Action, thinkMs: number, terror: number, confidence: number, clip: string, emote: string? }

FlyAgent.new(id: string, pack: FlyPack, seed: number): FlyAgent
FlyAgent.observe(self, event: DuelEvent)
FlyAgent.decide(self, view: View): Decision
Director.pick(ctx: { floor: number, zone: Zone, lossRun: number, recent: {string}, wins: number }, rng: Rng): string
```

State key: `"<chargedLeft>/<cellsLeft>/<livesSelf>/<livesOpp>/<known>"` with `known` in `u`, `c`, `d`.

## Meta (T60-T62)

```lua
export type MetaState = { xp: number, level: number, buzz: number, titles: {string}, equippedTitle: string?,
                          rank: { floor: number, zone: Zone, repaid: number },   -- repaid 0..1 of the opening debt
                          quests: {{ id: string, progress: number, goal: number, claimed: boolean }},
                          owned: {string}, equipped: { [string]: string } }
```

## Remotes (T30b)

All payloads carry `seq` so the client can drop duplicates and ask for a `Snapshot` after a gap.

| Remote | Direction | Payload |
|---|---|---|
| `Intent` | client -> server | `{seq, kind, target?, item?}` with `kind` one of `fire`, `item`, `ready` |
| `Event` | server -> client | `{seq, matchId, ev: DuelEvent}`; private events go only to their viewer |
| `Snapshot` | server -> client | `{seq, matchId, view: View}` for resync and new watchers |
| `Ledger` | server -> client | `{seq, debt, floor, zone, rate?, delta, reason}` |
| `Notice` | server -> client | `{seq, code, args}` |
| `MetaIntent` | client -> server | `{seq, kind, arg?}` with `kind` one of `quickplay`, `sit`, `watch`, `leave`, `claim`, `redeem`, `buy`, `equip` |
| `Meta` | server -> client | `{seq, patch: partial MetaState}` |

The server validates every intent (seat, turn, legality, rate limit) in `Guard` before anything else sees it.

## Catalogs (ids only; text lives in Strings.luau)

- **Cue ids** (presentation): `zap.charge`, `zap.hit`, `zap.fizzle`, `cell.enter`, `cell.load`, `bolt.lost`, `item.<id>`, `fly.<state>`, `light.flicker`, `room.enter`, `room.leave`, `shark.ring`, `elevator.up`, `basement.drop`, `blackout`, `ko`, `jackpot.freed`.
- **Caption ids**: `cap.cells_enter`, `cap.load_n`, `cap.turn_player`, `cap.turn_fly`, `cap.shark_calling`, `cap.freed`, `cap.foreclosed`.
- **Notice codes**: `forfeit`, `mercy`, `timeout`, `rage_quit`, `room_full`, `code_invalid`, `code_used`, `not_enough_buzz`, `purchase_failed`, `not_owned`.
- **Title ids**: `debt_free`, `champion`, `fly_whisperer`, `basement_dweller`, `collectors_bane`, `rage_quitter`.
- **Quest event keys**: `duel.won`, `duel.played`, `fly.beaten.<id>`, `item.used.<id>`, `fire.self`, `win.full_lives`.
- **Fly ids**: `rookie`, `panic`, `cheetah`, `pro`, `cheater`, `collector`. **Item ids**: `magnifier`, `vent`, `sugar`, `web`, `overcharge`.

## Schemas (T01 writes these, each with a passing and a failing fixture)

`docs/roblox/schemas/`: `flypack.schema.json`, `playerdata.schema.json`, `ruleset.schema.json`, `catalog.schema.json`, `quests.schema.json`, `asset-spec.schema.json`, `budgets.schema.json`.
