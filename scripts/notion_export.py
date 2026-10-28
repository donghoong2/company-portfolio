#!/usr/bin/env python3
"""공개 Notion 페이지(하위 페이지 포함)를 Markdown으로 내보낸다.

사용법: python3 scripts/notion_export.py <notion_url_or_page_id> [출력파일]
기본 출력: profile/notion_profile.md
"""
import json
import re
import sys
import urllib.request

API = "https://www.notion.so/api/v3"
MAX_DEPTH = 4


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
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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
        data = post("syncRecordValues", {"requests": [{"pointer": {"table": "block", "id": i}, "version": -1} for i in missing]})
        for bid, rec in data.get("recordMap", {}).get("block", {}).items():
            blocks[bid] = unwrap(rec)
        new_missing = {c for b in blocks.values() for c in b.get("content", []) if c not in blocks} - missing
        missing = new_missing
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
    if t == "page" and indent == 0 and depth == 0 and not out:
        out.append(f"# {title}\n")
    elif t == "page":
        if depth + 1 > MAX_DEPTH or bid in visited:
            out.append(f"{pad}- (하위 페이지) {title}")
            return
        visited.add(bid)
        out.append(f"\n{'#' * min(depth + 2, 6)} 📄 {title}\n")
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
        out.append(f"{pad}[{t}] {title or ''} {src or ''}".rstrip())
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


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = norm_id(sys.argv[1])
    dest = sys.argv[2] if len(sys.argv) > 2 else "profile/notion_profile.md"
    blocks = load_page(root)
    out = []
    render(root, blocks, 0, 0, out, {root})
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"저장 완료: {dest} ({len(out)} lines)")


if __name__ == "__main__":
    main()
