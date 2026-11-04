#!/usr/bin/env python3
"""GitHub 저장소·위키를 내려받고, 지원자 기여와 문서·이미지 목록을 정리한다.

사용법: python3 scripts/github_export.py [설정파일]      (기본: profile/sources.json)

설정 (profile/sources.json의 "github"):
  "github": {
    "orgs":    ["SM17-YoonDongJu"],              조직의 저장소 전부 (gh 필요)
    "repos":   ["owner/name"],                    개별 저장소 (선택)
    "authors": ["slimgreg5208@gmail.com"]         지원자 커밋 판별 (git --author 패턴, 이메일 권장)
  }

출력:
  profile/github/<repo>/, <repo>.wiki/   클론 (이미 있으면 pull)
  profile/github/index.md                저장소별 내 커밋 수·기간, 많이 바꾼 경로, 커밋 제목,
                                         문서 목록(첫 제목), 이미지 목록(로컬 경로 | 쓰인 문서 | 대체 텍스트)
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path("profile/github")
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
IMG_REF = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)|<img[^>]*src=[\"']([^\"']+)[\"'][^>]*?(?:alt=[\"']([^\"']*)[\"'])?")


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def sync(url, dest):
    if (dest / ".git").is_dir():
        run(["git", "fetch", "-q", "--all", "--prune"], cwd=dest, check=False)
    elif run(["git", "clone", "-q", "--filter=blob:none", url, str(dest)], check=False).returncode:
        return False
    # 기본 브랜치가 오래된 경우가 많아 개발 브랜치를 우선 체크아웃한다
    for br in ("develop", "dev"):
        if run(["git", "rev-parse", "-q", "--verify", f"origin/{br}"], cwd=dest, check=False).returncode == 0:
            run(["git", "checkout", "-q", "-B", br, f"origin/{br}"], cwd=dest, check=False)
            break
    else:
        run(["git", "pull", "-q", "--ff-only"], cwd=dest, check=False)
    return True


def org_repos(org):
    out = run(["gh", "repo", "list", org, "--limit", "100", "--json", "nameWithOwner,isArchived"]).stdout
    return [r["nameWithOwner"] for r in json.loads(out) if not r["isArchived"]]


def first_heading(p: Path):
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def docs_and_images(repo_dir: Path):
    files = [p for p in repo_dir.rglob("*") if ".git" not in p.parts and p.is_file()]
    docs = sorted(p for p in files if p.suffix.lower() == ".md")
    imgs = sorted(p for p in files if p.suffix.lower() in IMG_EXT)
    used = {}  # 이미지 파일 이름 → (문서, 대체 텍스트)
    for d in docs:
        for m in IMG_REF.finditer(d.read_text(encoding="utf-8", errors="ignore")):
            alt, src = (m.group(1), m.group(2)) if m.group(2) else (m.group(4) or "", m.group(3))
            used.setdefault(src.split("?")[0].rstrip("/").split("/")[-1], (d.relative_to(repo_dir), alt))
    return docs, imgs, used


def my_activity(repo_dir: Path, authors):
    who = [f"--author={a}" for a in authors]
    revs = ["HEAD", "--remotes"]  # 모든 원격 브랜치의 커밋 (중복 없이)
    total = len(run(["git", "rev-list", "--no-merges", *revs], cwd=repo_dir).stdout.split())
    mine = run(["git", "log", "--no-merges", "--format=%ad\t%s", "--date=short", *who, *revs], cwd=repo_dir).stdout.splitlines()
    paths = Counter()
    names = run(["git", "log", "--no-merges", "--name-only", "--format=", *who, *revs], cwd=repo_dir).stdout.split()
    for n in names:  # 파일이 속한 폴더 단위로 센다 (Java 패키지처럼 깊은 구조도 도메인이 보이게)
        paths[n.rsplit("/", 1)[0] + "/" if "/" in n else n] += 1
    return total, mine, paths


def main(argv):
    cfg_path = Path(argv[0] if argv else "profile/sources.json")
    if not cfg_path.is_file():
        print(__doc__.strip())
        return 2
    gh = json.loads(cfg_path.read_text(encoding="utf-8")).get("github", {})
    authors = gh.get("authors") or []
    repos = list(gh.get("repos", []))
    for org in gh.get("orgs", []):
        repos += [r for r in org_repos(org) if r not in repos]
    ROOT.mkdir(parents=True, exist_ok=True)

    out = ["# GitHub 자료", "", f"지원자 커밋 판별: {', '.join(authors) or '(authors 미설정)'}", ""]
    for full in repos:
        owner, name = full.split("/")
        repo_dir, wiki_dir = ROOT / name, ROOT / f"{name}.wiki"
        if not sync(f"https://github.com/{full}.git", repo_dir):
            print(f"실패: {full} (접근 불가)")
            out += [f"## {full}", "- 클론 실패 (비공개이거나 접근 권한 없음)", ""]
            continue
        if run(["git", "rev-parse", "-q", "--verify", "HEAD"], cwd=repo_dir, check=False).returncode:
            out += [f"## {full}", "- 빈 저장소", ""]
            print(f"건너뜀: {full} (빈 저장소)")
            continue
        has_wiki = sync(f"https://github.com/{full}.wiki.git", wiki_dir)
        total, mine, paths = my_activity(repo_dir, authors) if authors else (0, [], Counter())
        branch = run(["git", "branch", "--show-current"], cwd=repo_dir).stdout.strip()
        out += [f"## {full}", f"- 로컬: `{repo_dir}` ({branch})" + (f" · 위키 `{wiki_dir}`" if has_wiki else "")]
        if total <= 3:
            out.append(f"- ⚠️ 커밋 이력이 {total}개뿐(가져오기·스쿼시로 보임) — git으로 기여를 판별할 수 없다. 기여는 프로필 기준으로만 쓴다")
        if mine:
            out.append(f"- 내 커밋(merge 제외, 전 브랜치): {len(mine)} / 전체 {total} ({mine[-1].split(chr(9))[0]} ~ {mine[0].split(chr(9))[0]})")
            out += ["", "### 내가 많이 바꾼 경로", *[f"- `{p}` ({n})" for p, n in paths.most_common(15)]]
            out += ["", "### 내 커밋 (최근 40)", *[f"- {m.replace(chr(9), ' ')}" for m in mine[:40]]]
        else:
            out.append(f"- 내 커밋(merge 제외, 전 브랜치): 0 / 전체 {total}")
        for label, d, _raw in (("저장소", repo_dir, f"https://raw.githubusercontent.com/{full}/HEAD"),
                               ("위키", wiki_dir, f"https://raw.githubusercontent.com/wiki/{full}")):
            if not d.is_dir():
                continue
            docs, imgs, used = docs_and_images(d)
            if docs:
                out += ["", f"### {label} 문서 ({len(docs)})",
                        *[f"- `{p.relative_to(d)}` — {first_heading(p)}" for p in docs]]
            if imgs:
                out += ["", f"### {label} 이미지 ({len(imgs)})", "| 로컬 경로 | 쓰인 문서 | 대체 텍스트 |", "|---|---|---|"]
                for p in imgs:
                    doc, alt = used.get(p.name, ("", ""))
                    out.append(f"| `{p}` | {doc or '-'} | {alt.replace('|', '/') or '-'} |")
        out.append("")
        print(f"완료: {full} — 내 커밋 {len(mine)}" + (", 위키 있음" if has_wiki else ""))
    (ROOT / "index.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"저장: {ROOT / 'index.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
