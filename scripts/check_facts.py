#!/usr/bin/env python3
"""deck.json의 수치가 지원자 프로필에 실제로 있는지 검사한다.

사용법: check_facts.py companies/<slug>                 수치 검사
        check_facts.py companies/<slug> --find "<문장>"  문장이 덱 어느 슬라이드에 있는지 (리뷰 인용 확인용)

- 사실 출처: profile/notion_profile.md, profile/supplements.md(있으면)
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


def main(argv: list[str]) -> int:
    if not argv or not (Path(argv[0]) / "deck.json").is_file():
        print(__doc__.strip().splitlines()[2])
        print(__doc__.strip().splitlines()[3])
        return 2
    deck = json.loads((Path(argv[0]) / "deck.json").read_text(encoding="utf-8"))
    slides = deck.get("slides", [])

    if len(argv) == 3 and argv[1] == "--find":
        q = squash(argv[2])
        hits = [i for i, s in enumerate(slides, 1) if any(q in squash(t) for _, t in strings(s))]
        print(f"있음: 슬라이드 {', '.join(map(str, hits))}" if hits else "없음 (이미지 속 글자일 수 있으니 PNG로 확인)")
        return 0 if hits else 1

    src = [p for p in SOURCES if p.is_file()]
    if not src:
        print("사실 출처가 없다: profile/notion_profile.md")
        return 2
    known = set()
    for p in src:
        known.update(numbers(p.read_text(encoding="utf-8")))

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
            miss = sorted({n for n in numbers(text) if n not in known and n not in derived})
            if miss:
                bad += 1
                print(f"출처에 없음: 슬라이드 {i} ({s.get('type')}) {path} — {', '.join(miss)} | \"{text[:80]}\"")
    print(f"사실 출처: {', '.join(map(str, src))}")
    if bad or not ok:
        print(f"실패: 출처에서 확인되지 않는 수치 {bad}곳")
        return 1
    print("통과: 덱의 모든 수치가 출처에 있다")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
