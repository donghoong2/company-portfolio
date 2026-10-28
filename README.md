# 기업 맞춤 포트폴리오 생성기

지원 기업명을 입력하면 Claude Code 에이전트가 **인재상·채용공고(지원자격/우대사항)·브랜드 디자인**을 조사하고,
Notion 프로필의 경험을 그 기준에 맞춰 재구성한 **기업 맞춤 포트폴리오 PPTX**를 만든다.

```
/company-portfolio <기업명> [직무] [채용공고 URL]
```

## 파이프라인

1. **프로필 수집** — `scripts/notion_export.py`가 공개 Notion 페이지(DB·하위 페이지 포함)를 Markdown으로 변환
2. **기업 조사 (병렬 서브에이전트)**
   - `company-researcher` → 인재상·핵심가치·채용공고·기술 스택 → `research.md`
   - `brand-researcher` → 브랜드 컬러·폰트·디자인 톤 → `brand.json`
3. **매칭** — 경험 ↔ 인재상/자격요건 매핑 → `mapping.md`
4. **덱 작성** — 슬라이드 내용 `deck.json`
5. **렌더링** — `scripts/build_deck.js`(pptxgenjs)가 brand 토큰 + 내용으로 PPTX 생성
6. **검수** — `scripts/preview.sh`로 PNG 미리보기 후 수정

프로필에 있는 경험·수치만 사용하며 과장·창작하지 않는다 (`CLAUDE.md` 규칙).

## 구조

```
.claude/agents/            company-researcher, brand-researcher 서브에이전트
.claude/skills/            company-portfolio 스킬 (전체 절차, 스키마)
scripts/                   notion_export.py, build_deck.js, preview.sh
companies/_sample/         brand.json / deck.json 예시
output/_sample_portfolio.pptx
```

`profile/`, `companies/<기업>/`, `output/`의 실제 지원 자료는 `.gitignore`로 제외한다.

## 요구 사항

- [Claude Code](https://claude.com/claude-code)
- Node.js (`npm install`), Python 3
- 미리보기: LibreOffice 또는 Keynote
