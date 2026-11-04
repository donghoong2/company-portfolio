#!/usr/bin/env python3
"""deck.json(또는 resume.json)의 수치가 지원자 프로필에 실제로 있는지 검사한다.

사용법: check_facts.py companies/<slug> [--file resume.json]                 수치 검사
        check_facts.py companies/<slug> [--file resume.json] --find "<문장>"  문장이 어느 슬라이드·섹션에 있는지 (리뷰 인용 확인용)

- --file 기본값은 deck.json(slides[]). resume.json은 sections[]를 검사한다 (인적사항은 profile/personal.json이라 검사 대상 아님).

- 사실 출처: profile/notion_profile.md, profile/supplements.md(있으면)
- 참고 자료: profile/team_notion*.md, profile/github/ 아래 문서(.md). 여기에만 있는 수치는 통과시키되
  "참고 자료에만 있음"으로 따로 보여준다 — 팀 성과·팀 문서 수치로 표기했는지 직접 확인한다.
- 덱의 모든 문자열(notes 포함, meta 제외)에서 숫자를 뽑아 출처의 숫자 집합과 대조한다.
  콤마·앞자리 0은 무시하고, 날짜(2026.05, 2026-05-01)는 연·월·일로 나눠 비교한다.
- 출처 수치에서 계산한 값(감소율 등)은 deck.json 최상위 "derived"에 근거와 함께 적으면 통과한다:
  "derived": [{ "value": "42.2", "from": "52.6분 → 30.4분" }]   (from의 수치도 출처에 있어야 한다)
종료 코드: 통과 0, 출처에 없는 수치 있음 1, 사용법 오류 2.
"""
import json
import re
import sys
from pathlib import Path

SOURCES = [Path("profile/notion_profile.md"), Path("profile/supplements.md")]


def reference_files():
    files = sorted(Path("profile").glob("team_notion*.md"))
    gh = Path("profile/github")
    if gh.is_dir():
        files += sorted(p for p in gh.rglob("*.md") if ".git" not in p.parts)
    return files
SKIP_KEYS = {"type", "no", "image", "path", "kind"}
DATE = re.compile(r"(?<!\d)(\d{4})[.\-/](\d{1,2})(?:[.\-/](\d{1,2}))?(?!\d)")
NUM = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\d])")


def norm(i: str, frac: str | None) -> str:
    i = i.replace(",", "").lstrip("0") or "0"
    frac = (frac or "").rstrip("0")
    return f"{i}.{frac}" if frac else i


def numbers(text: str) -> list[str]:
    out = []
    for m in DATE.finditer(text):
        out += [norm(g, None) for g in m.groups() if g]
    text = DATE.sub(" ", text)
    out += [norm(m.group(1), m.group(2)) for m in NUM.finditer(text)]
    return out


def strings(node, path=""):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, v in node.items():
            if k not in SKIP_KEYS:
                yield from strings(v, f"{path}.{k}" if path else k)


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def usage() -> int:
    print("\n".join(__doc__.strip().splitlines()[2:4]))
    return 2


def main(argv: list[str]) -> int:
    name, find, rest = "deck.json", None, []
    i = 0
    while i < len(argv):
        if argv[i] in ("--file", "--find"):
            if i + 1 >= len(argv):
                return usage()
            if argv[i] == "--file":
                name = argv[i + 1]
            else:
                find = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if len(rest) != 1 or not (Path(rest[0]) / name).is_file():
        return usage()
    deck = json.loads((Path(rest[0]) / name).read_text(encoding="utf-8"))
    if "slides" in deck:
        slides, unit = deck["slides"], "슬라이드"
    else:
        slides, unit = deck.get("sections", []), "섹션"

    if find is not None:
        q = squash(find)
        hits = [i for i, s in enumerate(slides, 1) if any(q in squash(t) for _, t in strings(s))]
        print(f"있음: {unit} {', '.join(map(str, hits))}" if hits else "없음 (이미지 속 글자일 수 있으니 PNG로 확인)")
        return 0 if hits else 1

    src = [p for p in SOURCES if p.is_file()]
    if not src:
        print("사실 출처가 없다: profile/notion_profile.md")
        return 2
    known = set()
    for p in src:
        known.update(numbers(p.read_text(encoding="utf-8")))

    ref = set()
    refs = reference_files()
    for p in refs:
        ref.update(numbers(p.read_text(encoding="utf-8", errors="ignore")))
    ref -= known

    ok = True
    derived = set()
    for d in deck.get("derived", []):
        missing = [n for n in numbers(d.get("from", "")) if n not in known]
        if missing or not d.get("from"):
            ok = False
            print(f"derived 근거 불충분: {d.get('value')} ← \"{d.get('from', '')}\" (출처에 없음: {', '.join(missing) or 'from 비어 있음'})")
        else:
            derived.add(norm(*(d["value"].split(".") + [None])[:2]))
            print(f"계산값: {d['value']} ← {d['from']}")

    bad = 0
    for i, s in enumerate(slides, 1):
        for path, text in strings(s):
            nums = {n for n in numbers(text) if n not in known and n not in derived}
            only_ref = sorted(n for n in nums if n in ref)
            miss = sorted(nums - set(only_ref))
            if only_ref:
                print(f"참고 자료에만 있음: {unit} {i} ({s.get('type')}) {path} — {', '.join(only_ref)} | \"{text[:80]}\" → 팀 성과로 표기했는지 확인")
            if miss:
                bad += 1
                print(f"출처에 없음: {unit} {i} ({s.get('type')}) {path} — {', '.join(miss)} | \"{text[:80]}\"")
    print(f"사실 출처: {', '.join(map(str, src))}" + (f" · 참고 자료 {len(refs)}개" if refs else ""))
    if bad or not ok:
        print(f"실패: 출처에서 확인되지 않는 수치 {bad}곳")
        return 1
    print(f"통과: {name}의 모든 수치가 출처에 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
