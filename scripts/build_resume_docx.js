#!/usr/bin/env node
/**
 * resume.json + profile/personal.json → 편집 가능한 표준 양식 이력서 Word(.docx)
 *
 * 사용법: node scripts/build_resume_docx.js companies/<slug> [--allow-missing]
 *   입력: companies/<slug>/resume.json, profile/personal.json (+ 사진)
 *   출력: output/<slug>_resume.docx   (개인정보 포함 — output/은 .gitignore)
 *
 * build_resume.js(PDF)와 같은 resume.json을 읽고 같은 순서·양식으로 그린다.
 * Word·한컴오피스·Pages·Google Docs에서 열어 고칠 수 있게 표·글머리표·하이퍼링크를 실제 요소로 만든다.
 * 스키마: .claude/skills/company-resume/reference/resume-schema.md
 */
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, ExternalHyperlink, HeightRule, ImageRun, LevelFormat, Packer,
  Paragraph, ShadingType, Tab, TabStopType, Table, TableCell, TableLayoutType, TableRow, TextRun, VerticalAlign, WidthType,
} = require("docx");

const args = process.argv.slice(2);
const dir = args.find((a) => !a.startsWith("--"));
if (!dir || !fs.existsSync(path.join(dir, "resume.json"))) {
  console.error("사용법: node scripts/build_resume_docx.js companies/<slug> [--allow-missing]");
  process.exit(2);
}
const allowMissing = args.includes("--allow-missing");
const slug = path.basename(path.resolve(dir));
const resume = JSON.parse(fs.readFileSync(path.join(dir, "resume.json"), "utf8"));
const meta = resume.meta || {};
const style = resume.style || {};

// ---------- 인적사항 (build_resume.js와 같은 규칙) ----------
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

// ---------- 단위·토큰 ----------
const MM = 56.7; // 1mm = 56.7 DXA
const dxa = (mm) => Math.round(mm * MM);
const PAGE_W = 11906; // A4
const MARGIN = { top: dxa(12), bottom: dxa(13), left: dxa(13), right: dxa(13) };
const W = PAGE_W - MARGIN.left - MARGIN.right; // 본문 폭
const FONT = style.font || "맑은 고딕"; // 한글
const LATIN = style.latinFont || "Arial"; // 영문·숫자 — 어느 OS에나 있는 산세리프
const SIZE = 18; // 9pt (반 포인트 단위)
const ACCENT = (style.accent || "#2B2B2B").replace("#", "");
const LINE = { style: BorderStyle.SINGLE, size: 4, color: "8A8A8A" };
const BORDERS = { top: LINE, bottom: LINE, left: LINE, right: LINE, insideHorizontal: LINE, insideVertical: LINE };
const HEAD_FILL = { type: ShadingType.CLEAR, color: "auto", fill: "F1F3F5" };
const THEAD_FILL = { type: ShadingType.CLEAR, color: "auto", fill: "E7EAEE" };
const CELL_MARGIN = { top: 35, bottom: 35, left: 110, right: 110 };

// ---------- 텍스트 ----------
// "**굵게**"와 "\n"을 TextRun 묶음으로 (줄바꿈은 같은 문단 안 break)
function runs(text, opts = {}) {
  const out = [];
  String(text ?? "").split("\n").forEach((line, li) => {
    line.split(/(\*\*[^*]+\*\*)/).filter(Boolean).forEach((part, pi) => {
      const bold = part.startsWith("**") && part.endsWith("**");
      out.push(new TextRun({ text: bold ? part.slice(2, -2) : part, bold: bold || opts.bold, size: opts.size, color: opts.color,
        break: li > 0 && pi === 0 ? 1 : undefined }));
    });
  });
  return out.length ? out : [new TextRun("")];
}
// keep: 다음 행과 같은 쪽에 두기 (표가 쪽 사이에서 머리글만 남고 갈라지지 않게)
const para = (text, opts = {}) =>
  new Paragraph({ alignment: opts.align || AlignmentType.LEFT, keepNext: opts.keep, spacing: { before: 0, after: 0, line: 252 }, children: runs(text, opts) });
const dot = (d) => String(d || "").replace(/-/g, ".");
const shown = (url) => String(url).replace(/^https?:\/\//, "").replace(/\/$/, "");
const linkPara = (url, keep) =>
  new Paragraph({ keepNext: keep, children: [new ExternalHyperlink({ link: url.split(" ")[0], children: [new TextRun({ text: shown(url) })] })] });

function cell(children, { width, span = 1, rowSpan, head = false, fill, align, valign = VerticalAlign.CENTER, keep } = {}) {
  const kids = (Array.isArray(children) ? children : [children]).map((c) =>
    typeof c === "string" ? para(c, { bold: head, keep, align: align || (head ? AlignmentType.CENTER : AlignmentType.LEFT) }) : c);
  return new TableCell({
    width: { size: width, type: WidthType.DXA }, columnSpan: span > 1 ? span : undefined, rowSpan,
    shading: fill || (head ? HEAD_FILL : undefined), verticalAlign: valign, margins: CELL_MARGIN, children: kids,
  });
}
function table(columnWidths, rows) {
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths, layout: TableLayoutType.FIXED, borders: BORDERS, rows });
}
const row = (cells, height) =>
  new TableRow({ children: cells, cantSplit: true, height: height ? { value: height, rule: HeightRule.ATLEAST } : undefined });
const sumTo = (ws) => { const s = ws.reduce((a, b) => a + b, 0); ws[ws.length - 1] += W - s; return ws; };

function heading(text, pageBreak = false) {
  return new Paragraph({
    keepNext: true, pageBreakBefore: pageBreak, spacing: { before: pageBreak ? 0 : 150, after: 60 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 5 } },
    children: [new TextRun({ text, bold: true, size: 21 })],
  });
}
const gap = () => new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: "", size: 8 })] });

// ---------- 인적사항 표 ----------
function personalTable() {
  const p = personal;
  const info = meta.info || [];
  const links = p.links || [];
  const photoW = dxa(35), k = dxa(19);
  const v = Math.floor((W - photoW - 2 * k) / 2);
  const cols = sumTo([photoW, k, v, k, v]);
  const span3 = cols[2] + cols[3] + cols[4];
  const nRows = 4 + info.length + links.length;
  const photo = p.photo && fs.existsSync(p.photo)
    ? new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({
        type: path.extname(p.photo).toLowerCase() === ".png" ? "png" : "jpg",
        data: fs.readFileSync(p.photo), transformation: { width: 113, height: 151 } })] })
    : para("");
  const H = dxa(8.6);
  const rows = [
    row([cell(photo, { width: photoW, rowSpan: nRows, fill: { type: ShadingType.CLEAR, color: "auto", fill: "FFFFFF" } }),
      cell("성 명", { width: k, head: true }), cell(p.name || "", { width: cols[2] }),
      cell("영 문", { width: k, head: true }), cell(p.nameEn || "", { width: cols[4] })], H),
    row([cell("생년월일", { width: k, head: true }), cell(dot(p.birth), { width: cols[2] }),
      cell("지원분야", { width: k, head: true }), cell(meta.role || "", { width: cols[4] })], H),
    row([cell("휴 대 폰", { width: k, head: true }), cell(p.phone || "", { width: cols[2] }),
      cell("이 메 일", { width: k, head: true }), cell(p.email || "", { width: cols[4] })], H),
    row([cell("주 소", { width: k, head: true }), cell(p.address || "", { width: span3, span: 3 })], H),
    ...info.map((r) => row([cell(r.label, { width: k, head: true }), cell(r.value, { width: span3, span: 3 })], H)),
    ...links.map((l) => row([cell(l.label, { width: k, head: true }), cell(linkPara(l.url), { width: span3, span: 3 })], H)),
  ];
  return table(cols, rows);
}

// ---------- 섹션 ----------
function gridTable(s) {
  const cols = s.columns || [];
  const rws = s.rows || [];
  const widths = sumTo(cols.map((_, i) => Math.floor(W * (s.widths?.[i] || 100 / cols.length) / 100)));
  const align = cols.map((_, i) => s.align?.[i] || (rws.some((r) => String(r[i] ?? "").length > 24) ? "l" : "c"));
  return table(widths, [
    row(cols.map((c, i) => cell(c, { width: widths[i], head: true, fill: THEAD_FILL, keep: true }))),
    ...rws.map((r, ri) => row(cols.map((_, i) => cell(para(r[i], { keep: ri < rws.length - 1,
      align: align[i] === "l" ? AlignmentType.LEFT : AlignmentType.CENTER }), { width: widths[i] })))),
  ]);
}

function skillsTable(s) {
  const widths = sumTo([dxa(31), W - dxa(31)]);
  const gs = s.groups || [];
  return table(widths, gs.map((g, gi) => { const keep = gi < gs.length - 1;
    return row([cell(g.name, { width: widths[0], head: true, keep }), cell((g.items || []).join(" · "), { width: widths[1], keep })]); }));
}

const bullet = (text, keep) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, keepNext: keep, spacing: { before: 0, after: 0, line: 252 }, children: runs(text) });

function projectTable(p) {
  const k = dxa(17);
  const right = Math.floor(W * 0.26);
  const widths = sumTo([k, W - 2 * k - right, k, right]);
  const span3 = widths[1] + widths[2] + widths[3];
  const titleTabs = p.org ? [{ type: TabStopType.RIGHT, position: span3 - 2 * CELL_MARGIN.left }] : undefined;
  const title = new Paragraph({ tabStops: titleTabs, keepNext: true, children: [
    new TextRun({ text: p.name, bold: true, size: 19 }),
    ...(p.summary ? [new TextRun({ text: " — ", color: "444444" }), ...runs(p.summary, { color: "444444" })] : []),
    ...(p.org ? [new TextRun({ children: [new Tab(), p.org], size: 16, color: "555555" })] : []),
  ] });
  const K = { keep: true };
  const rows = [
    row([cell("프로젝트", { width: k, head: true, ...K }), cell(title, { width: span3, span: 3 })]),
    row([cell("기 간", { width: k, head: true, ...K }), cell(p.period || "", { width: widths[1], ...K }),
      cell("팀 구성", { width: k, head: true, ...K }), cell(p.team || "", { width: widths[3], ...K })]),
  ];
  if (p.role) rows.push(row([cell("역 할", { width: k, head: true, ...K }), cell(para(p.role, K), { width: span3, span: 3 })]));
  if (p.stack?.length) rows.push(row([cell("기 술", { width: k, head: true, ...K }), cell(p.stack.join(" · "), { width: span3, span: 3, ...K })]));
  if (p.bullets?.length) rows.push(row([cell("주요 내용", { width: k, head: true, keep: !!p.link }),
    cell(p.bullets.map((b) => bullet(b, !!p.link)), { width: span3, span: 3 })]));
  if (p.link) rows.push(row([cell("링 크", { width: k, head: true }), cell(linkPara(p.link), { width: span3, span: 3 })]));
  return table(widths, rows);
}

function textBlock(s) {
  const paras = s.body == null ? [] : Array.isArray(s.body) ? s.body : [s.body];
  const kids = [...paras.map((t) => para(t)), ...(s.items || []).map((t) => bullet(t))];
  return table([W], [row([cell(kids.length ? kids : [para("")], { width: W, valign: VerticalAlign.TOP })])]);
}

const RENDER = {
  table: (s) => [gridTable(s)],
  skills: (s) => [skillsTable(s)],
  projects: (s) => (s.items || []).flatMap((p, i) => (i ? [gap(), projectTable(p)] : [projectTable(p)])),
  text: (s) => [textBlock(s)],
};

function today() {
  const d = new Date();
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
    children: [new TextRun({ text: meta.title || "이력서", bold: true, size: 42, characterSpacing: 400 })] }),
  personalTable(),
];
(resume.sections || []).forEach((s, i) => {
  const render = RENDER[s.type];
  if (!render) {
    console.error(`알 수 없는 섹션 type: "${s.type}" (sections[${i}]) — table | skills | projects | text`);
    process.exit(2);
  }
  body.push(heading(s.title, !!s.pageBreak), ...render(s));
});
if (meta.declaration !== false) {
  body.push(new Paragraph({
    spacing: { before: 140 }, tabStops: [{ type: TabStopType.RIGHT, position: W - 60 }],
    children: [
      new TextRun({ text: `위의 기재 사항은 사실과 다름이 없음을 확인합니다.    ${meta.date || today()}`, size: 20 }),
      new TextRun({ children: [new Tab(), "작성자 "], size: 20 }),
      new TextRun({ text: personal.name || "", bold: true, size: 20 }),
      new TextRun({ text: " (인)", size: 20 }),
    ],
  }));
}

const doc = new Document({
  creator: personal.name || "",
  title: `${meta.title || "이력서"} — ${personal.name || ""}`,
  styles: {
    default: { document: { run: { font: { ascii: LATIN, eastAsia: FONT, hAnsi: LATIN, cs: LATIN }, size: SIZE } } },
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 220, hanging: 160 } } } }] }] },
  sections: [{ properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: MARGIN } }, children: body }],
});

fs.mkdirSync("output", { recursive: true });
const out = path.join("output", `${slug}_resume.docx`);
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log(`✅ ${out} — 글꼴: ${FONT} / ${LATIN} (Word·한컴오피스·Pages·Google Docs에서 편집)`);
});
