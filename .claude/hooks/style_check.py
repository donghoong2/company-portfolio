#!/usr/bin/env python3
"""PostToolUse 훅: deck.json·resume.json을 고치거나 빌드하면 문장 스타일 경고를 Claude에게 보여준다.

- Write/Edit/MultiEdit로 companies/<slug>/(deck|resume).json을 고치면: Edit은 바꾼 글자가 들어간 필드만, Write는 파일 전체.
- Bash로 build_deck.js·build_resume.js·build_resume_docx.js를 돌리거나 deck/resume.json을 스크립트로 고치면: 파일 전체.
- 경고만 한다(항상 exit 0). 경고는 additionalContext로 Claude에게, 한 줄 요약은 systemMessage로 사용자에게.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_CHARS = 6000
WRITE_HINT = re.compile(r"json\.dump|write_text|\.write\(|sed -i|>\s*\S*companies/")


def targets(tool: str, ti: dict) -> tuple[dict[str, set[str]], str | None]:
    found: dict[str, set[str]] = {}
    only = None
    if tool in ("Write", "Edit", "MultiEdit"):
        m = re.search(r"(?:^|/)companies/([^/]+)/(deck|resume)\.json$", ti.get("file_path", ""))
        if m:
            found[m.group(1)] = {f"{m.group(2)}.json"}
            if tool == "Edit":
                only = ti.get("new_string", "")
            elif tool == "MultiEdit":
                only = "\n".join(e.get("new_string", "") for e in ti.get("edits", []))
    elif tool == "Bash":
        cmd = ti.get("command", "")
        for m in re.finditer(r"build_(deck|resume|resume_docx)\.js\s+(?:\S*/)?companies/([^/\s'\"]+)", cmd):
            found.setdefault(m.group(2), set()).add("deck.json" if m.group(1) == "deck" else "resume.json")
        if WRITE_HINT.search(cmd):
            for m in re.finditer(r"companies/([^/\s'\"]+)/(deck|resume)\.json", cmd):
                found.setdefault(m.group(1), set()).add(f"{m.group(2)}.json")
    return found, only


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    found, only = targets(data.get("tool_name", ""), data.get("tool_input") or {})
    if not found:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".")
    checker = root / "scripts/check_style.py"
    if not checker.is_file():
        return 0

    reports, total = [], 0
    for slug, files in sorted(found.items()):
        for name in sorted(files):
            if not (root / "companies" / slug / name).is_file():
                continue
            cmd = [sys.executable, str(checker), f"companies/{slug}", "--file", name]
            tmp = None
            if only is not None:
                tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
                tmp.write(only)
                tmp.close()
                cmd += ["--only-from", tmp.name]
            try:
                out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=30).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
            finally:
                if tmp:
                    os.unlink(tmp.name)
            m = re.search(r"문장 스타일 경고 (\d+)건", out)
            if m:
                total += int(m.group(1))
                reports.append(out.strip())

    if not total:
        return 0
    text = "\n\n".join(reports)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n… (잘림 — 전체는 python3 scripts/check_style.py companies/<slug>)"
    scope = "고친 문장" if only is not None else ", ".join(f"companies/{s}" for s in sorted(found))
    print(json.dumps({
        "systemMessage": f"문장 스타일 경고 {total}건 ({scope}) — 빌드는 그대로 진행",
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": "[style-check 훅] 문장 스타일 경고 (경고만, 빌드는 막지 않음). "
                                 "writing-style.md 기준으로 문장을 다듬되 사실·수치는 바꾸지 않는다.\n" + text,
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
