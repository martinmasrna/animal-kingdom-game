"""Cards change one way only: tools/cards/hq.py. Blocks any other edit of the card data (decks.json, cards.json) or of
the crop tables in static/art.js, so every change respects Martin's locks and lands in his review on the card table.

Wired as a PreToolUse hook from the workspace folder above the game repo (the folder every session starts in), and from
the game repo itself for a session started there. The guarded repo is the one this file lives in. Exit 2 refuses the
tool call and shows the agent the message.
"""
import json
import re
import sys
from pathlib import Path

MSG = ("Cards change only through the card table's tool, so locks hold and Martin reviews every change:\n"
       "  .venv/bin/python tools/cards/hq.py set ID COLUMN VALUE [--note N]   (columns: habitat rarity animal tag strength effect)\n"
       "  .venv/bin/python tools/cards/hq.py level ID COLUMN LEVEL [--note N]\n"
       "  .venv/bin/python tools/cards/hq.py crop ID [--crop x,y,d] [--strip x,y,z] [--full y|reset]\n"
       "  .venv/bin/python tools/cards/hq.py show [ID...]\n"
       "(run from the game repo, the workspace's game/ folder). Its docstring has the rules.")

# only the real repo is guarded; worktrees and scratch copies aren't. Paths are compared as lower-case forward-slash
# strings so the same hook holds on the Mac and on Windows.
GAME = Path(__file__).resolve().parents[2].as_posix().lower() + "/"
DATA = re.compile(r"^" + re.escape(GAME) + r"(tools/card-workbench/decks\.json|animal_kingdom/data/cards\.json)$")
ART = re.compile(r"^" + re.escape(GAME) + r"animal_kingdom/web/static/art\.js$")
# a CROP, STRIP or FULL entry: `  lion: [.651, .373, .55],` or `bat: .349,`
ENTRY = re.compile(r"(^|[\s,{])[a-z0-9_]+: (\[[\d., ]+\]|\.\d+|\d\.\d+)\s*,", re.M)
SHELL_WRITE = re.compile(r"(sed\s+(-[a-zA-Z]*i|--in-place)|perl\s+-[a-zA-Z]*i|>\s*\S*|\btee\b|\bmv\b|\bcp\b|\.write|json\.dump|writeFile|set-content|out-file|add-content)", re.I)
NAMES = re.compile(r"(decks\.json|data/cards\.json|static/art\.js|\bcards\.json|\bart\.js)")


def norm(p: str) -> str:
    return Path(p).resolve().as_posix().lower() if p else ""


def refuse() -> None:
    print(MSG, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    tool, inp = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
    if tool in ("Edit", "Write", "MultiEdit"):
        path = norm(inp.get("file_path", ""))
        if DATA.search(path):
            refuse()
        if ART.search(path):
            texts = [inp.get("content", ""), inp.get("old_string", ""), inp.get("new_string", "")]
            texts += [e.get(k, "") for e in inp.get("edits", []) for k in ("old_string", "new_string")]
            if tool == "Write" or any(ENTRY.search(t or "") for t in texts):
                refuse()
    elif tool in ("Bash", "PowerShell"):
        cmd = inp.get("command", "")
        if "hq.py" in cmd or "convert.py" in cmd or "install.sh" in cmd:
            return
        cmd_n = cmd.replace("\\", "/").lower()
        cwd = norm(ev.get("cwd", ""))
        in_game = cwd + "/" == GAME or (cwd.startswith(GAME) and "/.claude/worktrees/" not in cwd)
        if not in_game and GAME not in cmd_n:
            return    # relative paths here can't reach the real repo's files
        if NAMES.search(cmd) and SHELL_WRITE.search(cmd):
            # reading is fine (cat, grep, git diff); only writes to those files are refused
            for m in re.finditer(r"(>\s*|sed\s+-[a-zA-Z]*i\S*\s+.*?|\btee\s+|\bmv\s+\S+\s+|\bcp\s+\S+\s+|perl\s+-\S+\s+.*?)(\S*(decks\.json|cards\.json|art\.js))", cmd):
                refuse()
            if re.search(r"(\.write|json\.dump|writeFile|set-content|out-file|add-content)", cmd, re.I) and NAMES.search(cmd):
                refuse()


if __name__ == "__main__":
    main()
