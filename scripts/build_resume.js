#!/usr/bin/env node
/**
 * resume.json + profile/personal.json → 표준 양식 이력서 PDF (HTML을 Chrome 헤드리스로 인쇄)
 *
 * 사용법: node scripts/build_resume.js companies/<slug> [--allow-missing] [--html]
 *   입력: companies/<slug>/resume.json, profile/personal.json (+ 사진)
 *   출력: output/<slug>_resume.pdf   (--html이면 같은 이름의 .html도 남긴다 — 개인정보 포함)
 *   --allow-missing: 인적사항 미입력 항목을 빈칸으로 두고 만든다 (초안 확인용)
 *
 * 스키마는 .claude/skills/company-resume/reference/resume-schema.md 참고.
 * 인적사항은 resume.json에 넣지 않는다 — profile/personal.json(.gitignore)에서만 읽는다.
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { pathToFileURL } = require("url");

const args = process.argv.slice(2);
const dir = args.find((a) => !a.startsWith("--"));
if (!dir || !fs.existsSync(path.join(dir, "resume.json"))) {
  console.error("사용법: node scripts/build_resume.js companies/<slug> [--allow-missing] [--html]");
  process.exit(2);
}
const allowMissing = args.includes("--allow-missing");
const keepHtml = args.includes("--html");
const slug = path.basename(path.resolve(dir));
const resume = JSON.parse(fs.readFileSync(path.join(dir, "resume.json"), "utf8"));
const meta = resume.meta || {};
const style = resume.style || {};

// ---------- 인적사항 ----------
const PERSONAL = "profile/personal.json";
const personal = fs.existsSync(PERSONAL) ? JSON.parse(fs.readFileSync(PERSONAL, "utf8")) : {};
const REQUIRED = { name: "성명", birth: "생년월일", phone: "휴대폰", email: "이메일", address: "주소", photo: "사진" };
const missing = Object.entries(REQUIRED)
  .filter(([k]) => !personal[k] || (k === "photo" && !fs.existsSync(personal.photo)))
  .map(([, label]) => label);
if (missing.length) {
  const msg = `인적사항 미입력: ${missing.join(", ")} → python3 scripts/personal.py 로 입력`;
  if (!allowMissing) {
    console.error(`${msg} (빈칸으로 만들려면 --allow-missing)`);
    process.exit(1);
  }
  console.warn(`⚠️  ${msg} — 빈칸으로 만든다`);
}

// ---------- 유틸 ----------
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const fmt = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
const dot = (d) => String(d || "").replace(/-/g, ".");
function dataUri(p) {
  const mime = path.extname(p).toLowerCase() === ".png" ? "image/png" : "image/jpeg";
  return `data:${mime};base64,${fs.readFileSync(p).toString("base64")}`;
}
function today() {
  const d = new Date();
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}
function link(url) {
  const shown = String(url).replace(/^https?:\/\//, "").replace(/\/$/, "");
  return `<a href="${esc(url)}">${esc(shown)}</a>`;
}

// ---------- 폰트 ----------
const FONT_STACK = [style.font, "Pretendard", "Nanum Gothic", "Apple SD Gothic Neo"].filter(Boolean);
function usedFont() {
  try {
    const fams = execFileSync("fc-list", [":", "family"], { encoding: "utf8" }).toLowerCase();
    return FONT_STACK.find((f) => fams.includes(f.toLowerCase())) || "sans-serif";
  } catch {
    return null;
  }
}

// ---------- 섹션 ----------
function personalTable() {
  const p = personal;
  const links = p.links || [];
  const info = meta.info || []; // 공고별 추가 행 (예: 근무 가능 기간) — resume.json meta.info
  const rows = 4 + info.length + links.length;
  const photo = p.photo && fs.existsSync(p.photo) ? `<img src="${dataUri(p.photo)}" alt="">` : "";
  const nameRow = p.nameEn
    ? `<th>성 명</th><td>${esc(p.name)}</td><th>영 문</th><td>${esc(p.nameEn)}</td>`
    : `<th>성 명</th><td colspan="3">${esc(p.name)}</td>`;
  return `<table class="personal">
<colgroup><col class="photo-col"><col class="k"><col><col class="k"><col></colgroup>
<tr><td class="photo" rowspan="${rows}">${photo}</td>${nameRow}</tr>
<tr><th>생년월일</th><td>${esc(dot(p.birth))}</td><th>지원분야</th><td>${esc(meta.role || "")}</td></tr>
<tr><th>휴 대 폰</th><td>${esc(p.phone)}</td><th>이 메 일</th><td>${esc(p.email)}</td></tr>
<tr><th>주 소</th><td colspan="3">${esc(p.address)}</td></tr>
${info.map((r) => `<tr><th>${esc(r.label)}</th><td colspan="3">${fmt(r.value)}</td></tr>`).join("\n")}
${links.map((l) => `<tr><th>${esc(l.label)}</th><td colspan="3">${link(l.url)}</td></tr>`).join("\n")}
</table>`;
}

function gridTable(s) {
  const cols = s.columns || [];
  const rows = s.rows || [];
  // 열 정렬: 지정값(c|l) 우선, 없으면 긴 글이 있는 열만 왼쪽 정렬
  const align = cols.map((_, i) => s.align?.[i] || (rows.some((r) => String(r[i] ?? "").length > 24) ? "l" : "c"));
  return `<table class="grid">
<colgroup>${cols.map((_, i) => `<col${s.widths?.[i] ? ` style="width:${s.widths[i]}%"` : ""}>`).join("")}</colgroup>
<thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
<tbody>${rows.map((r) => `<tr>${cols.map((_, i) => `<td class="${align[i]}">${fmt(r[i])}</td>`).join("")}</tr>`).join("\n")}</tbody>
</table>`;
}

function skillsTable(s) {
  return `<table class="grid kv"><colgroup><col class="k"><col></colgroup>
${(s.groups || []).map((g) => `<tr><th>${esc(g.name)}</th><td>${(g.items || []).map(esc).join(" · ")}</td></tr>`).join("\n")}
</table>`;
}

function projectTable(p) {
  const title = `<b>${esc(p.name)}</b>${p.summary ? ` <span class="muted">— ${fmt(p.summary)}</span>` : ""}${
    p.org ? `<span class="org">${esc(p.org)}</span>` : ""
  }`;
  const rows = [
    `<tr class="ptitle"><th>프로젝트</th><td colspan="3">${title}</td></tr>`,
    `<tr><th>기 간</th><td>${esc(p.period)}</td><th>팀 구성</th><td>${esc(p.team)}</td></tr>`,
  ];
  if (p.role) rows.push(`<tr><th>역 할</th><td colspan="3">${fmt(p.role)}</td></tr>`);
  if (p.stack?.length) rows.push(`<tr><th>기 술</th><td colspan="3">${p.stack.map(esc).join(" · ")}</td></tr>`);
  if (p.bullets?.length)
    rows.push(`<tr><th>주요 내용</th><td colspan="3"><ul>${p.bullets.map((b) => `<li>${fmt(b)}</li>`).join("")}</ul></td></tr>`);
  if (p.link) rows.push(`<tr><th>링 크</th><td colspan="3">${link(p.link)}</td></tr>`);
  return `<table class="grid project"><colgroup><col class="k"><col><col class="k"><col style="width:26%"></colgroup>
${rows.join("\n")}
</table>`;
}

function textBlock(s) {
  const paras = s.body == null ? [] : Array.isArray(s.body) ? s.body : [s.body];
  const items = s.items?.length ? `<ul>${s.items.map((t) => `<li>${fmt(t)}</li>`).join("")}</ul>` : "";
  return `<div class="text">${paras.map((t) => `<p>${fmt(t)}</p>`).join("")}${items}</div>`;
}

const RENDER = {
  table: gridTable,
  skills: skillsTable,
  projects: (s) => (s.items || []).map(projectTable).join("\n"),
  text: textBlock,
};

function section(s, i) {
  const render = RENDER[s.type];
  if (!render) {
    console.error(`알 수 없는 섹션 type: "${s.type}" (sections[${i}]) — table | skills | projects | text`);
    process.exit(2);
  }
  return `<section class="sec-${s.type}${s.pageBreak ? " break" : ""}"><h2>${esc(s.title)}</h2>${render(s)}</section>`;
}

const declaration =
  meta.declaration === false
    ? ""
    : `<div class="decl"><p>위의 기재 사항은 사실과 다름이 없음을 확인합니다.</p>
<p class="date">${esc(meta.date || today())}</p><p class="sign">작성자 <b>${esc(personal.name || "")}</b> (인)</p></div>`;

const accent = style.accent || "#2B2B2B";
const fontCss = [...FONT_STACK, "sans-serif"].map((f) => (f === "sans-serif" ? f : `"${f}"`)).join(", ");

const html = `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>${esc(meta.title || "이력서")} — ${esc(personal.name || "")}</title>
<style>
@page { size: A4; margin: 12mm 13mm 13mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: ${fontCss}; font-size: 9pt; line-height: 1.45; color: #111;
  word-break: keep-all; overflow-wrap: anywhere; }
h1 { text-align: center; font-size: 21pt; font-weight: 800; letter-spacing: 0.7em; padding-left: 0.7em;
  margin: 0 0 3mm; }
h2 { font-size: 10.5pt; font-weight: 800; margin: 3.2mm 0 1.2mm; padding-left: 2mm;
  border-left: 3px solid ${accent}; line-height: 1.2; break-after: avoid; }
section.break { break-before: page; }
section.break h2 { margin-top: 0; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th, td { border: 0.6pt solid #8a8a8a; padding: 0.9mm 2mm; vertical-align: middle; }
th { background: #f1f3f5; font-weight: 700; text-align: center; }
.grid thead th { background: #e7eaee; }
col.k { width: 15mm; }
.grid.kv col.k { width: 31mm; }
.grid.project col.k { width: 17mm; }
tr { break-inside: avoid; }
td.c { text-align: center; } td.l { text-align: left; }
.personal tr { height: 8.4mm; }
.personal col.photo-col { width: 35mm; }
.personal col.k { width: 19mm; }
.personal td.photo { padding: 1mm; text-align: center; background: #fff; }
.personal img { width: 30mm; height: 40mm; object-fit: cover; display: block; margin: 0 auto; }
.project { margin-bottom: 2.6mm; break-inside: avoid; }
.project .ptitle td { font-size: 9.6pt; }
.org { float: right; color: #555; font-size: 8.4pt; padding-top: 0.4mm; }
.muted { color: #444; font-weight: 400; }
ul { margin: 0; padding-left: 4mm; } li { margin: 0.5mm 0; }
li b { white-space: nowrap; }
.text { border: 0.6pt solid #8a8a8a; padding: 2mm 3mm; } .text p { margin: 0.8mm 0; }
section.sec-text { break-inside: avoid; }
a { color: inherit; text-decoration: none; }
.decl { margin-top: 4.5mm; text-align: center; break-inside: avoid; font-size: 10pt; }
.decl p { margin: 1.2mm 0; } .decl .sign { text-align: right; margin-right: 6mm; margin-top: 2mm; }
</style></head>
<body>
<h1>${esc(meta.title || "이력서")}</h1>
${personalTable()}
${(resume.sections || []).map(section).join("\n")}
${declaration}
</body></html>`;

// ---------- Chrome으로 PDF 인쇄 ----------
function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  return candidates.find((p) => fs.existsSync(p));
}
const chrome = findChrome();
if (!chrome) {
  console.error("Chrome/Chromium/Edge를 찾지 못했다 — 설치하거나 CHROME_PATH를 지정");
  process.exit(2);
}

fs.mkdirSync("output", { recursive: true });
const outPdf = path.join("output", `${slug}_resume.pdf`);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "resume-"));
try {
  const htmlPath = path.join(tmp, "resume.html");
  const tmpPdf = path.join(tmp, "resume.pdf");
  fs.writeFileSync(htmlPath, html);
  execFileSync(
    chrome,
    [
      "--headless",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      `--user-data-dir=${path.join(tmp, "chrome")}`,
      "--no-pdf-header-footer",
      `--print-to-pdf=${tmpPdf}`,
      pathToFileURL(htmlPath).href,
    ],
    { stdio: ["ignore", "ignore", "pipe"], timeout: 120000 }
  );
  if (!fs.existsSync(tmpPdf) || fs.statSync(tmpPdf).size === 0) throw new Error("PDF가 만들어지지 않았다");
  fs.copyFileSync(tmpPdf, outPdf);
  if (keepHtml) fs.copyFileSync(htmlPath, outPdf.replace(/\.pdf$/, ".html"));
} catch (e) {
  console.error(`PDF 인쇄 실패 (기존 파일 유지): ${e.message}`);
  process.exit(1);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}

const pages = (fs.readFileSync(outPdf).toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) || []).length;
const maxPages = meta.maxPages; // 선택 — 지정했을 때만 경고
const font = usedFont();
if (font) console.log(`폰트: ${font}${style.font && font !== style.font ? ` (⚠️ "${style.font}" 미설치 → 대체)` : ""}`);
console.log(`✅ ${outPdf} — ${pages}쪽`);
if (maxPages && pages > maxPages) console.warn(`⚠️  ${pages}쪽 > maxPages ${maxPages}쪽`);
