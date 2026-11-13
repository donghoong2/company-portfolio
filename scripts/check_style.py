#!/usr/bin/env python3
"""deck.json·resume.json 문장 스타일 검사 (경고만, 빌드는 막지 않는다).

사용법:
  python3 scripts/check_style.py companies/<slug>                 deck.json·resume.json 중 있는 것 모두
  python3 scripts/check_style.py companies/<slug> --file resume.json
  python3 scripts/check_style.py companies/<slug> --strict        경고가 있으면 종료 코드 1
  python3 scripts/check_style.py companies/<slug> --file deck.json --only-from <파일>
                                                                  그 파일 글자가 들어간 필드만 (훅이 Edit 직후에 쓴다)

문장 필드(bullet·설명·노트 등)만 본다. 제목 라벨·기술 목록·수치·기간·표 칸은 보지 않는다.
- 끝맺음: 이력서는 "~했다"(…다), 덱은 "~했습니다"(…니다). 명사·수치로 끝나는 문장(개조식)과 다른 문체를 잡는다.
- 용어: 풀어 쓸 말이 있는 전문 용어·코드 식별자, 한 문장에 영문 용어가 너무 많은 경우.
- 나열·길이: 가운뎃점 나열, 화살표·괄호 과다, 너무 긴 문장.
기준과 고쳐 쓰는 법: .claude/skills/company-portfolio/reference/writing-style.md
"""
import json
import re
import sys
from pathlib import Path

# 풀어 쓸 말이 있는 용어 → 제안. 대소문자 무시, 단어 경계로 찾는다.
JARGON = {
    "groundedness": "원문 근거 검사",
    "fail-closed": "검사가 실패하면 막는",
    "fail-open": "검사가 실패해도 통과시키는",
    "freeze": "기존 위반을 기록해 두고",
    "smoke": "간이 테스트",
    "generic plan": "범용 실행 계획",
    "custom plan": "값별 실행 계획",
    "fan-in": "결과를 한데 모으는",
    "fan-out": "여러 곳으로 나눠 보내는",
    "dry-run": "실제로 쓰지 않고 미리 실행",
    "fallback": "대체 처리",
    "afterCommit": "커밋 뒤",
    "idempotent": "여러 번 실행해도 같은 결과",
    "halfvec": "절반 정밀도 벡터",
    "prepared statement": "미리 준비한 쿼리",
    "RTR": "리프레시 토큰 교체",
    "NER": "개체명 인식",
}
# 영문 개수에 넣지 않는 흔한 약어·단위
COMMON = {
    "PR", "API", "DB", "CI", "CD", "AI", "LLM", "SW", "IT", "UI", "UX", "OS", "ID", "URL", "JSON", "SQL",
    "TPS", "rps", "ms", "s", "p95", "p99", "CPU", "GPU", "GB", "MB", "KB", "E2E", "AWS", "FE", "BE", "PDF",
}

# 문장으로 끝맺어야 하는 필드 (덱). 부모 키별 예외는 PHRASE_PATH에서 뺀다.
DECK_SENTENCE = {"summary", "intro", "lead", "caption", "context", "problem", "action", "result", "evidence",
                 "desc", "contributions", "sub", "message", "notes", "body", "bullets", "text"}
DECK_PHRASE_PATH = {("fit", "items", "desc"), ("requirements", "rows", "evidence")}
# 제목은 라벨형(짧고 쉼표 없음)이면 넘어가고, 주장형이면 끝맺음을 본다
TITLE_KEYS = {"title"}
TITLE_EXEMPT_TYPES = {"cover", "section"}
TITLE_LABEL_MAX = 18

RESUME_SENTENCE = {"items", "body", "bullets"}

LIMITS = {
    "resume": {"default": 110},
    "deck": {"default": 90, "action": 70, "result": 80, "contributions": 70, "evidence": 90, "desc": 80, "caption": 100},
}


def plain(s: str) -> str:
    return s.replace("**", "").strip()


def sentences(s: str) -> list[str]:
    """문단을 문장으로 나눈다. 숫자 뒤 마침표(1.5)와 공백 없는 마침표(db.t4g)는 자르지 않는다."""
    text = re.sub(r"\s*\n\s*", " ", plain(s))  # \n은 화면 줄바꿈일 뿐 문장 경계가 아니다
    return [p.strip() for p in re.split(r"(?<=[^\d\s])\.\s+(?=\S)", text) if p.strip()]


URL_TAIL = re.compile(r"\s*[·—\-|]?\s*(https?://)?[\w.-]+\.(com|io|im|kr|net|org|dev|app)(/\S*)?$")


def core_end(s: str) -> str:
    """끝맺음 판단용 꼬리: 마침표·괄호 출처 표기·링크를 걷어낸다."""
    s = plain(s).rstrip(" .。!")
    while True:
        t = URL_TAIL.sub("", s).rstrip(" .")
        if t.endswith(")"):
            depth, i = 0, len(t) - 1
            while i >= 0:
                depth += {")": 1, "(": -1}.get(t[i], 0)
                if depth == 0:
                    break
                i -= 1
            head = t[:i].rstrip(" .")
            # 서술어 뒤에 붙은 "(약관 ETL)" 같은 출처 표기만 걷는다. "30.4분 (−42.2%)"처럼 앞이 명사면 그대로 둔다.
            if i > 0 and re.search(r"[다요]$", head):
                t = head
        if t == s:
            return s
        s = t


def ending_issue(s: str, kind: str) -> str | None:
    end = core_end(s)
    if not end:
        return None
    tail = end[-14:]
    if kind == "resume":
        if end.endswith("니다"):
            return f'"~니다"로 끝남 (…{tail}) — 이력서는 "~했다" 체'
        if end.endswith("다"):
            return None
    else:
        if end.endswith("니다") or end.endswith("니까"):
            return None
        if end.endswith("다"):
            return f'"~다"로 끝남 (…{tail}) — 덱은 "~했습니다" 체'
    what = "수치·기호" if re.search(r"[\d%)\]→]$", end) else "명사·단어"
    want = '"~했다"' if kind == "resume" else '"~했습니다"'
    return f"{what}로 끝남 (…{tail}) — {want}로 끝맺기"


GLOSS = re.compile(r"\([A-Za-z@][\w @/.,·+→\-]*\)")  # 풀이 뒤 괄호 속 원어 "(freeze)", "(tsvector, trigram)"


def latin_terms(s: str) -> list[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z0-9+#./_-]*", GLOSS.sub("", plain(s)))
    out = []
    for t in toks:
        t = t.rstrip("./-")
        if not t or t in COMMON or re.fullmatch(r"[a-z]{1,2}", t) or "." in t and re.search(r"\.(com|io|im|kr|md|json|py|js)\b", t):
            continue
        out.append(t)
    return out


def jargon_hits(s: str) -> list[str]:
    text = GLOSS.sub("", plain(s))  # 우리말 풀이 뒤 괄호에 붙인 원어는 풀어 쓴 것으로 본다
    hits = []
    for term, hint in JARGON.items():
        flags = 0 if term.isupper() else re.I
        if re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", text, flags):
            hits.append(f"{term}→{hint}")
    for ident in re.findall(r"(?<![A-Za-z])(?:[a-z]+[A-Z][a-z][A-Za-z0-9]*|[a-z]+_[a-z_]+)", text):
        if not any(ident.lower() == k.lower() for k in JARGON):
            hits.append(f"{ident}(코드 식별자)")
    return hits


def check_text(s: str, kind: str, key: str, endings: bool) -> list[str]:
    issues = []
    head = re.match(r"\*\*[^*]+\*\*\s*—\s*", s.strip())  # 앞의 "**소제목** —"은 영문 개수에서 뺀다
    label = plain(head.group(0)) if head else ""
    for idx, sent in enumerate(sentences(s)):
        if endings:
            e = ending_issue(sent, kind)
            if e:
                issues.append(e)
        lim = LIMITS[kind].get(key, LIMITS[kind]["default"])
        size = len(re.sub(r"(https?://)?[\w.-]+\.(com|io|im|kr|net|org|dev|app)(/\S*)?", "", sent))  # 링크는 길이에서 뺀다
        if key != "notes" and size > lim:
            issues.append(f"{size}자 — {lim}자 이내로 나누거나 줄이기")
        dots = max((len(m.split("·")) for m in re.findall(r"[^\s,—(]+(?:·[^\s,—)]+)+", sent)), default=0)
        if dots >= 4:
            issues.append(f"가운뎃점 나열 {dots}개 — 2~3개만 남기거나 문장으로 풀기")
        if sent.count("→") >= 3:
            issues.append(f"화살표 {sent.count('→')}개 — 전후 한 쌍만 남기기")
        if sent.count("(") >= 3:
            issues.append(f"괄호 {sent.count('(')}개 — 본문으로 풀거나 빼기")
        lat = latin_terms(sent[len(label):] if idx == 0 and label and sent.startswith(label) else sent)
        if len(lat) >= 5:
            issues.append(f"영문 용어 {len(lat)}개 ({', '.join(lat[:6])}) — 한 문장에 3개 이하")
    hits = jargon_hits(s)
    if hits:
        issues.append("풀어 쓸 용어: " + ", ".join(dict.fromkeys(hits)))
    return issues


def title_issue(s: str) -> list[str]:
    t = plain(s).replace("\n", " ")
    end = core_end(t)
    if end.endswith("니다"):
        return []
    if end.endswith("다"):
        return [f'제목이 "~다"로 끝남 (…{end[-14:]}) — 덱은 "~했습니다" 체']
    if len(t) <= TITLE_LABEL_MAX and "," not in t:
        return []  # "기술 스택" 같은 라벨형 제목
    return [f'제목이 명사·수치로 끝남 (…{end[-14:]}) — 주장형 제목은 "~했습니다"로']


def visit_deck(v, path: list[str], key: str, stype: str):
    """슬라이드 안의 글자 필드를 돌며 (경로, 경고 목록)을 낸다."""
    if isinstance(v, str):
        if key in TITLE_KEYS and len(path) == 1:
            if stype not in TITLE_EXEMPT_TYPES:
                yield path, title_issue(v)
            return
        if key in DECK_SENTENCE:
            parent = next((p for p in reversed(path[:-1]) if not p.isdigit()), "")
            phrase = (stype, parent, key) in DECK_PHRASE_PATH
            yield path, check_text(v, "deck", key, endings=not phrase)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from visit_deck(x, path + [f"{i + 1}"], key, stype)
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from visit_deck(x, path + [k], k, stype)


def walk_deck(deck: dict):
    for no, slide in enumerate(deck.get("slides", []), 1):
        stype = slide.get("type", "")
        for k, v in slide.items():
            for path, issues in visit_deck(v, [k], k, stype):
                if issues:
                    yield f"슬라이드 {no} ({stype}) {'.'.join(path)}", path_text(slide, path), issues


def path_text(obj, path):
    for p in path:
        obj = obj[int(p) - 1] if isinstance(obj, list) else obj[p]
    return obj


def walk_resume(resume: dict):
    for sec in resume.get("sections", []):
        title = sec.get("title", sec.get("type"))
        if sec.get("type") == "text":
            for i, item in enumerate(sec.get("items") or [], 1):
                yield f"{title} {i}", item, check_text(item, "resume", "items", True)
            body = sec.get("body")
            for i, para in enumerate([body] if isinstance(body, str) else body or [], 1):
                yield f"{title} 문단 {i}", para, check_text(para, "resume", "body", True)
        elif sec.get("type") == "projects":
            for p in sec.get("items", []):
                for i, b in enumerate(p.get("bullets") or [], 1):
                    yield f"{title} › {p.get('name')} {i}", b, check_text(b, "resume", "bullets", True)


def touched(text: str, only: str) -> bool:
    """Edit의 new_string(JSON 원문 조각)이 이 필드를 건드렸는지."""
    enc = json.dumps(text, ensure_ascii=False)[1:-1]
    frag = only.strip().strip('",')
    return enc in only or (len(frag) >= 8 and frag in enc)


def check_file(path: Path, only: str | None = None) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = walk_deck(data) if "slides" in data else walk_resume(data)
    n = 0
    for where, text, issues in rows:
        if not issues or (only is not None and not touched(text, only)):
            continue
        n += len(issues)
        snippet = plain(text).replace("\n", " ")
        print(f"⚠️  {path.name} {where}: {snippet[:60]}{'…' if len(snippet) > 60 else ''}")
        for msg in issues:
            print(f"     - {msg}")
    return n


def usage() -> int:
    print(__doc__.strip())
    return 2


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--strict"]
    strict = len(args) != len(argv)
    files, only = None, None
    if "--only-from" in args:
        i = args.index("--only-from")
        if i + 1 >= len(args):
            return usage()
        only = Path(args[i + 1]).read_text(encoding="utf-8")
        del args[i:i + 2]
    if "--file" in args:
        i = args.index("--file")
        if i + 1 >= len(args):
            return usage()
        files = [args[i + 1]]
        del args[i:i + 2]
    if len(args) != 1:
        return usage()
    base = Path(args[0])
    paths = [base / f for f in (files or ["deck.json", "resume.json"]) if (base / f).is_file()]
    if not paths:
        print(f"검사할 파일이 없다: {base}/{files[0] if files else 'deck.json·resume.json'}")
        return 2
    total = sum(check_file(p, only) for p in paths)
    if total:
        print(f"\n문장 스타일 경고 {total}건 — 기준: .claude/skills/company-portfolio/reference/writing-style.md")
        print("사실·수치는 그대로 두고 문장만 고친다. 고친 뒤 check_facts.py를 다시 돌린다.")
    else:
        print("문장 스타일 경고 없음: " + ", ".join(p.name for p in paths))
    return 1 if strict and total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
