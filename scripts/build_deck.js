#!/usr/bin/env node
/**
 * brand.json + deck.json → 기업 맞춤 포트폴리오 PPTX
 *
 * 사용법: node scripts/build_deck.js companies/<slug> [--force-brand-fonts]
 *   입력: companies/<slug>/brand.json, companies/<slug>/deck.json
 *   출력: output/<slug>_portfolio.pptx
 *
 * 스키마는 .claude/skills/company-portfolio/reference/schemas.md 참고.
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const pptxgen = require("pptxgenjs");

const dir = process.argv[2];
if (!dir) {
  console.error("사용법: node scripts/build_deck.js companies/<slug> [--force-brand-fonts]");
  process.exit(1);
}
const forceBrandFonts = process.argv.includes("--force-brand-fonts");
const slug = path.basename(path.resolve(dir));
const brand = JSON.parse(fs.readFileSync(path.join(dir, "brand.json"), "utf8"));
const deck = JSON.parse(fs.readFileSync(path.join(dir, "deck.json"), "utf8"));

// ---------- 브랜드 토큰 ----------
const hex = (c, d) => String(c || d).replace("#", "").toUpperCase();
const C = {
  primary: hex(brand.colors?.primary, "1F6FEB"),
  secondary: hex(brand.colors?.secondary || brand.colors?.primary, "1F6FEB"),
  accent: hex(brand.colors?.accent || brand.colors?.primary, "F59E0B"),
  bg: hex(brand.colors?.background, "FFFFFF"),
  surface: hex(brand.colors?.surface, "F3F4F6"),
  text: hex(brand.colors?.text, "111827"),
  muted: hex(brand.colors?.muted, "6B7280"),
  onPrimary: hex(brand.colors?.onPrimary, "FFFFFF"),
  border: hex(brand.colors?.border || brand.colors?.surface, "E5E7EB"),
};
const style = {
  corner: "rounded",
  coverStyle: "split",
  accentShape: "bar",
  sectionStyle: "solid",
  ...(brand.style || {}),
};

function installedFamilies() {
  try {
    return execSync("fc-list : family", { encoding: "utf8" }).toLowerCase();
  } catch {
    return null;
  }
}
const families = installedFamilies();
const warned = new Set();
function resolveFont(name, fallback) {
  if (!name) return fallback;
  if (forceBrandFonts || families === null) return name;
  if (families.includes(name.toLowerCase())) return name;
  if (warned.has(name)) return fallback;
  warned.add(name);
  console.warn(`⚠️  폰트 미설치: "${name}" → "${fallback}"로 대체 (설치 후 재빌드하거나 --force-brand-fonts 사용)`);
  return fallback;
}
const fallbackFont = brand.fonts?.fallback || "Apple SD Gothic Neo";
const F = {
  head: resolveFont(brand.fonts?.heading, fallbackFont),
  body: resolveFont(brand.fonts?.body, fallbackFont),
};

// ---------- 레이아웃 상수/유틸 ----------
const W = 13.333, H = 7.5, M = 0.6;
const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = deck.meta?.author || "";
pptx.company = brand.company || "";
pptx.title = deck.meta?.title || `${brand.company} Portfolio`;

const SHAPE = () => (style.corner === "sharp" ? pptx.ShapeType.rect : pptx.ShapeType.roundRect);
const RADIUS = style.corner === "pill" ? 0.3 : 0.12;

const isWide = (ch) => /[ᄀ-ᇿ　-鿿가-힯＀-￯]/.test(ch);
function textWidthIn(str, size) {
  let w = 0;
  for (const ch of String(str)) w += (isWide(ch) ? 1.0 : 0.56) * (size / 72);
  return w;
}
// 박스에 들어가는 최대 폰트 크기 추정
function fit(text, boxW, boxH, max, min = 9, lineH = 1.35) {
  const paras = Array.isArray(text) ? text : String(text || "").split("\n");
  for (let s = max; s >= min; s -= 0.5) {
    const usableW = boxW - 0.2;
    let lines = 0;
    for (const p of paras) lines += Math.max(1, Math.ceil(textWidthIn(p, s) / usableW));
    if (lines * s * lineH / 72 + 0.1 <= boxH) return s;
  }
  return min;
}

function textHeightIn(text, boxW, size, lineH = 1.35) {
  const paras = Array.isArray(text) ? text : String(text || "").split("\n");
  let lines = 0;
  for (const p of paras) lines += Math.max(1, Math.ceil(textWidthIn(p, size) / (boxW - 0.2)));
  return lines * size * lineH / 72 + 0.1;
}

function box(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(SHAPE(), {
    x, y, w, h,
    fill: { color: fill },
    line: opts.line ? { color: opts.line, width: 0.75 } : { type: "none" },
    rectRadius: RADIUS,
    ...opts.extra,
  });
}

function txt(slide, text, x, y, w, h, o = {}) {
  slide.addText(text, {
    x, y, w, h,
    fontFace: o.head ? F.head : F.body,
    fontSize: o.size || 14,
    color: o.color || C.text,
    bold: !!o.bold,
    align: o.align || "left",
    valign: o.valign || "top",
    margin: o.margin ?? 0.05,
    lineSpacingMultiple: o.lineSpacing || 1.15,
    paraSpaceAfter: o.paraAfter || 0,
    ...o.extra,
  });
}

function pills(slide, items, x, y, maxW, o = {}) {
  const size = o.size || 10.5, h = o.h || 0.32, gap = 0.08;
  let cx = x, cy = y;
  for (const it of items || []) {
    const w = textWidthIn(it, size) + 0.3;
    if (cx + w > x + maxW && cx > x) { cx = x; cy += h + gap; }
    slide.addShape(pptx.ShapeType.roundRect, {
      x: cx, y: cy, w, h, rectRadius: h / 2,
      fill: { color: o.fill || C.surface }, line: { type: "none" },
    });
    txt(slide, it, cx, cy, w, h, { size, color: o.color || C.text, align: "center", valign: "middle", margin: 0 });
    cx += w + gap;
  }
  return cy + h;
}

function accentMark(slide, x, y, color = style.markColor === "accent" ? C.accent : C.primary) {
  if (style.accentShape === "bar") slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.5, h: 0.07, fill: { color }, line: { type: "none" } });
  else if (style.accentShape === "dot") slide.addShape(pptx.ShapeType.ellipse, { x, y: y - 0.03, w: 0.14, h: 0.14, fill: { color }, line: { type: "none" } });
}

let pageNo = 0;
function base(s, opts = {}) {
  const slide = pptx.addSlide();
  pageNo += 1;
  slide.background = { color: opts.bg || C.bg };
  if (s.notes) slide.addNotes(s.notes);
  if (opts.chrome === false) return slide;
  if (s.label) txt(slide, s.label.toUpperCase(), M, 0.35, 8, 0.3, { size: 10, color: C.primary, bold: true, extra: { charSpacing: 1 } });
  accentMark(slide, M, 0.72);
  if (s.title) txt(slide, s.title, M, 0.82, W - 2 * M, 0.7, { head: true, bold: true, size: fit(s.title, W - 2 * M, 0.7, 26, 18), valign: "middle" });
  if (s.lead) txt(slide, s.lead, M, 1.5, W - 2 * M, 0.45, { size: 13, color: C.muted, valign: "middle" });
  // footer
  txt(slide, `${deck.meta?.author || ""} · Portfolio for ${brand.company || ""}`, M, H - 0.45, 7, 0.3, { size: 9, color: C.muted, valign: "middle" });
  txt(slide, String(pageNo).padStart(2, "0"), W - M - 1, H - 0.45, 1, 0.3, { size: 9, color: C.muted, align: "right", valign: "middle" });
  if (brand.logo && fs.existsSync(path.join(dir, brand.logo))) {
    slide.addImage({ path: path.join(dir, brand.logo), x: W - M - 1.1, y: 0.32, w: 1.1, h: 0.36, sizing: { type: "contain", w: 1.1, h: 0.36 } });
  }
  return slide;
}
const contentTop = (s) => (s.lead ? 2.1 : 1.75);

// ---------- 슬라이드 렌더러 ----------
const R = {};

R.cover = (s) => {
  const slide = base(s, { chrome: false, bg: style.coverStyle === "solid" ? C.primary : C.bg });
  const meta = deck.meta || {};
  const label = s.label || `PORTFOLIO · ${meta.role || ""}`;
  let x = M + 0.2, w = W - 2 * M - 0.4, fg = C.text, sub = C.muted, hl = C.primary;
  if (style.coverStyle === "solid") { fg = C.onPrimary; sub = C.onPrimary; hl = style.markColor === "accent" ? C.accent : C.onPrimary; }
  if (style.coverStyle === "split") {
    slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W * 0.36, h: H, fill: { color: C.primary }, line: { type: "none" } });
    txt(slide, brand.company || "", 0.6, H - 1.3, W * 0.36 - 1.0, 0.6, { head: true, bold: true, size: 22, color: C.onPrimary });
    x = W * 0.36 + 0.7; w = W - x - M;
  }
  if (style.coverStyle === "minimal") slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.25, h: H, fill: { color: C.primary }, line: { type: "none" } });
  txt(slide, label, x, 1.6, w, 0.4, { size: 13, bold: true, color: hl, extra: { charSpacing: 2 } });
  txt(slide, s.headline, x, 2.1, w, 2.2, { head: true, bold: true, size: fit(s.headline, w, 2.2, 40, 26, 1.25), color: fg, lineSpacing: 1.1, valign: "top" });
  if (s.subhead) txt(slide, s.subhead, x, 4.35, w, 0.9, { size: fit(s.subhead, w, 0.9, 17, 12), color: sub });
  txt(slide, [
    { text: meta.author || "", options: { bold: true, fontSize: 16, color: fg, breakLine: true } },
    { text: [meta.contact, meta.date].filter(Boolean).join("  ·  "), options: { fontSize: 11, color: sub } },
  ], x, H - 1.5, w, 0.8, { valign: "bottom" });
};

R.profile = (s) => {
  const slide = base(s);
  const top = contentTop(s), lw = 6.1;
  txt(slide, s.name || deck.meta?.author || "", M, top, lw, 0.6, { head: true, bold: true, size: 28 });
  if (s.role) txt(slide, s.role, M, top + 0.6, lw, 0.4, { size: 14, color: C.primary, bold: true });
  const maxIntroH = 2.6;
  const introSize = fit(s.intro, lw, maxIntroH, 15, 10.5, 1.45);
  const introH = Math.min(maxIntroH, textHeightIn(s.intro, lw, introSize, 1.45));
  txt(slide, s.intro || "", M, top + 1.1, lw, introH, { size: introSize, lineSpacing: 1.3 });
  pills(slide, s.keywords, M, top + 1.3 + introH, lw, { fill: C.primary, color: C.onPrimary });
  // 오른쪽: 정보 + 역량
  const rx = M + lw + 0.5, rw = W - rx - M;
  let y = top;
  for (const it of s.info || []) {
    txt(slide, it.label, rx, y, 1.3, 0.35, { size: 11, color: C.muted, bold: true });
    txt(slide, it.value, rx + 1.3, y, rw - 1.3, 0.35, { size: fit(it.value, rw - 1.3, 0.35, 12, 9) });
    y += 0.36;
  }
  y += 0.15;
  const comps = s.competencies || [];
  const ch = comps.length ? Math.min(1.25, (H - 0.8 - y) / comps.length - 0.12) : 0;
  for (const c of comps) {
    box(slide, rx, y, rw, ch, C.surface);
    txt(slide, c.title, rx + 0.2, y + 0.06, rw - 0.4, 0.32, { bold: true, size: 13, color: C.primary });
    txt(slide, c.desc, rx + 0.2, y + 0.38, rw - 0.4, ch - 0.42, { size: fit(c.desc, rw - 0.4, ch - 0.42, 11.5, 10, 1.3), lineSpacing: 1.05 });
    y += ch + 0.12;
  }
};

R.fit = (s) => {
  const slide = base(s);
  const items = s.items || [];
  const top = contentTop(s), n = items.length;
  const cols = n <= 3 ? n : 2, rows = Math.ceil(n / cols), gap = 0.25;
  const cw = (W - 2 * M - gap * (cols - 1)) / cols;
  const chh = (H - 0.75 - top - gap * (rows - 1)) / rows;
  items.forEach((it, i) => {
    const x = M + (i % cols) * (cw + gap), y = top + Math.floor(i / cols) * (chh + gap);
    box(slide, x, y, cw, chh, C.surface);
    slide.addShape(pptx.ShapeType.rect, { x, y: y + 0.2, w: 0.08, h: 0.5, fill: { color: C.primary }, line: { type: "none" } });
    txt(slide, it.value, x + 0.3, y + 0.15, cw - 0.5, 0.45, { head: true, bold: true, size: 16, color: C.primary, valign: "middle" });
    if (it.desc) txt(slide, it.desc, x + 0.3, y + 0.62, cw - 0.5, 0.45, { size: fit(it.desc, cw - 0.5, 0.45, 10.5, 8.5), color: C.muted });
    const ey = y + (it.desc ? 1.1 : 0.7), eh = chh - (ey - y) - 0.15;
    txt(slide, it.evidence, x + 0.3, ey, cw - 0.5, eh, { size: fit(it.evidence, cw - 0.5, eh, 15, 9, 1.4), lineSpacing: 1.3 });
  });
};

R.requirements = (s) => {
  const slide = base(s);
  const top = contentTop(s);
  const head = ["구분", "요구 역량", "나의 근거", "관련 경험"].map((t) => ({
    text: t, options: { bold: true, color: C.onPrimary, fill: { color: C.primary }, fontFace: F.head, fontSize: 11, align: "center", valign: "middle" },
  }));
  const rows = (s.rows || []).map((r) => [
    { text: r.kind || "", options: { bold: true, align: "center", color: ["필수", "공식", "자격"].includes(r.kind) ? C.primary : (style.markColor === "accent" ? C.secondary : C.accent) } },
    { text: r.req || "" },
    { text: r.evidence || "" },
    { text: r.project || "", options: { color: C.muted } },
  ]);
  const n = Math.max(rows.length, 1);
  const size = n > 7 ? 9 : n > 5 ? 10 : 11;
  slide.addTable([head, ...rows], {
    x: M, y: top, w: W - 2 * M, colW: [0.9, 3.4, 5.7, W - 2 * M - 10.0],
    fontFace: F.body, fontSize: size, color: C.text, valign: "middle",
    border: { type: "solid", pt: 0.5, color: C.border },
    fill: { color: C.bg }, rowH: Math.min(0.75, (H - 0.8 - top) / (n + 1)),
    autoPage: false, margin: 0.06,
  });
};

R.section = (s) => {
  const solid = style.sectionStyle !== "light";
  const slide = base(s, { chrome: false, bg: solid ? C.primary : C.surface });
  const fg = solid ? C.onPrimary : C.text, hl = solid ? C.onPrimary : C.primary;
  txt(slide, s.no || "", M + 0.2, 2.0, 4, 1.2, { head: true, bold: true, size: 60, color: hl });
  txt(slide, s.title || "", M + 0.2, 3.3, W - 2 * M, 1.0, { head: true, bold: true, size: fit(s.title, W - 2 * M, 1.0, 34, 22), color: fg });
  if (s.subtitle) txt(slide, s.subtitle, M + 0.2, 4.35, W - 2 * M - 1, 1.0, { size: 15, color: fg });
  if (s.tags) pills(slide, s.tags, M + 0.2, 5.5, W - 2 * M, { fill: solid ? C.onPrimary : C.primary, color: solid ? C.primary : C.onPrimary });
};

R.project = (s) => {
  const slide = base(s);
  const top = contentTop(s), lw = 5.6, rx = M + lw + 0.45, rw = W - rx - M;
  if (s.fitTags) pills(slide, s.fitTags, M, top, lw, { fill: C.primary, color: C.onPrimary, size: 10 });
  let y = top + (s.fitTags ? 0.5 : 0);
  txt(slide, s.summary || "", M, y, lw, 1.5, { size: fit(s.summary, lw, 1.5, 14, 10, 1.45), lineSpacing: 1.3 });
  y += 1.6;
  for (const [k, v] of [["기간", s.period], ["팀 구성", s.team], ["역할", s.role]]) {
    if (!v) continue;
    txt(slide, k, M, y, 1.0, 0.32, { size: 11, color: C.muted, bold: true });
    txt(slide, v, M + 1.0, y, lw - 1.0, 0.32, { size: fit(v, lw - 1.0, 0.32, 11.5, 8.5) });
    y += 0.36;
  }
  y += 0.15;
  pills(slide, s.stack, M, y, lw, { size: 10 });
  // 우측: 지표 + 기여
  const metrics = s.metrics || [];
  let ry = top;
  if (metrics.length) {
    const gap = 0.18, mw = (rw - gap * (metrics.length - 1)) / metrics.length;
    metrics.forEach((m, i) => {
      const x = rx + i * (mw + gap);
      box(slide, x, ry, mw, 1.35, C.primary);
      txt(slide, m.value, x + 0.1, ry + 0.12, mw - 0.2, 0.7, { head: true, bold: true, size: fit(m.value, mw - 0.2, 0.7, 26, 14, 1.1), color: C.onPrimary, align: "center", valign: "middle" });
      txt(slide, m.label, x + 0.1, ry + 0.82, mw - 0.2, 0.45, { size: fit(m.label, mw - 0.2, 0.45, 10.5, 8), color: C.onPrimary, align: "center" });
    });
    ry += 1.6;
  }
  if (s.image && fs.existsSync(path.resolve(s.image))) {
    const ih = H - 0.8 - ry;
    slide.addImage({ path: path.resolve(s.image), x: rx, y: ry, w: rw, h: ih, sizing: { type: "contain", w: rw, h: ih } });
    return;
  }
  const items = s.contributions || [];
  const ch = H - 0.8 - ry;
  txt(slide, "담당 및 기여", rx, ry, rw, 0.35, { bold: true, size: 13, color: C.primary });
  const size = fit(items.map((t) => "• " + t), rw, ch - 0.45, 12.5, 9, 1.5);
  slide.addText(items.map((t) => ({ text: t, options: { bullet: { indent: 14 }, paraSpaceAfter: 5 } })), {
    x: rx, y: ry + 0.42, w: rw, h: ch - 0.45, fontFace: F.body, fontSize: size, color: C.text, valign: "top", lineSpacingMultiple: 1.2, margin: 0.05,
  });
};

R.star = (s) => {
  const slide = base(s);
  const top = contentTop(s) + (s.fitTag ? 0.45 : 0);
  if (s.fitTag) pills(slide, [s.fitTag], M, contentTop(s), 6, { fill: C.primary, color: C.onPrimary, size: 10 });
  const cols = [
    { k: "문제", v: [s.context, s.problem].filter(Boolean) },
    { k: "해결", v: s.action || [] },
    { k: "결과", v: s.result || [] },
  ];
  const gap = 0.45, cw = (W - 2 * M - gap * 2) / 3, maxH = H - 0.8 - top;
  const lists = cols.map((c) => (Array.isArray(c.v) ? c.v : [c.v]).map((t) => "• " + t));
  const size = Math.min(...lists.map((l) => fit(l, cw - 0.5, maxH - 0.9, 15, 9, 1.5)));
  const need = Math.max(...lists.map((l) => textHeightIn(l, cw - 0.5, size, 1.5) + l.length * 0.08));
  const ch = Math.min(maxH, Math.max(2.8, need + 1.1));
  cols.forEach((c, i) => {
    const x = M + i * (cw + gap);
    const highlight = i === 2;
    box(slide, x, top, cw, ch, highlight ? C.primary : C.surface);
    const fg = highlight ? C.onPrimary : C.text;
    txt(slide, c.k, x + 0.25, top + 0.2, cw - 0.5, 0.4, { head: true, bold: true, size: 15, color: highlight ? C.onPrimary : C.primary });
    const items = Array.isArray(c.v) ? c.v : [c.v];
    slide.addText(items.map((t) => ({ text: t, options: { bullet: { indent: 12 }, paraSpaceAfter: 6 } })), {
      x: x + 0.25, y: top + 0.7, w: cw - 0.5, h: ch - 0.9, fontFace: F.body, fontSize: size, color: fg, valign: "top", lineSpacingMultiple: 1.2, margin: 0.03,
    });
    if (i < 2) slide.addShape(pptx.ShapeType.rightArrow, { x: x + cw + 0.1, y: top + ch / 2 - 0.15, w: 0.25, h: 0.3, fill: { color: C.muted }, line: { type: "none" } });
  });
};

R.architecture = (s) => {
  const slide = base(s);
  const top = contentTop(s), layers = s.layers || [];
  const capH = s.caption ? 0.5 : 0, gap = 0.15;
  const lh = Math.min(1.0, (H - 0.8 - top - capH - gap * (layers.length - 1)) / Math.max(layers.length, 1));
  layers.forEach((l, i) => {
    const y = top + i * (lh + gap);
    box(slide, M, y, 2.0, lh, C.primary);
    txt(slide, l.name, M + 0.1, y, 1.8, lh, { bold: true, size: fit(l.name, 1.8, lh, 12, 9), color: C.onPrimary, align: "center", valign: "middle" });
    const items = l.items || [], ix = M + 2.2, iw = W - M - ix, g = 0.12;
    const bw = (iw - g * (items.length - 1)) / Math.max(items.length, 1);
    items.forEach((it, j) => {
      box(slide, ix + j * (bw + g), y, bw, lh, C.surface, { line: C.border });
      txt(slide, it, ix + j * (bw + g) + 0.05, y, bw - 0.1, lh, { size: fit(it, bw - 0.1, lh, 12, 8), align: "center", valign: "middle" });
    });
  });
  if (s.caption) txt(slide, s.caption, M, H - 0.8 - capH + 0.05, W - 2 * M, capH, { size: 11, color: C.muted, valign: "middle" });
};

R.activities = (s) => {
  const slide = base(s);
  const top = contentTop(s), items = s.items || [];
  const rh = Math.min(1.05, (H - 0.8 - top) / Math.max(items.length, 1) - 0.1);
  items.forEach((it, i) => {
    const y = top + i * (rh + 0.1);
    box(slide, M, y, W - 2 * M, rh, C.surface);
    txt(slide, it.period || "", M + 0.2, y, 1.9, rh, { size: 10.5, color: C.muted, valign: "middle" });
    txt(slide, [
      { text: it.name || "", options: { bold: true, fontSize: 13.5, color: C.text, breakLine: true } },
      { text: it.role || "", options: { fontSize: 10.5, color: C.primary } },
    ], M + 2.1, y, 3.4, rh, { valign: "middle" });
    const dw = W - 2 * M - 5.7 - (it.fitTag ? 1.9 : 0);
    txt(slide, it.desc || "", M + 5.6, y, dw, rh, { size: fit(it.desc, dw, rh, 11.5, 8.5), valign: "middle" });
    if (it.fitTag) pills(slide, [it.fitTag], W - M - 1.85, y + rh / 2 - 0.16, 1.75, { fill: C.primary, color: C.onPrimary, size: 9.5 });
  });
};

R.skills = (s) => {
  const slide = base(s);
  const top = contentTop(s), groups = s.groups || [];
  const cols = groups.length > 4 ? 3 : 2, gap = 0.22;
  const rows = Math.ceil(groups.length / cols);
  const cw = (W - 2 * M - gap * (cols - 1)) / cols;
  const maxH = (H - 0.8 - top - gap * (rows - 1)) / Math.max(rows, 1);
  let pillSize = 11.5, pillH = 0.38;
  const pillRows = (items) => {
    let r = 1, cx = 0;
    for (const it of items || []) {
      const w = textWidthIn(it, pillSize) + 0.3;
      if (cx + w > cw - 0.4 && cx > 0) { r += 1; cx = 0; }
      cx += w + 0.08;
    }
    return r;
  };
  const needH = () => Math.max(...groups.map((g) => 0.75 + pillRows(g.items) * (pillH + 0.08))) + 0.15;
  while (needH() > maxH && pillSize > 9) { pillSize -= 0.5; pillH = Math.max(0.3, pillH - 0.02); }
  const chh = Math.min(maxH, needH());
  groups.forEach((g, i) => {
    const x = M + (i % cols) * (cw + gap), y = top + Math.floor(i / cols) * (chh + gap);
    box(slide, x, y, cw, chh, C.surface);
    txt(slide, g.name, x + 0.2, y + 0.15, cw - 0.4, 0.4, { bold: true, size: 14, color: C.primary });
    pills(slide, g.items, x + 0.2, y + 0.65, cw - 0.4, { fill: C.bg, size: pillSize, h: pillH });
  });
};

R.image = (s) => {
  const slide = base(s);
  const top = contentTop(s), capH = s.caption ? 0.5 : 0, ih = H - 0.8 - top - capH;
  if (s.path && fs.existsSync(path.resolve(s.path))) {
    slide.addImage({ path: path.resolve(s.path), x: M, y: top, w: W - 2 * M, h: ih, sizing: { type: "contain", w: W - 2 * M, h: ih } });
  } else {
    box(slide, M, top, W - 2 * M, ih, C.surface, { line: C.border });
    txt(slide, `이미지 없음: ${s.path || "(경로 미지정)"}`, M, top, W - 2 * M, ih, { color: C.muted, align: "center", valign: "middle" });
  }
  if (s.caption) txt(slide, s.caption, M, top + ih + 0.05, W - 2 * M, capH, { size: 11, color: C.muted, align: "center" });
};

R.closing = (s) => {
  const slide = base(s, { chrome: false, bg: C.primary });
  txt(slide, s.message || "감사합니다", M + 0.2, 2.0, W - 2 * M - 0.4, 2.2, { head: true, bold: true, size: fit(s.message, W - 2 * M - 0.4, 2.2, 36, 22, 1.25), color: C.onPrimary, valign: "bottom" });
  if (s.sub) txt(slide, s.sub, M + 0.2, 4.35, W - 2 * M - 0.4, 0.9, { size: 15, color: C.onPrimary });
  txt(slide, (s.contacts || []).join("\n"), M + 0.2, H - 1.6, W - 2 * M, 1.0, { size: 12, color: C.onPrimary, valign: "bottom" });
};

// ---------- 빌드 ----------
for (const s of deck.slides || []) {
  const fn = R[s.type];
  if (!fn) { console.warn(`⚠️  알 수 없는 슬라이드 타입: ${s.type} (건너뜀)`); continue; }
  fn(s);
}
fs.mkdirSync("output", { recursive: true });
const out = path.join("output", `${slug}_portfolio.pptx`);
pptx.writeFile({ fileName: out }).then(() => {
  console.log(`✅ ${out} (${pageNo} slides, fonts: ${F.head} / ${F.body})`);
});
