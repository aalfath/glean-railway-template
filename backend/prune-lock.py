"""Filter `uv export` output: drop torch, sentence-transformers and every
package only they pull in (CUDA wheels, transformers, scipy, ...). Versions and
environment markers stay exactly as upstream locked them.

Usage: uv export --frozen ... | python prune-lock.py uv.lock > requirements.txt
"""
import re
import sys
import tomllib

DROP = {"torch", "sentence-transformers"}

lock = tomllib.load(open(sys.argv[1], "rb"))
pkgs = {}
for p in lock["package"]:
    pkgs.setdefault(p["name"], []).append(p)


def deps(name):
    out = []
    for p in pkgs.get(name, []):
        for d in p.get("dependencies", []):
            out.append(d["name"])
            for extra in d.get("extra", []):
                for q in pkgs.get(d["name"], []):
                    out += [x["name"] for x in q.get("optional-dependencies", {}).get(extra, [])]
    return out


roots = [n for n, ps in pkgs.items() if any("editable" in p["source"] or "virtual" in p["source"] for p in ps)]
seen, stack = set(), list(roots)
while stack:
    n = stack.pop()
    if n in seen or n in DROP:
        continue
    seen.add(n)
    stack += deps(n)

keep = {re.sub(r"[-_.]+", "-", n).lower() for n in seen}
dropped = 0
for line in sys.stdin:
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", line)
    if m and re.sub(r"[-_.]+", "-", m.group(1)).lower() not in keep:
        dropped += 1
        continue
    if m or not line.strip().startswith(("-e", "./")):
        sys.stdout.write(line)
print(f"# pruned {dropped} packages", file=sys.stderr)
