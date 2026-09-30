"""Keep the Fly Roulette plan consistent.

DESIGN.md is the source of truth. This script derives the rest from it:
TASKS.md, AGENTS.md, one brief per work item in tasks/, and one agent
definition per agent in .claude/agents/.

    python docs/roblox/check_design.py           # check everything, exit 1 on problems
    python docs/roblox/check_design.py --write   # regenerate the derived files, then check
"""
import itertools
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DESIGN = os.path.join(HERE, "DESIGN.md")
TASKS_DIR = os.path.join(HERE, "tasks")
AGENTS_DIR = os.path.join(REPO, ".claude", "agents")
GENERATED = "<!-- Generated from DESIGN.md by check_design.py --write. Edit DESIGN.md instead. -->"

# Short path prefixes used in the tables, longest first.
PREFIXES = (("SV/", "roblox/src/server/"), ("CL/", "roblox/src/client/"), ("PY/", "fly_jjs/core/"),
            ("PT/", "tests/"), ("S/", "roblox/src/shared/"), ("R/", "roblox/"), ("D/", "docs/roblox/"))
TASK_ID = r"T\d\d[a-z]?(?:-\d)?"
NOTES = {"T22a": "W4, real bake on your PC", "T43": "W3, placeholder clips until T24", "T50": "W4 pass 1, W6 pass 2"}
READ_FIRST = [  # (task-id prefix, DESIGN.md sections)
    ("T00", "6, 9, 11"), ("T01", "2, 3, 6, 7b"), ("T02", "2, 6"), ("T10", "2, 6"), ("T11", "3, 6"), ("T12", "4, 6"),
    ("T13", "2, 4"), ("T2", "4, 5"), ("T30", "6, 7"), ("T31", "3, 6"), ("T32", "3, 6, 7"), ("T33", "6, 8"),
    ("T4", "6, 7"), ("T46", "1, 7, 7b"), ("T47", "1, 4, 7, 7b"), ("T48", "1, 3, 7"), ("T49", "7, 7b"),
    ("T50", "3, 4"), ("T51", "1, 7b, 10"), ("T52", "7, 7b, 8"), ("T53", "7b, 8"), ("T6", "3, 6, 7b"),
]
RULES = """- Edit only the paths you own. Anything else goes through a change request in `docs/roblox/ccr/CCR-<n>.md`; the Lead rules on it and the owner applies it.
- Contracts (`CONTRACTS.md`, `Types.luau`, `Net/Protocol.luau`, `docs/roblox/schemas/`) are frozen once `contracts-v1` is tagged.
- `--!strict` Luau. No Roblox APIs in `roblox/src/shared/`; only `Main.*.luau` and `roblox/src/server/Platform/` call `game:GetService`.
- Run `bash roblox/scripts/check.sh` (and `python -m pytest` for Python work) before pushing, and paste the output in the PR.
- One branch and one PR per work item: `claude/fr-<ID>-<slug>` into the integration branch.
- No secrets and no connectome data in git. No names, art or audio from Buckshot Roulette or from the reference Roblox game.
- Nothing outside a duel may change the debt, lives, items or odds (DESIGN.md sections 3 and 7b)."""
REPORT = """1. Work item and agent.
2. Files changed (all inside your owned paths).
3. Each handoff check above as `command -> result`.
4. Open risks and follow-ups.
5. Who consumes this next (see "Blocks")."""


def expand(text):
    """Turn table shorthand (S/Rules/) into repo paths (roblox/src/shared/Rules/)."""
    for short, full in PREFIXES:
        text = re.sub(r"(?<![\w/.])" + re.escape(short), full, text)
    return text


def section(md, start, stop):
    """The text from heading `start` up to heading `stop`."""
    a = md.index(start)
    b = md.index(stop, a + len(start))
    return md[a:b].rstrip() + "\n"


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_rows(md, header):
    a = md.index(header)
    out = []
    for line in md[a:].splitlines()[2:]:
        if not line.startswith("|"):
            break
        out.append(cells(line))
    return out


def split_paths(owns):
    """Owned paths of one table cell, braces expanded, notes and parentheses dropped."""
    main = re.sub(r"\([^)]*\)", "", owns).split(";")[0]
    out = []
    for part in re.split(r",(?![^{]*\})", main):
        part = part.strip().rstrip(".").replace(" ", "")
        if not part:
            continue
        m = re.match(r"(.*)\{([^}]*)\}(.*)", part)
        out += [m.group(1) + x + m.group(3) for x in m.group(2).split(",")] if m else [part]
    return out


def parse_deps(raw):
    if raw.startswith("none"):
        return []
    raw = re.sub(r"T(\d\d)a-c", lambda m: f"T{m.group(1)}a, T{m.group(1)}b, T{m.group(1)}c", raw.split(";")[0])
    return re.findall(TASK_ID, raw)


def id_key(tid):
    m = re.match(r"T(\d\d)([a-z]?)(?:-(\d))?", tid)
    return int(m.group(1)), m.group(2), m.group(3) or ""


def load(md):
    """Everything the checks and generators need, parsed from DESIGN.md."""
    roster = {}
    for c in table_rows(md, "| ID | Name | Role | Slug"):
        roster[c[0]] = {"name": c[1], "role": c[2], "slug": c[3].strip("`"), "covers": c[4]}
    items = {}
    for c in table_rows(md, "| Task | Primary Agent"):
        m = re.match(r"\*\*(" + TASK_ID + r")\*\* (.+) \(([^;]+); (\w+)\)$", c[0])
        items[m.group(1)] = {"title": m.group(2), "where": m.group(3), "size": m.group(4),
                             "primary": re.match(r"A\d\d", c[1]).group(0), "support_text": c[2],
                             "support": re.findall(r"A\d\d", c[2]), "owns": c[3], "deps_text": c[4],
                             "deps": parse_deps(c[4]), "deliverable": c[5]}
    gates = {c[0]: {"checks": c[1], "reviewers": re.findall(r"A\d\d", c[2])}
             for c in table_rows(md, "| Task | Verified before handoff")}
    directory = {}
    body = section(md, "### 9.6 Agent Directory", "### 9.7")
    for block in re.split(r"\n(?=\*\*A\d\d )", body)[1:]:
        aid = block[2:5]
        fields = {}
        for line in block.splitlines()[1:]:
            m = re.match(r"- ([A-Z][\w ]+?): (.*)", line)
            if m:
                fields[m.group(1)] = m.group(2)
        directory[aid] = {"heading": block.splitlines()[0], **fields}
    manifest = defaultdict(set)
    code = section(md, "### 9.7", "### 9.8").split("```")[1]
    wave = None
    for line in code.splitlines():
        m = re.match(r"W(\d)\s", line)
        if m:
            wave = int(m.group(1))
        for slug, tid, again in re.findall(r"([a-z-]+)->(" + TASK_ID + r")( \(pass 2\))?", line):
            if not again:
                manifest[wave].add((tid, slug))
    return {"roster": roster, "items": items, "gates": gates, "directory": directory, "manifest": manifest}


def waves(items):
    level = {}

    def depth(t):
        if t not in level:
            level[t] = 0 if not items[t]["deps"] else 1 + max(depth(d) for d in items[t]["deps"])
        return level[t]
    for t in items:
        depth(t)
    return level


def brief_name(tid, item):
    slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")
    return f"{tid}-{slug[:48].rstrip('-')}.md"


def who(roster, aid):
    r = roster[aid]
    return f"{r['name']}, {aid}"


def read_first(tid):
    for prefix, sections in READ_FIRST:
        if tid.startswith(prefix):
            return sections
    return "1-10"


def render_brief(data, tid, level):
    roster, items, gates = data["roster"], data["items"], data["gates"]
    it = items[tid]
    prim = roster[it["primary"]]
    blocks = sorted((t for t in items if tid in items[t]["deps"]), key=id_key)
    deps = ", ".join(f"{d} ({who(roster, items[d]['primary'])})" for d in it["deps"]) or "none"
    extra = it["deps_text"].split(";", 1)[1].strip() if ";" in it["deps_text"] else ""
    owns = "\n".join(f"- `{expand(p)}`" for p in split_paths(it["owns"]))
    main, _, rest = it["owns"].partition(";")
    notes = re.findall(r"\(([^)]*)\)", main) + ([rest.strip()] if rest.strip() else [])
    note = expand("Also: " + "; ".join(notes) + ".") if notes else ""
    gate = gates[tid]
    reviewers = ", ".join(f"{roster[a]['name']} ({a})" for a in gate["reviewers"])
    return f"""{GENERATED}
# {tid} {it['title']}

| | |
|---|---|
| Primary agent | **{prim['name']}** ({it['primary']}, {prim['role']}); spawn as `{prim['slug']}` |
| Supporting | {it['support_text']} |
| Where / size | {it['where']} / {it['size']} (C cloud agent, PC your machine with the connectome, ST a Roblox Studio step) |
| Wave | {NOTES.get(tid, 'W%d' % level[tid])} |
| Depends on | {deps}{'; ' + extra if extra else ''} |
| Blocks | {', '.join(blocks) or 'nothing (end of a chain)'} |
| Reviewer | {reviewers} |

## Deliverable

{expand(it['deliverable'])}

## Owns (edit only these)

{owns}
{chr(10) + note + chr(10) if note else ''}
## Read first

- [DESIGN.md](../DESIGN.md), sections {read_first(tid)}.
- [CONTRACTS.md](../CONTRACTS.md), the shared types and remotes.
- Your agent file `.claude/agents/{prim['slug']}.md`.
- The handoff reports of the items you depend on.

## Handoff checks (paste each command and its result in the PR)

{expand(gate['checks'])}

`CHK` = `bash roblox/scripts/check.sh` (StyLua check, Selene, `lune run tests/run`, every lint in `roblox/tools/lint/`, `rojo build`). `PYT f` = `python -m pytest tests/f`.

The reviewer signs off in the PR; the Lead merges only with this output pasted.

## Rules

{RULES}

## Handoff report (PR description)

{REPORT}
"""


def cap(text):
    return text[:1].upper() + text[1:]


def render_agent(data, aid, level):
    roster, items, d = data["roster"], data["items"], data["directory"][aid]
    r = roster[aid]
    mine = sorted((t for t in items if items[t]["primary"] == aid), key=lambda t: (level[t], id_key(t)))
    briefs = "\n".join(f"- {t}: `docs/roblox/tasks/{brief_name(t, items[t])}`" for t in mine)
    def quoted(text):
        return '"' + text.replace("\\", "\\\\").replace('"', "'") + '"'
    if aid == "A00":
        desc = (f"{r['name']}, the Lead of the Fly Roulette build. Runs the waves in docs/roblox/TASKS.md, spawns "
                "specialists, enforces handoff gates and rules on change requests. Normally the main session, not a subagent.")
        head = f"---\nname: {r['slug']}\ndescription: {quoted(desc)}\n---\n"
        briefs = "- none as primary; see the gates you review in `docs/roblox/TASKS.md`"
    else:
        purpose = d["Purpose"].split(":", 1)[-1].strip()
        desc = (f"{r['name']}, {r['role']} specialist for the Fly Roulette Roblox game. "
                f"Use for work items {', '.join(mine)}: {purpose}")
        head = (f"---\nname: {r['slug']}\ndescription: {quoted(desc)}\n"
                f"tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch\n---\n")
    return f"""{head}{GENERATED}

You are **{r['name']}** ({aid}), {r['role']} on the Fly Roulette team. The design is `docs/roblox/DESIGN.md`; the shared contracts are `docs/roblox/CONTRACTS.md`.

## Your job

{cap(expand(d['Purpose']))}

## Your work items

{cap(expand(d['Tasks']))}

Briefs:
{briefs}

## Paths you own

{expand(d['Owns'])}

May edit: {expand(d['May edit'])}

## Inputs and outputs

Inputs: {expand(d['Inputs'])}

## Definition of done

{cap(d['Handoff when'])} Every item's handoff checks are in its brief.

## Rules

{RULES}

## Handoff report (PR description)

{REPORT}
"""


def render_tasks(md):
    parts = [section(md, "### 9.1 Operating model", "### 9.3"), section(md, "### 9.4 Assignment table", "### 9.6"),
             section(md, "### 9.7 Execution waves", "### 9.9")]
    return f"{GENERATED}\n# Fly Roulette: work items, gates and waves\n\nExtracted from [DESIGN.md](DESIGN.md) section 9. Briefs: [tasks/](tasks/).\n\n" + "\n".join(parts)


def render_agents(md):
    parts = [section(md, "### 9.3 The roster", "### 9.4"), section(md, "### 9.6 Agent Directory", "### 9.7")]
    return f"{GENERATED}\n# Fly Roulette: agents\n\nExtracted from [DESIGN.md](DESIGN.md) section 9. Definitions: `.claude/agents/<slug>.md`.\n\n" + "\n".join(parts)


def expected_files(md, data):
    """Every derived file: {absolute path: content}."""
    level = waves(data["items"])
    files = {os.path.join(HERE, "TASKS.md"): render_tasks(md), os.path.join(HERE, "AGENTS.md"): render_agents(md)}
    for tid, item in data["items"].items():
        files[os.path.join(TASKS_DIR, brief_name(tid, item))] = render_brief(data, tid, level)
    for aid, r in data["roster"].items():
        files[os.path.join(AGENTS_DIR, r["slug"] + ".md")] = render_agent(data, aid, level)
    return files


def find_cycle(items):
    state = {}

    def visit(t, path):
        if state.get(t) == 1:
            return path[path.index(t):] + [t]
        if state.get(t) == 2:
            return None
        state[t] = 1
        for d in items[t]["deps"]:
            if d in items:
                found = visit(d, path + [t])
                if found:
                    return found
        state[t] = 2
        return None
    for t in items:
        found = visit(t, [])
        if found:
            return found
    return None


def check(md, data):
    """Every consistency rule from DESIGN.md section 10. Returns a list of problems."""
    roster, items, gates, directory = data["roster"], data["items"], data["gates"], data["directory"]
    bad = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            if len({len(cells(x)) for x in lines[i:j]}) > 1:
                bad.append(f"DESIGN.md line {i + 1}: table rows have different column counts")
            i = j
        else:
            i += 1
    names = [r["name"] for r in roster.values()]
    slugs = [r["slug"] for r in roster.values()]
    if len(set(names)) != len(names) or len(set(slugs)) != len(slugs):
        bad.append("roster: names and slugs must be unique")
    for aid, r in roster.items():
        if not re.fullmatch(r"[a-z]+(-[a-z]+)+", r["slug"]) or not r["slug"].startswith(r["name"].lower() + "-"):
            bad.append(f"roster {aid}: slug {r['slug']} must be <name>-<role> in lowercase")
    for tid, it in items.items():
        for aid in [it["primary"]] + it["support"]:
            if aid not in roster:
                bad.append(f"{tid}: unknown agent {aid}")
        for dep in it["deps"]:
            if dep not in items:
                bad.append(f"{tid}: depends on unknown item {dep}")
        for dep, aid in re.findall(r"(" + TASK_ID + r"|T\d\da-c) \((A\d\d)\)", it["deps_text"]):
            real = items.get(dep.replace("a-c", "a"))
            if real and real["primary"] != aid:
                bad.append(f"{tid}: dependency {dep} is owned by {real['primary']}, not {aid}")
    if bad:
        return bad
    cycle = find_cycle(items)
    if cycle:
        return bad + ["dependency cycle: " + " -> ".join(cycle)]
    level = waves(items)
    computed = defaultdict(set)
    for tid, w in level.items():
        computed[w].add((tid, roster[items[tid]["primary"]]["slug"]))
    for w in sorted(set(computed) | set(data["manifest"])):
        if computed[w] != data["manifest"][w]:
            bad.append(f"wave W{w}: manifest {sorted(data['manifest'][w])} but the dependencies give {sorted(computed[w])}")
    primaries = defaultdict(list)
    for tid, it in items.items():
        primaries[it["primary"]].append(tid)
    for aid in roster:
        if aid != "A00" and not primaries[aid]:
            bad.append(f"{aid} {roster[aid]['name']} has no primary work item")
    owned = [(it["primary"], tid, p) for tid, it in items.items() for p in split_paths(it["owns"])]
    for (a1, t1, p1), (a2, t2, p2) in itertools.combinations(owned, 2):
        q1, q2 = p1.rstrip("/"), p2.rstrip("/")
        if a1 != a2 and (q1 == q2 or q1.startswith(q2 + "/") or q2.startswith(q1 + "/")):
            bad.append(f"ownership overlap: {t1} {p1} and {t2} {p2}")
    for aid, r in roster.items():
        d = directory.get(aid)
        if not d:
            bad.append(f"directory: no entry for {aid}")
            continue
        if f"**{aid} {r['name']}, " not in d["heading"] or f"`{r['slug']}`" not in d["heading"]:
            bad.append(f"directory {aid}: heading must show {r['name']} and `{r['slug']}`")
        if aid == "A00":
            continue
        table = {p for a, _, p in owned if a == aid}
        if set(split_paths(d.get("Owns", ""))) != table:
            bad.append(f"directory {aid}: owned paths differ from the assignment table")
        listed = set(re.findall(TASK_ID, re.split(r"Reviewer|Supporting", d.get("Tasks", ""))[0]))
        if listed != set(primaries[aid]):
            bad.append(f"directory {aid}: primary items {sorted(listed)} but the table says {sorted(primaries[aid])}")
    if set(gates) != set(items):
        bad.append(f"handoff gates: missing {sorted(set(items) - set(gates))}, extra {sorted(set(gates) - set(items))}")
    for tid, g in gates.items():
        for aid in g["reviewers"]:
            if aid not in roster:
                bad.append(f"gate {tid}: unknown reviewer {aid}")
            elif tid in items and aid == items[tid]["primary"]:
                bad.append(f"gate {tid}: the primary agent cannot review its own item")
            elif aid != "A00" and tid not in directory.get(aid, {}).get("Tasks", ""):
                bad.append(f"directory {aid}: missing review of {tid}")
    return bad


def check_files(md, data):
    """Derived files exist, are current, and nothing stale is left; relative links resolve."""
    bad = []
    expected = expected_files(md, data)
    for path, text in expected.items():
        rel = os.path.relpath(path, REPO)
        if not os.path.exists(path):
            bad.append(f"{rel}: missing (run with --write)")
        elif open(path, encoding="utf-8").read() != text:
            bad.append(f"{rel}: out of date (run with --write)")
    for folder in (TASKS_DIR, AGENTS_DIR):
        if os.path.isdir(folder):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if name.endswith(".md") and path not in expected and GENERATED in open(path, encoding="utf-8").read():
                    bad.append(f"{os.path.relpath(path, REPO)}: stale generated file")
    for root, _, files in os.walk(HERE):
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", open(path, encoding="utf-8").read()):
                if "://" not in target and not os.path.exists(os.path.normpath(os.path.join(root, target))):
                    bad.append(f"{os.path.relpath(path, REPO)}: broken link {target}")
    return bad


def write(md, data):
    expected = expected_files(md, data)
    for folder in (TASKS_DIR, AGENTS_DIR):
        os.makedirs(folder, exist_ok=True)
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if name.endswith(".md") and path not in expected and GENERATED in open(path, encoding="utf-8").read():
                os.remove(path)
    for path, text in expected.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return len(expected)


def main(argv):
    md = open(DESIGN, encoding="utf-8").read()
    data = load(md)
    if "--write" in argv:
        print(f"wrote {write(md, data)} files")
    problems = check(md, data)
    if not problems:
        problems = check_files(md, data)
    level = waves(data["items"]) if not problems else {}
    for p in problems:
        print("FAIL", p)
    if problems:
        return 1
    sizes = [sum(1 for w in level.values() if w == k) for k in range(max(level.values()) + 1)]
    print(f"OK: {len(data['items'])} work items, {len(data['roster'])} agents, waves {sizes}, "
          f"{len(expected_files(md, data))} derived files current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
