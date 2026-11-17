#!/usr/bin/env python3
"""PreToolUse hook: predicts what an Edit/MultiEdit/Write will break or change before it lands (regex + git grep; fails open)."""
import difflib, fnmatch, json, os, re, subprocess, sys
from pathlib import Path

ASK_AT = os.environ.get("IMPACT_ASK_AT", "NONE").upper()  # NONE (always ask, default) | LOW | MEDIUM | HIGH | CRITICAL | NEVER
PROTECTED = os.environ.get("IMPACT_PROTECTED", "*/migrations/*,*/auth/*,*/security/*,*.proto,*/.env*").split(",")
LEVELS, MAX_SITES = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"], 10
EXT = {".py": "py", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".java": "java", ".cs": "java", ".go": "go"}
DEFS = {  # groups: (name, params); JS arrow functions use groups 3 and 4
    "py": r"^[ \t]*(?:async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->[^:\n]*)?:", "go": r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(([^)]*)\)",
    "js": r"function\s+(\w+)\s*\(([^)]*)\)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
    "java": r"^[ \t]*(?:(?:public|private|protected|internal|static|final|async|override|virtual)\s+)*[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*(?:throws[^{]*)?\{"}
CONST = re.compile(r"^[ \t]*(?:export\s+)?(?:const\s+|(?:public\s+)?static\s+final\s+\w+\s+)?([A-Z][A-Z0-9_]+)\s*(?::[^=\n]+)?=\s*([^=\n][^\n]*?);?\s*$", re.M)
IMPORT = re.compile(r"^\s*(?:import|from|using|#include)\b|\brequire\s*\(|\bimport\s*\(")
TEST = re.compile(r"(^|/)(tests?|__tests__|specs?)/|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$|Tests?\.\w+$")
WHY = (("return values", r"\breturn\b"), ("raises/throws", r"\b(raise|throw)\b"), ("conditions", r"\b(if|elif|else|switch|case)\b"),
       ("side effects/I-O", r"\b(open|write|save|send|delete|insert|update|fetch|requests)\b"))
ERR = {"py": ("ImportError/NameError at runtime", "TypeError at runtime"), "java": ("compile error",) * 2, "go": ("compile error",) * 2,
       "js": ("ReferenceError or undefined import", "TS compile error (plain JS: undefined args)")}  # (missing symbol, bad call)
def norm(t): return "\n".join(l.rstrip() for l in t.splitlines() if l.strip())
def word(n): return re.compile(r"(?<![\w$])" + re.escape(n) + r"(?![\w$])")
def split(s):  # split on top-level commas
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += (ch in "([{") - (ch in ")]}")
        if ch == "," and depth == 0: out.append(cur); cur = ""
        else: cur += ch
    return [x.strip() for x in out + [cur] if x.strip()]
def symbols(text, lang):  # -> {name: (params, normalized body)}
    ms, out = list(re.finditer(DEFS[lang], text, re.M | re.S)), {}
    for i, m in enumerate(ms):
        g = m.groups(); name, prm = (g[0], g[1]) if g[0] else (g[2], g[3])
        if not name or name in out or name in ("if", "for", "while", "switch", "catch", "return", "else", "new"): continue
        body = text[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(text)]
        if lang == "py" and (cut := re.search(r"\n(?=\S)", body)): body = body[:cut.start()]
        out[name] = (" ".join(re.sub(r"#[^\n]*|//[^\n]*", "", prm).split()), norm(body))
    return out
def params(p, lang):  # -> (names, required_count, accepts_extra_positional)
    names, req, var = [], 0, False
    for a in split(p):
        if a in ("self", "cls", "/", "*") or a.startswith(("*", "...")): var |= a not in ("self", "cls", "/", "*"); continue
        toks = re.split(r"[:=]", a)[0].split() or ["?"]
        names.append((toks[-1] if lang == "java" else toks[0]).rstrip("?"))
        req += "=" not in a and not toks[0].endswith("?")
    return names, req, var
def check_call(line, name, sig, lang):  # -> problem text, "" if compatible, None if it cannot tell
    if not (m := re.search(r"(?<![\w$])" + re.escape(name) + r"\s*\(", line)): return None
    depth, i = 1, m.end()
    while i < len(line) and depth: depth += (line[i] in "([{") - (line[i] in ")]}"); i += 1
    if depth: return None  # call spans several lines
    args = split(line[m.end():i - 1])
    if any(a.startswith(("*", "...")) for a in args): return None
    kws = {a.split("=")[0].strip() for a in args if lang == "py" and re.match(r"^\w+\s*=(?!=)", a)}
    pos, (names, req, var) = len(args) - len(kws), sig
    probs = [f"missing required {n}" for n in names[pos:req] if n not in kws]
    if pos > len(names) and not var: probs.append(f"passes {pos} args, now takes {len(names)}")
    return "; ".join(probs + [f"unknown keyword {k}" for k in kws - set(names)])
def grep(root, names):  # -> [(file, line, text)] for whole-word matches of any name
    cmd = ["git", "grep", "-n", "-I", "-w", "-F", "--untracked"] + [x for n in names for x in ("-e", n)]
    try: r = subprocess.run(cmd + ["--", ".", ":(exclude).claude"], cwd=root, capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired): return []
    rows = [l.split(":", 2) for l in r.stdout.decode("utf-8", "replace").splitlines()]
    return [(f, int(n), t.strip()) for f, n, t in (x for x in rows if len(x) == 3 and x[1].isdigit())]
def simulate(tool, ti, text):  # -> file text after the edit, or None if the edit would fail
    if tool == "Write": return ti.get("content", "").replace("\r\n", "\n")
    for e in (ti.get("edits") or []) if tool == "MultiEdit" else [ti]:
        o, n = (e.get("old_string") or "").replace("\r\n", "\n"), (e.get("new_string") or "").replace("\r\n", "\n")
        if not o or o not in text: return None
        text = text.replace(o, n) if e.get("replace_all") else text.replace(o, n, 1)
    return text

def main():
    d = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    tool, ti = d.get("tool_name"), d.get("tool_input") or {}
    if tool not in ("Edit", "MultiEdit", "Write") or not ti.get("file_path"): return
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or d.get("cwd") or ".").resolve()
    path = (root / ti["file_path"]).resolve()
    if not path.is_relative_to(root): return  # outside the project
    rel, lang = path.relative_to(root).as_posix(), EXT.get(path.suffix.lower())
    old = path.read_bytes().decode("utf-8", "replace").replace("\r\n", "\n") if path.exists() else ""
    if (new := simulate(tool, ti, old)) is None or new == old: return
    o, n = (symbols(old, lang), symbols(new, lang)) if lang else ({}, {})
    oc, nc = ({m[1]: m[2].strip() for m in CONST.finditer(t)} for t in (old, new)) if lang else ({}, {})
    removed, added = [s for s in o if s not in n], [s for s in n if s not in o]
    renames = {r: a for r in removed for a in added if difflib.SequenceMatcher(None, o[r][1], n[a][1]).ratio() > 0.8}
    sig = [s for s in o if s in n and o[s][0] != n[s][0]]
    body = [s for s in o if s in n and s not in sig and o[s][1] != n[s][1]]
    cchg, crem = [c for c in oc if c in nc and oc[c] != nc[c]], [c for c in oc if c not in nc]
    indirect = [s for s in o if s in n and s not in sig + body and any(word(c).search(n[s][1]) for c in cchg)]
    stem = path.parent.name if path.stem in ("__init__", "index") else path.stem
    hits = grep(root, sorted({x for x in removed + sig + body + indirect + cchg + crem + [stem] if len(x) >= 3}))
    def refs(name, calls=False):  # references in other files, skipping definitions (and imports if calls=True)
        is_def = re.compile(r"\b(?:def|function|func|class)\s+" + re.escape(name) + r"\b")
        return [(f, l, t) for f, l, t in hits if f != rel and word(name).search(t) and not is_def.search(t) and not (calls and IMPORT.search(t))]
    F = []  # findings: (kind, title, effect, [(file, line, text, note)], weight, breaking_count)
    for s in removed:
        sites, new_name = refs(s), renames.get(s); note = f"replace with {new_name}" if new_name else "symbol no longer exists"
        F.append(("BREAKING" if sites else "INFO", f"{s} " + (f"renamed to {new_name}" if new_name else "removed"),
                  f"{ERR[lang][0]} at {len(sites)} reference(s)" if sites else "no references outside this file",
                  [x + (note,) for x in sites], 3 * len(sites), len(sites)))
    for s in sig:
        new_sig, bad, unsure, ok = params(n[s][0], lang), [], [], 0
        for f, l, t in refs(s, calls=True):
            p = check_call(t, s, new_sig, lang)
            if p is None: unsure.append((f, l, t, "verify manually"))
            elif p: bad.append((f, l, t, p))
            else: ok += 1
        F.append(("BREAKING" if bad else "SIGNATURE", f"{s}({o[s][0]}) -> {s}({n[s][0]})",
                  f"{ERR[lang][1]} at {len(bad)} call(s); {len(unsure)} to verify; {ok} still compatible"
                  + ("; body also changed" if o[s][1] != n[s][1] else ""), bad + unsure, 3 * len(bad) + len(unsure), len(bad)))
    for s in body + indirect:
        diff = [l for l in difflib.unified_diff(o[s][1].splitlines(), n[s][1].splitlines(), lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        why = [w for w, rx in WHY if any(re.search(rx, l) for l in diff)]
        if s in indirect: why = ["uses changed constant " + ", ".join(c for c in cchg if word(c).search(n[s][1]))]
        sites = refs(s, calls=True); files = {f for f, _, _ in sites}
        F.append(("BEHAVIOR", f"{s}: behavior change ({', '.join(why) or 'logic'})",
                  f"callers in {len(files)} file(s) will get different results" if files else "no callers outside this file",
                  [x + ("check expected result",) for x in sites], len(files), 0))
    for c in cchg + crem:
        sites, kept = refs(c), c in nc
        F.append(("CONSTANT" if kept else "BREAKING", f"{c}: {oc[c]} -> {nc.get(c, '(removed)')}", f"{len(sites)} usage(s) affected",
                  [x + ("uses this constant",) for x in sites], len({f for f, _, _ in sites}) if kept else 3 * len(sites), 0 if kept else len(sites)))
    importers = sorted({f for f, _, t in hits if f != rel and word(stem).search(t) and IMPORT.search(t)})
    tests = sorted({f for f in importers + [x[0] for k in F for x in k[3]] if TEST.search(f)})
    protected = any(fnmatch.fnmatch("/" + rel, g.strip()) for g in PROTECTED if g.strip())
    score = sum(k[4] for k in F) + min(len(importers), 20) // 2 + 20 * protected
    level, n_break = LEVELS[sum(score >= t for t in (1, 5, 15, 30))], sum(k[5] for k in F)
    def render(max_sites):
        out = [f"=== IMPACT ANALYSIS: {rel} ({tool}) | Risk {level}{' | PROTECTED PATH' if protected else ''} ==="]
        out += [] if F else ["No symbol-level changes detected."]
        for i, (kind, title, effect, sites, _, _) in enumerate(sorted(F, key=lambda k: -k[4]), 1):
            out.append(f"{i}. [{kind}] {title}")
            if sites:  # Effect and call sites only when something outside this file is affected
                out.append(f"   Effect: {effect}")
                out += [f"     - {f}:{l}  {t[:80]}  <- {note}" for f, l, t, note in sites[:max_sites]] + [f"     (+{len(sites) - max_sites} more)"] * (len(sites) > max_sites)
        return "\n".join(out + (["TESTS LIKELY AFFECTED: " + ", ".join(tests[:MAX_SITES])] if tests else []))
    report = render(MAX_SITES)
    prompt = next((r for r in (render(m) for m in (MAX_SITES, 5, 3, 1, 0)) if len(r) <= 3000), render(0)[:3000])
    log_dir = root / ".claude" / "hooks"; log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "impact-latest.md").write_text(report + "\n", encoding="utf-8")
    with open(log_dir / "impact.log", "a", encoding="utf-8") as fh: fh.write(json.dumps({"file": rel, "risk": level, "breaking": n_break, "tests": tests}) + "\n")
    if level == "NONE" and ASK_AT != "NONE": return
    hso = {"hookEventName": "PreToolUse", "additionalContext": report + "\n\nINSTRUCTIONS: Before each edit, show the user this "
           "impact analysis and wait for approval. Fix every BREAKING site in this same task, and run the affected tests afterwards."}
    if protected or (ASK_AT in LEVELS and LEVELS.index(level) >= LEVELS.index(ASK_AT)):
        hso.update(permissionDecision="ask", permissionDecisionReason=prompt)
    print(json.dumps({"systemMessage": f"Impact {level}: {rel}, {n_break} breaking ref(s), {len(tests)} test file(s). "
                      "See .claude/hooks/impact-latest.md", "hookSpecificOutput": hso}))
if __name__ == "__main__":
    try: main()
    except Exception as e:  # analysis failed: still require approval unless asking is disabled
        print(f"impact_analysis skipped: {e}", file=sys.stderr)
        if ASK_AT != "NEVER":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                  "permissionDecisionReason": f"Impact analysis could not run ({e}). Approve this edit without it?"}}))
    sys.exit(0)