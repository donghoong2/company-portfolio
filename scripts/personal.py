#!/usr/bin/env python3
"""이력서 인적사항(이름·생년월일·연락처·주소·사진)을 입력받아 profile/personal.json에 저장한다.

사용법:
  python3 scripts/personal.py                      터미널에서 빈 항목을 하나씩 입력 (기존 값은 Enter로 유지)
  python3 scripts/personal.py set --birth 2000-01-01 --address "..." --photo ~/photo.jpg [--phone --email --name --name-en --link GitHub=https://...]
  python3 scripts/personal.py check                이력서에 필요한 항목이 다 있는지 (없으면 종료 코드 1)
  python3 scripts/personal.py show                 저장된 값 보기

- profile/ 은 .gitignore 대상이다. 인적사항과 사진은 저장소에 올라가지 않는다.
- 사진은 profile/photo.<확장자>로 복사한다 (증명사진 3:4 비율 권장).
- 이름·영문 이름·GitHub가 비어 있으면 profile/notion_profile.md 첫 제목과 링크에서 미리 채운다.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PATH = Path("profile/personal.json")
REQUIRED = ["name", "birth", "phone", "email", "address", "photo"]
LABELS = {
    "name": "성명", "nameEn": "영문 성명", "birth": "생년월일", "phone": "휴대폰",
    "email": "이메일", "address": "주소", "photo": "사진 경로",
}


def load() -> dict:
    data = json.loads(PATH.read_text(encoding="utf-8")) if PATH.is_file() else {}
    data.setdefault("links", [])
    return data


def save(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"저장: {PATH}")


def prefill(data: dict) -> None:
    src = Path("profile/notion_profile.md")
    if not src.is_file():
        return
    text = src.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(\S+)\s*\(([^)]+)\)", text, re.M)
    if m:
        data.setdefault("name", m.group(1))
        data.setdefault("nameEn", m.group(2).strip())
    gh = re.search(r"https://github\.com/[\w-]+(?=[)\s])", text)
    if gh and not any(link.get("label") == "GitHub" for link in data["links"]):
        data["links"].append({"label": "GitHub", "url": gh.group(0)})


def norm_birth(v: str) -> str:
    d = re.findall(r"\d+", v)
    if len(d) == 1 and len(d[0]) == 8:
        d = [d[0][:4], d[0][4:6], d[0][6:]]
    if len(d) != 3 or len(d[0]) != 4:
        raise ValueError(f"생년월일 형식을 알 수 없다: {v} (예: 2000-01-01)")
    y, m, day = int(d[0]), int(d[1]), int(d[2])
    if not (1 <= m <= 12 and 1 <= day <= 31):
        raise ValueError(f"생년월일 범위 오류: {v}")
    return f"{y:04d}-{m:02d}-{day:02d}"


def norm_phone(v: str) -> str:
    d = re.sub(r"\D", "", v)
    if not re.fullmatch(r"01\d{8,9}", d):
        raise ValueError(f"휴대폰 번호 형식 오류: {v} (예: 010-1234-5678)")
    return f"{d[:3]}-{d[3:-4]}-{d[-4:]}"


def norm_email(v: str) -> str:
    v = v.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
        raise ValueError(f"이메일 형식 오류: {v}")
    return v


def copy_photo(v: str) -> str:
    src = Path(v).expanduser()
    if not src.is_file():
        raise ValueError(f"사진 파일이 없다: {src}")
    ext = src.suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        raise ValueError(f"사진은 jpg/png만: {src.name}")
    dest = Path("profile") / f"photo{'.jpg' if ext == '.jpeg' else ext}"
    for old in Path("profile").glob("photo.*"):
        if old.resolve() != src.resolve():
            old.unlink()
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(dest)],
                             capture_output=True, text=True, check=True).stdout
        w, h = (int(x) for x in re.findall(r"pixel\w+: (\d+)", out))
        if abs(w / h - 0.75) > 0.05:
            print(f"⚠️  사진 비율 {w}x{h} — 증명사진 3:4가 아니면 이력서에서 잘려 보인다")
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    return str(dest)


NORMALIZE = {"birth": norm_birth, "phone": norm_phone, "email": norm_email, "photo": copy_photo}


def put(data: dict, key: str, value: str) -> None:
    value = value.strip()
    data[key] = NORMALIZE.get(key, lambda x: x)(value) if value else value


def put_link(data: dict, spec: str) -> None:
    label, _, url = spec.partition("=")
    if not url:
        raise ValueError(f"--link 형식: 라벨=URL ({spec})")
    data["links"] = [link for link in data["links"] if link.get("label") != label.strip()]
    data["links"].append({"label": label.strip(), "url": url.strip()})


def missing(data: dict) -> list[str]:
    out = [k for k in REQUIRED if not data.get(k)]
    if data.get("photo") and not Path(data["photo"]).is_file():
        out.append("photo")
    return sorted(set(out), key=REQUIRED.index)


def cmd_set(args: list[str]) -> int:
    flags = {"--name": "name", "--name-en": "nameEn", "--birth": "birth", "--phone": "phone",
             "--email": "email", "--address": "address", "--photo": "photo"}
    data = load()
    prefill(data)
    i = 0
    while i < len(args):
        if i + 1 >= len(args):
            print(f"값이 없다: {args[i]}")
            return 2
        flag, value = args[i], args[i + 1]
        if flag == "--link":
            put_link(data, value)
        elif flag in flags:
            put(data, flags[flag], value)
        else:
            print(f"알 수 없는 옵션: {flag}")
            return 2
        i += 2
    save(data)
    return report(data)


def cmd_interactive() -> int:
    data = load()
    prefill(data)
    print("빈칸으로 Enter를 누르면 기존 값을 유지한다.")
    for key, label in LABELS.items():
        while True:
            cur = data.get(key, "")
            raw = input(f"{label}{f' [{cur}]' if cur else ''}: ").strip()
            if not raw:
                break
            try:
                put(data, key, raw)
                break
            except ValueError as e:
                print(f"  {e}")
    raw = input("링크 (라벨=URL, 쉼표로 여러 개, 예: GitHub=https://github.com/me): ").strip()
    for spec in filter(None, (s.strip() for s in raw.split(","))):
        put_link(data, spec)
    save(data)
    return report(data)


def report(data: dict) -> int:
    miss = missing(data)
    if miss:
        print("미입력: " + ", ".join(LABELS[k] for k in miss))
        return 1
    print("이력서 인적사항 완료")
    return 0


def main(argv: list[str]) -> int:
    try:
        if not argv:
            if not sys.stdin.isatty():
                print(__doc__.strip())
                return 2
            return cmd_interactive()
        if argv[0] == "set":
            return cmd_set(argv[1:])
        if argv[0] == "check":
            return report(load())
        if argv[0] == "show":
            print(json.dumps(load(), ensure_ascii=False, indent=2))
            return report(load())
    except ValueError as e:
        print(e)
        return 2
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
