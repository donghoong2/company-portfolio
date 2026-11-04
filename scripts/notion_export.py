#!/usr/bin/env python3
"""공개 Notion 페이지(하위 페이지 포함)를 Markdown으로 내보낸다.

사용법: python3 scripts/notion_export.py <notion_url_or_page_id> [출력파일] [--assets <이미지 폴더>] [--delay <초>]
기본 출력: profile/notion_profile.md

--assets: 페이지 속 이미지(Notion 첨부·외부 URL)를 내려받고 <이미지 폴더>/index.md에
          파일 | 위치(페이지 › 제목) | 캡션 | 원본 목록을 남긴다. Markdown의 [image] 줄에도 로컬 경로를 붙인다.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.notion.so/api/v3"
MAX_DEPTH = 4
IMAGES = []          # (block_id, src, caption, context, filename)
CTX = {"page": "", "heading": ""}
BATCH = 100
DELAY = 0.0          # 요청 사이 대기(초). 큰 워크스페이스는 --delay 3 정도로 429를 줄인다


def norm_id(s):
    m = re.findall(r"[0-9a-f]{32}", s.replace("-", ""))
    if not m:
        raise SystemExit(f"페이지 ID를 찾을 수 없음: {s}")
    h = m[0]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def post(endpoint, body):
    req = urllib.request.Request(
        f"{API}/{endpoint}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    time.sleep(DELAY)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or 2 ** attempt * 3
            print(f"  {e.code} — {wait}s 후 재시도", file=sys.stderr)
            time.sleep(wait)
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:  # SSL EOF 등 일시적 네트워크 오류
            if attempt == 5:
                raise
            wait = 2 ** attempt * 3
            print(f"  네트워크 오류({e}) — {wait}s 후 재시도", file=sys.stderr)
            time.sleep(wait)


def unwrap(rec):
    v = rec.get("value", {})
    return v.get("value", v) if isinstance(v, dict) else {}


def load_page(page_id):
    blocks, cursor, chunk = {}, {"stack": []}, 0
    while True:
        data = post("loadPageChunk", {"pageId": page_id, "limit": 100, "cursor": cursor,
                                      "chunkNumber": chunk, "verticalColumns": False})
        for bid, rec in data.get("recordMap", {}).get("block", {}).items():
            blocks[bid] = unwrap(rec)
        cursor = data.get("cursor", {"stack": []})
        chunk += 1
        if not cursor.get("stack"):
            break
    missing = {c for b in blocks.values() for c in b.get("content", []) if c not in blocks}
    while missing:
        ids = sorted(missing)
        for i in range(0, len(ids), BATCH):  # 한 번에 많이 요청하면 413
            data = post("syncRecordValues", {"requests": [{"pointer": {"table": "block", "id": x}, "version": -1}
                                                          for x in ids[i:i + BATCH]]})
            for bid, rec in data.get("recordMap", {}).get("block", {}).items():
                blocks[bid] = unwrap(rec)
        missing = {c for b in blocks.values() for c in b.get("content", []) if c not in blocks} - missing
    return blocks


def text(prop):
    out = []
    for seg in prop or []:
        t = seg[0]
        for fmt in (seg[1] if len(seg) > 1 else []):
            if fmt[0] == "a":
                t = f"[{t}]({fmt[1]})"
            elif fmt[0] == "b":
                t = f"**{t}**"
        out.append(t)
    return "".join(out)


def render(bid, blocks, depth, indent, out, visited):
    b = blocks.get(bid)
    if not b or not b.get("alive", True):
        return
    t = b.get("type")
    p = b.get("properties", {})
    title = text(p.get("title"))
    pad = "  " * indent
    child_indent = indent
    if t in ("page", "header", "sub_header", "sub_sub_header"):
        CTX["page" if t == "page" else "heading"] = title
        if t == "page":
            CTX["heading"] = ""
    if t == "page" and indent == 0 and depth == 0 and not out:
        out.append(f"# {title}\n")
    elif t == "page":
        if depth + 1 > MAX_DEPTH or bid in visited:
            out.append(f"{pad}- (하위 페이지) {title}")
            return
        visited.add(bid)
        out.append(f"\n{'#' * min(depth + 2, 6)} 📄 {title}\n")
        print(f"  {'  ' * depth}📄 {title}", file=sys.stderr)
        sub = load_page(bid)
        blocks.update(sub)
        for c in blocks[bid].get("content", []):
            render(c, blocks, depth + 1, 0, out, visited)
        return
    elif t == "header":
        out.append(f"\n## {title}")
    elif t == "sub_header":
        out.append(f"\n### {title}")
    elif t == "sub_sub_header":
        out.append(f"\n#### {title}")
    elif t in ("bulleted_list", "toggle"):
        out.append(f"{pad}- {title}")
        child_indent = indent + 1
    elif t == "numbered_list":
        out.append(f"{pad}1. {title}")
        child_indent = indent + 1
    elif t == "to_do":
        out.append(f"{pad}- [ ] {title}")
        child_indent = indent + 1
    elif t == "quote":
        out.append(f"> {title}")
    elif t == "callout":
        out.append(f"> 💡 {title}")
    elif t == "code":
        out.append(f"```\n{title}\n```")
    elif t == "divider":
        out.append("---")
    elif t in ("image", "file", "pdf", "video", "bookmark", "embed"):
        src = (b.get("format") or {}).get("display_source") or text(p.get("source"))
        line = f"{pad}[{t}] {title or ''} {src or ''}".rstrip()
        if t == "image" and src:
            cap = text(p.get("caption")) or title or ""
            fname = image_name(len(IMAGES) + 1, src)
            IMAGES.append((bid, src, cap, " › ".join(x for x in (CTX["page"], CTX["heading"]) if x), fname))
            line += f" → {fname}"
        out.append(line)
    elif t == "table_row":
        cells = [text(v) for v in p.values()]
        out.append("| " + " | ".join(cells) + " |")
    elif t in ("collection_view", "collection_view_page"):
        render_collection(b, blocks, depth, out, visited)
        return
    elif title:
        out.append(f"{pad}{title}")
    for c in b.get("content", []) or []:
        render(c, blocks, depth, child_indent, out, visited)


def prop_value(val, ptype):
    if not val:
        return ""
    if ptype == "date":
        for seg in val:
            for fmt in (seg[1] if len(seg) > 1 else []):
                if fmt[0] == "d":
                    d = fmt[1]
                    return d.get("start_date", "") + (f" ~ {d['end_date']}" if d.get("end_date") else "")
    return text(val)


def render_collection(b, blocks, depth, out, visited):
    cid = b.get("collection_id") or (b.get("format") or {}).get("collection_pointer", {}).get("id")
    view_ids = b.get("view_ids") or []
    if not cid or not view_ids:
        return
    coll = unwrap(post("syncRecordValues", {"requests": [{"pointer": {"table": "collection", "id": cid}, "version": -1}]})
                  ["recordMap"]["collection"][cid])
    name = text(coll.get("name")).strip()
    schema = coll.get("schema", {})
    data = post("queryCollection", {
        "collection": {"id": cid}, "collectionView": {"id": view_ids[0]},
        "loader": {"type": "reducer", "reducers": {"collection_group_results": {"type": "results", "limit": 200}},
                   "searchQuery": "", "userTimeZone": "Asia/Seoul"},
    })
    ids = data.get("result", {}).get("reducerResults", {}).get("collection_group_results", {}).get("blockIds", [])
    for bid, rec in data.get("recordMap", {}).get("block", {}).items():
        blocks[bid] = unwrap(rec)
    out.append(f"\n{'#' * min(depth + 2, 6)} 🗂 {name}\n")
    for rid in ids:
        row = blocks.get(rid, {})
        props = row.get("properties", {})
        out.append(f"\n{'#' * min(depth + 3, 6)} {text(props.get('title'))}")
        for key, meta in schema.items():
            if key == "title" or meta.get("type") in ("created_time", "last_edited_time"):
                continue
            v = prop_value(props.get(key), meta.get("type"))
            if v:
                out.append(f"- **{meta.get('name')}**: {v}")
        if row.get("content") and depth + 1 <= MAX_DEPTH and rid not in visited:
            visited.add(rid)
            blocks.update(load_page(rid))
            for c in blocks[rid].get("content", []):
                render(c, blocks, depth + 1, 0, out, visited)


def image_name(n, src):
    base = src.split("?")[0].rstrip("/").split("/")[-1].split(":")[-1]
    stem, _, ext = base.rpartition(".")
    if not stem or ext.lower() not in ("png", "jpg", "jpeg", "gif", "webp", "svg"):
        stem, ext = base or "image", "png"
    stem = re.sub(r"[^0-9A-Za-z가-힣_-]+", "-", stem).strip("-")[:60] or "image"
    return f"{n:03d}-{stem}.{ext.lower()}"


def download_images(folder):
    os.makedirs(folder, exist_ok=True)
    signed = {}
    att = [(bid, src) for bid, src, *_ in IMAGES if src.startswith("attachment:") or "secure.notion-static.com" in src]
    for i in range(0, len(att), 20):
        part = att[i:i + 20]
        res = post("getSignedFileUrls", {"urls": [{"url": s, "permissionRecord": {"table": "block", "id": b}} for b, s in part]})
        for (b, _), u in zip(part, res.get("signedUrls", []), strict=False):
            signed[b] = u
    rows = ["| 파일 | 위치 | 캡션 | 원본 |", "|---|---|---|---|"]
    ok = 0
    for bid, src, cap, ctx, fname in IMAGES:
        url = urllib.parse.quote(signed.get(bid) or src, safe=":/?&=%#+,;@!$'()*~")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(os.path.join(folder, fname), "wb") as f:
                f.write(r.read())
            ok += 1
            status = fname
        except Exception as e:  # noqa: BLE001 — 실패해도 목록에 남기고 계속
            status = f"~~{fname}~~ (실패: {e})"
        rows.append(f"| {status} | {ctx} | {cap.replace('|', '/')} | {src.split('?')[0][:120]} |")
    with open(os.path.join(folder, "index.md"), "w", encoding="utf-8") as f:
        f.write("# 이미지 목록\n\n" + "\n".join(rows) + "\n")
    print(f"이미지: {ok}/{len(IMAGES)} 저장 → {folder}/")


def main():
    args = sys.argv[1:]
    assets = None
    global DELAY
    if "--delay" in args:
        i = args.index("--delay")
        DELAY = float(args[i + 1])
        del args[i:i + 2]
    if "--assets" in args:
        i = args.index("--assets")
        assets = args[i + 1]
        del args[i:i + 2]
    if not args:
        raise SystemExit(__doc__)
    root = norm_id(args[0])
    dest = args[1] if len(args) > 1 else "profile/notion_profile.md"
    blocks = load_page(root)
    out = []
    render(root, blocks, 0, 0, out, {root})
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"저장 완료: {dest} ({len(out)} lines)")
    if assets:
        download_images(assets)


if __name__ == "__main__":
    main()
