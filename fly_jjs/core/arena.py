"""A small JJS-style 1v1 arena, for training and testing the fly without Roblox.

It renders frames the real pipeline consumes (the eyes, the opponent tracker and the
health-bar rewards all run unchanged) and takes the same keyboard/mouse input the game
would get from InputController. Mechanics are loosely modelled on JJS: M1 combos with a
knockback on the 4th hit, four skills on cooldowns, block (F), dash with i-frames (Q),
jump (Space), awakening (G) when the meter is full. The opponent approaches, telegraphs
its strikes, combos, blocks some hits and throws projectiles.

It is not JJS: its visuals and timings are simpler. Use it to warm the fly up, to watch
it fight, and to check that changes help; fine-tune in the real game.
"""
import math

import numpy as np
import cv2

from fly_jjs.core.combat import DEFAULT_HP_BARS

DT = 0.05                     # seconds per frame (20 FPS, like the game loop)
ARENA_RADIUS = 18.0           # metres
HFOV = math.radians(80)
CAMERA_BACK = 5.0             # third-person camera: this far behind the player...
CAMERA_HEIGHT = 2.2           # ...at this height, looking forward
CAMERA_SIDE = 0.8             # ...and a little to the right (over the shoulder, like shift-lock)
MOUSE_RAD_PER_PX = 0.0035     # camera turn per mouse pixel

SKILLS = {   # key: (range m, half-arc deg, damage, cooldown s, stun s)
    "1": (3.0, 35, 9, 5.0, 0.0),
    "2": (7.0, 12, 8, 7.0, 0.0),
    "3": (2.5, 45, 12, 9.0, 0.8),
    "4": (4.0, 25, 15, 12.0, 0.0),
}
M1 = dict(range=2.3, arc=35, damage=4.0, cooldown=0.28, combo_reset=1.0, knockback=3.5, stun=0.7)
PALETTE = [(235, 235, 240), (40, 40, 45), (40, 40, 200), (200, 90, 40), (60, 170, 60), (120, 200, 230),
           (150, 60, 150), (30, 140, 230)]


class ArenaInput:
    """InputController backend that feeds the arena instead of the operating system."""

    sprint_gap = 0.0

    def __init__(self):
        self.held = set()
        self.taps = []
        self.clicks = 0
        self.mouse = [0.0, 0.0]

    def key_down(self, key):
        self.held.add(key)

    def key_up(self, key):
        self.held.discard(key)

    def tap(self, key):
        self.taps.append(key)

    def click(self):
        self.clicks += 1

    def move(self, dx, dy):
        self.mouse[0] += dx
        self.mouse[1] += dy

    def camera_button(self, down):
        pass

    def take(self):
        """This frame's input; taps, clicks and mouse movement are consumed."""
        out = (set(self.held), list(self.taps), self.clicks, tuple(self.mouse))
        self.taps, self.clicks, self.mouse = [], 0, [0.0, 0.0]
        return out


def _angle_to(src, dst):
    """Yaw (radians, 0 = +y, clockwise) of the direction from src to dst."""
    return math.atan2(dst[0] - src[0], dst[1] - src[1])


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Arena:
    def __init__(self, width=480, height=360, difficulty=1.0, seed=0, max_seconds=75.0):
        self.width, self.height = width, height
        self.difficulty = difficulty
        self.max_seconds = max_seconds
        self.rng = np.random.default_rng(seed)
        self.focal = (width / 2) / math.tan(HFOV / 2)
        self._panorama = self._make_panorama()
        self.reset()

    # ---- setup ----------------------------------------------------------------------

    def _make_panorama(self):
        """A 360-degree backdrop (sky, skyline, ground) that scrolls as the camera turns."""
        w = int(round(self.width * 2 * math.pi / HFOV))
        h = self.height
        pano = np.zeros((h, w, 3), np.uint8)
        horizon = h // 2
        for y in range(horizon):
            t = y / horizon
            pano[y] = (200 - 60 * t, 165 - 35 * t, 120 - 30 * t)
        x = 0
        while x < w:
            bw = int(self.rng.integers(w // 40, w // 14))
            bh = int(self.rng.integers(h // 12, h // 3))
            shade = int(self.rng.integers(55, 110))
            pano[horizon - bh:horizon, x:x + bw] = (shade, shade + 5, shade + 10)
            x += bw + int(self.rng.integers(0, w // 30))
        ground = cv2.GaussianBlur(self.rng.random((h - horizon, w)).astype(np.float32), (0, 0), 3)
        ground = (ground - ground.min()) / (np.ptp(ground) + 1e-6)
        pano[horizon:, :, 0] = (70 + 35 * ground).astype(np.uint8)
        pano[horizon:, :, 1] = (95 + 35 * ground).astype(np.uint8)
        pano[horizon:, :, 2] = (85 + 35 * ground).astype(np.uint8)
        return np.concatenate([pano, pano[:, :self.width]], axis=1)   # wrap-around margin

    def reset(self):
        r = self.rng
        start = r.uniform(0, 2 * math.pi)
        self.player = dict(pos=np.array([math.sin(start), math.cos(start)]) * 6.0,
                           yaw=0.0, hp=100.0, cooldowns={}, block=False, dash_t=0.0, dash_dir=None,
                           iframes=0.0, air=0.0, sprint=False, combo=0, last_m1=-9.0, awaken_t=0.0,
                           meter=0.0, hit_flash=0.0, stun=0.0,
                           colour=PALETTE[int(r.integers(len(PALETTE)))])
        opp_angle = start + math.pi + r.uniform(-0.6, 0.6)
        self.opp = dict(pos=np.array([math.sin(opp_angle), math.cos(opp_angle)]) * 6.0,
                        yaw=0.0, hp=100.0, state="approach", t=0.0, combo=0, stun=0.0, skill_cd=r.uniform(3, 6),
                        strafe=r.choice([-1, 1]), strafe_t=0.0, spark=0.0, blocking=0.0,
                        colour=PALETTE[int(r.integers(len(PALETTE)))])
        # Face roughly away from the opponent sometimes, so the camera has to find it.
        self.player["yaw"] = _angle_to(self.player["pos"], self.opp["pos"]) + r.uniform(-1.2, 1.2)
        self.opp["yaw"] = _angle_to(self.opp["pos"], self.player["pos"])
        self.projectiles = []
        self.pillars = [np.array([math.sin(a), math.cos(a)]) * r.uniform(8, 16)
                        for a in r.uniform(0, 2 * math.pi, 5)]
        self.frame = 0
        self.time = 0.0
        self.done = False
        self.won = None
        self.stats = dict(dealt=0.0, taken=0.0, hits=0, got_hit=0, blocked=0)
        self._prev_w_tap = -9.0

    # ---- simulation -----------------------------------------------------------------

    def _facing_error(self, who, target_pos):
        return abs(math.degrees(_wrap(_angle_to(who["pos"], target_pos) - who["yaw"])))

    def _hurt_opponent(self, damage, stun=0.0, knockback=0.0):
        o, p = self.opp, self.player
        if p["awaken_t"] > 0:
            damage *= 1.5
        if o["blocking"] > 0:
            damage *= 0.2
        o["hp"] = max(0.0, o["hp"] - damage)
        o["spark"] = 0.15
        o["stun"] = max(o["stun"], stun)
        if knockback:
            away = o["pos"] - p["pos"]
            o["pos"] = o["pos"] + away / (np.linalg.norm(away) + 1e-6) * knockback
            o["stun"] = max(o["stun"], M1["stun"])
        if o["state"] in ("windup", "skill"):
            o["state"], o["t"] = "approach", 0.0          # interrupted
        p["meter"] = min(1.0, p["meter"] + damage / 120.0)
        self.stats["dealt"] += damage
        self.stats["hits"] += 1

    def _hurt_player(self, damage, blockable=True):
        p, o = self.player, self.opp
        if p["iframes"] > 0:
            return
        if blockable and p["block"] and self._facing_error(p, o["pos"]) < 70:
            damage *= 0.2
            self.stats["blocked"] += 1
        p["hp"] = max(0.0, p["hp"] - damage)
        p["hit_flash"] = 0.15
        self.stats["taken"] += damage
        self.stats["got_hit"] += 1

    def _player_act(self, held, taps, clicks, mouse):
        p, o = self.player, self.opp
        p["yaw"] = _wrap(p["yaw"] + mouse[0] * MOUSE_RAD_PER_PX)
        p["block"] = "f" in held and p["stun"] <= 0
        if "w" in taps:
            self._prev_w_tap = self.time
        if "w" in held and self.time - self._prev_w_tap < 0.4:
            p["sprint"] = True
        if "w" not in held:
            p["sprint"] = False
        if p["stun"] > 0:
            return

        fwd = np.array([math.sin(p["yaw"]), math.cos(p["yaw"])])
        right = np.array([math.cos(p["yaw"]), -math.sin(p["yaw"])])
        move = fwd * (("w" in held) - ("s" in held)) + right * (("d" in held) - ("a" in held))
        if "q" in taps and p["cooldowns"].get("q", 0) <= 0:
            p["dash_t"], p["iframes"] = 0.2, 0.25
            p["dash_dir"] = move / np.linalg.norm(move) if np.linalg.norm(move) > 0 else fwd
            p["cooldowns"]["q"] = 2.0
        if p["dash_t"] > 0:
            p["pos"] = p["pos"] + p["dash_dir"] * (4.0 / 0.2) * DT
        elif np.linalg.norm(move) > 0:
            speed = 9.0 if p["sprint"] else 6.0
            if p["block"]:
                speed *= 0.5
            p["pos"] = p["pos"] + move / np.linalg.norm(move) * speed * DT
        if "space" in taps and p["air"] <= 0 and p["cooldowns"].get("space", 0) <= 0:
            p["air"], p["cooldowns"]["space"] = 0.6, 0.8

        dist = float(np.linalg.norm(o["pos"] - p["pos"]))
        facing = self._facing_error(p, o["pos"])
        if clicks and not p["block"] and self.time - p["last_m1"] >= M1["cooldown"]:
            if self.time - p["last_m1"] > M1["combo_reset"]:
                p["combo"] = 0
            p["last_m1"] = self.time
            if dist <= M1["range"] and facing <= M1["arc"]:
                p["combo"] += 1
                if p["combo"] >= 4:
                    self._hurt_opponent(M1["damage"], knockback=M1["knockback"])
                    p["combo"] = 0
                else:
                    self._hurt_opponent(M1["damage"])
            else:
                p["combo"] = 0
        for key, (rng_m, arc, dmg, cd, stun) in SKILLS.items():
            if key in taps and p["cooldowns"].get(key, 0) <= 0 and not p["block"]:
                p["cooldowns"][key] = cd
                if dist <= rng_m and facing <= arc:
                    self._hurt_opponent(dmg, stun=stun)
        if "r" in taps and p["cooldowns"].get("r", 0) <= 0:
            p["cooldowns"]["r"] = 10.0
            if dist <= 3.0:
                self._hurt_opponent(7.0)
        if "g" in taps and p["meter"] >= 1.0:
            p["meter"], p["awaken_t"] = 0.0, 12.0

    def _opponent_act(self):
        o, p = self.opp, self.player
        d = self.difficulty
        to_player = p["pos"] - o["pos"]
        dist = float(np.linalg.norm(to_player))
        o["yaw"] = _angle_to(o["pos"], p["pos"])
        o["blocking"] = max(0.0, o["blocking"] - DT)
        if o["stun"] > 0:
            o["stun"] -= DT
            return
        o["skill_cd"] -= DT
        o["t"] += DT
        dirn = to_player / (dist + 1e-6)
        side = np.array([dirn[1], -dirn[0]]) * o["strafe"]

        if o["state"] == "windup":                         # telegraphed strike
            if o["t"] >= 0.32 / d:
                if dist <= 2.2 and p["air"] <= 0:
                    self._hurt_player(6.0 * d)
                o["combo"] += 1
                if o["combo"] >= 3:
                    o["state"], o["t"], o["combo"] = "recover", 0.0, 0
                else:
                    o["state"], o["t"] = "windup", 0.0 - 0.12
            return
        if o["state"] == "skill":                          # charging a projectile
            if o["t"] >= 0.6 / d:
                self.projectiles.append(dict(pos=o["pos"].copy(), target=p["pos"].copy(),
                                             speed=15.0, colour=(40, 160, 255)))
                o["state"], o["t"], o["skill_cd"] = "recover", 0.0, self.rng.uniform(5, 8) / d
            return
        if o["state"] == "recover":
            if o["t"] >= 0.8:
                o["state"], o["t"] = "approach", 0.0
            else:
                o["pos"] = o["pos"] - dirn * 2.0 * DT
            return

        # Approach / strafe, start attacks.
        o["strafe_t"] += DT
        if o["strafe_t"] > 2.0:
            o["strafe"], o["strafe_t"] = -o["strafe"], 0.0
        if 3.5 <= dist <= 9.0 and o["skill_cd"] <= 0 and self.rng.random() < 0.04 * d:
            o["state"], o["t"] = "skill", 0.0
        elif dist <= 2.0:
            o["state"], o["t"], o["combo"] = "windup", 0.0, 0
        else:
            o["pos"] = o["pos"] + (dirn * 5.5 * min(1.0, d) + side * 1.5) * DT

    def _projectiles(self):
        p = self.player
        keep = []
        for pr in self.projectiles:
            step = pr["target"] - pr["pos"]
            left = float(np.linalg.norm(step))
            travel = pr["speed"] * DT
            if left <= travel:
                if np.linalg.norm(p["pos"] - pr["target"]) < 1.3 and p["air"] <= 0:
                    self._hurt_player(12.0 * self.difficulty)
                continue
            pr["pos"] = pr["pos"] + step / left * travel
            keep.append(pr)
        self.projectiles = keep

    def step(self, arena_input):
        """Advance one frame with this frame's input. Returns the stats dict."""
        if self.done:
            return self.stats
        held, taps, clicks, mouse = arena_input.take()
        p, o = self.player, self.opp
        for who in (p,):
            for k in list(who["cooldowns"]):
                who["cooldowns"][k] = max(0.0, who["cooldowns"][k] - DT)
        for key in ("dash_t", "iframes", "air", "hit_flash", "awaken_t", "stun"):
            p[key] = max(0.0, p[key] - DT)
        o["spark"] = max(0.0, o["spark"] - DT)

        # The opponent sometimes reads an incoming M1 and blocks it.
        if clicks and self.rng.random() < 0.12 * self.difficulty:
            o["blocking"] = 0.3

        self._player_act(held, taps, clicks, mouse)
        self._opponent_act()
        self._projectiles()
        for body in (p, o):
            r = np.linalg.norm(body["pos"])
            if r > ARENA_RADIUS:
                body["pos"] = body["pos"] / r * ARENA_RADIUS
        # Bodies don't overlap.
        gap = o["pos"] - p["pos"]
        dist = np.linalg.norm(gap)
        if dist < 0.8:
            push = gap / (dist + 1e-6) * (0.8 - dist) / 2
            o["pos"], p["pos"] = o["pos"] + push, p["pos"] - push

        self.frame += 1
        self.time = self.frame * DT          # counted, so 1500 frames is exactly 75 s
        if p["hp"] <= 0 or o["hp"] <= 0 or self.time >= self.max_seconds:
            self.done = True
            self.won = o["hp"] <= 0 or (p["hp"] > 0 and p["hp"] > o["hp"] and self.time >= self.max_seconds)
        return self.stats

    # ---- rendering ------------------------------------------------------------------

    def _project(self, world_xy, height=0.0):
        """Screen (x, y) and depth of a world point seen by the third-person camera,
        or None if it is behind the camera."""
        p = self.player
        fwd = np.array([math.sin(p["yaw"]), math.cos(p["yaw"])])
        right = np.array([math.cos(p["yaw"]), -math.sin(p["yaw"])])
        camera = p["pos"] - fwd * CAMERA_BACK + right * CAMERA_SIDE
        rel = world_xy - camera
        z = float(rel @ fwd)
        if z < 0.5:
            return None
        x = float(rel @ right)
        eye = CAMERA_HEIGHT + (0.6 if p["air"] > 0 else 0.0)
        return (self.width / 2 + x / z * self.focal, self.height / 2 - (height - eye) / z * self.focal, z)

    def _draw_person(self, img, pos, colour, windup=0.0, spark=0.0, aura=0.0):
        feet = self._project(pos, 0.0)
        head = self._project(pos, 1.8)
        if feet is None or head is None:
            return
        fx, fy, z = feet
        hy = head[1]
        h = fy - hy
        if h < 4 or fx < -h or fx > self.width + h:
            return
        w = 0.34 * h
        c = tuple(int(v) for v in colour)
        if aura > 0:
            cv2.circle(img, (int(fx), int(hy + 0.45 * h)), int(0.4 * h * (0.5 + aura)), (40, 160, 255), -1)
        cv2.rectangle(img, (int(fx - w / 2), int(hy + 0.22 * h)), (int(fx + w / 2), int(hy + 0.6 * h)), c, -1)
        cv2.rectangle(img, (int(fx - w / 2), int(hy + 0.6 * h)), (int(fx - w * 0.05), int(fy)), c, -1)
        cv2.rectangle(img, (int(fx + w * 0.05), int(hy + 0.6 * h)), (int(fx + w / 2), int(fy)), c, -1)
        cv2.rectangle(img, (int(fx - w * 0.8), int(hy + 0.24 * h)), (int(fx - w / 2), int(hy + 0.55 * h)), c, -1)
        cv2.rectangle(img, (int(fx + w / 2), int(hy + 0.24 * h)), (int(fx + w * 0.8), int(hy + 0.55 * h)), c, -1)
        cv2.circle(img, (int(fx), int(hy + 0.11 * h)), max(2, int(0.11 * h)), c, -1)
        if windup > 0:
            cv2.circle(img, (int(fx + w * 0.8), int(hy + 0.3 * h)), max(2, int(0.18 * h * windup)), (180, 255, 255), -1)
        if spark > 0:
            cv2.circle(img, (int(fx), int(hy + 0.4 * h)), max(2, int(0.25 * h)), (255, 255, 255), 2)

    def render(self):
        p, o = self.player, self.opp
        w, h = self.width, self.height
        pano_w = self._panorama.shape[1] - w
        offset = int(((p["yaw"] - HFOV / 2) % (2 * math.pi)) / (2 * math.pi) * pano_w)
        img = self._panorama[:, offset:offset + w].copy()

        things = []
        for pillar in self.pillars:
            proj = self._project(pillar)
            if proj is not None:
                things.append((proj[2], "pillar", pillar))
        proj = self._project(o["pos"])
        if proj is not None:
            things.append((proj[2], "opp", o["pos"]))
        proj = self._project(p["pos"])
        if proj is not None:
            things.append((proj[2], "self", p["pos"]))
        for pr in self.projectiles:
            proj = self._project(pr["pos"], 1.2)
            if proj is not None:
                things.append((proj[2], "proj", pr))
        for _, kind, thing in sorted(things, key=lambda t: -t[0]):
            if kind == "pillar":
                base, top = self._project(thing, 0.0), self._project(thing, 4.0)
                if base and top:
                    half = max(2, int(0.5 / base[2] * self.focal))
                    cv2.rectangle(img, (int(base[0] - half), int(top[1])), (int(base[0] + half), int(base[1])),
                                  (95, 95, 105), -1)
            elif kind == "opp":
                windup = min(1.0, o["t"] / 0.32) if o["state"] == "windup" else 0.0
                aura = min(1.0, o["t"] / 0.6) if o["state"] == "skill" else 0.0
                self._draw_person(img, o["pos"], o["colour"], windup, o["spark"], aura)
            elif kind == "self":
                self._draw_person(img, p["pos"], p["colour"])
            else:
                x, y, z = self._project(thing["pos"], 1.2)
                cv2.circle(img, (int(x), int(y)), max(3, int(0.35 / z * self.focal)), thing["colour"], -1)

        if p["hit_flash"] > 0:   # drawn under the HUD, like a game's damage vignette
            red = np.zeros_like(img)
            red[:, :] = (30, 30, 220)
            img = cv2.addWeighted(img, 0.6, red, 0.4, 0)

        self._draw_bar(img, DEFAULT_HP_BARS["self"]["roi"], p["hp"] / 100.0, (60, 200, 60), thick=1.0)
        self._draw_bar(img, DEFAULT_HP_BARS["enemy"]["roi"], o["hp"] / 100.0, (40, 40, 220), thick=0.5)
        x0, x1 = int(0.05 * w), int(0.35 * w)
        cv2.rectangle(img, (x0, int(0.955 * h)), (x0 + int((x1 - x0) * p["meter"]), int(0.975 * h)), (230, 150, 50), -1)
        return np.dstack([img, np.full((h, w), 255, np.uint8)])

    def _draw_bar(self, img, roi, fill, colour, thick=1.0):
        h, w = img.shape[:2]
        x0, y0, x1, y1 = int(roi[0] * w), int(roi[1] * h), int(roi[2] * w), int(roi[3] * h)
        pad = int((y1 - y0) * (1 - thick) / 2)
        cv2.rectangle(img, (x0, y0 + pad), (x1, y1 - pad), (30, 30, 30), -1)
        cv2.rectangle(img, (x0, y0 + pad), (x0 + int((x1 - x0) * fill), y1 - pad), colour, -1)


def _arena_brain_meta(path):
    """Profile metadata so the arena brain shows up in the Profile Manager."""
    import json
    import os
    import time
    meta_path = os.path.join(os.path.dirname(path), "metadata.json")
    if not os.path.exists(meta_path):
        with open(meta_path, "w") as f:
            json.dump({"name": "arena", "description": "Trained in the simulated arena",
                       "created": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)


def run_arena(fights=10, learn=True, watch=True, difficulty=1.0, seed=None, brain_path=None,
              readout=None, instincts=None, verbose=True):
    """Let the fly fight simulated opponents. Returns one result dict per fight.

    The arena brain lives in the "arena" profile, so it never overwrites the brain you
    use in the game; load it from the Profile Manager when you want to play with it.
    """
    import os

    from fly_jjs.core.agent import FlyAgent
    from fly_jjs.core.brain import get_brain_components
    from fly_jjs.core.config import ConfigManager
    from fly_jjs.core.storage import ARENA_WEIGHTS_PATH

    cfg = dict(ConfigManager.load_config())
    cfg["hp_bars"] = None                     # the arena draws its own health bars
    if instincts is not None:
        cfg["instincts"] = instincts
    path = brain_path or ARENA_WEIGHTS_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    components = get_brain_components()
    arena = Arena(difficulty=difficulty, seed=seed)
    backend = ArenaInput()
    agent = FlyAgent(components, cfg, arena.width, arena.height, backend, learn=learn, readout=readout, seed=seed)
    agent.learner.load(path)
    window = "Fly Arena"
    results = []
    stop = False
    for n in range(fights):
        arena.reset()
        agent.new_fight()
        while not arena.done and not stop:
            img = arena.render()
            step = agent.step(img, arena.time)
            arena.step(backend)
            if watch:
                view = cv2.resize(img[:, :, :3], (arena.width * 2, arena.height * 2), interpolation=cv2.INTER_NEAREST)
                cv2.putText(view, f"Fight {n + 1}/{fights}  {arena.time:4.1f}s  dopamine {agent.learner.dopamine:+.2f}",
                            (12, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(view, "Pressing: " + (", ".join(sorted(step.actions)) or "-"), (12, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 128), 1)
                cv2.imshow(window, view)
                if cv2.waitKey(1) & 0xFF == 27:
                    stop = True
        if stop:
            break
        final, _ = agent.end_fight(arena.render())
        result = dict(fight=n + 1, won=bool(arena.won), seconds=round(arena.time, 1), **arena.stats)
        results.append(result)
        if verbose:
            print(f"[Arena] Fight {n + 1}: {'WIN ' if arena.won else 'LOSS'} in {arena.time:4.1f}s | "
                  f"dealt {arena.stats['dealt']:5.1f} | taken {arena.stats['taken']:5.1f} | "
                  f"win rate so far {np.mean([r['won'] for r in results]):.0%}")
        if learn:
            agent.learner.save(path)
            _arena_brain_meta(path)
    if watch:
        try:
            cv2.destroyWindow(window)
        except Exception:
            pass
    return results
