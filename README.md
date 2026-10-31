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
4. **보충 질문** — 프로필로 채울 수 없는 빈 곳(미충족 요건, 원인·전후 수치·측정 조건·선택 이유)을 한 번에 묻고 답을 `profile/supplements.md`에 출처와 함께 쌓는다. 다음 기업 덱에서도 재사용
5. **덱 작성** — 슬라이드 내용 `deck.json`
6. **수치 검사** — `scripts/check_facts.py`가 덱의 수치를 사실 출처와 대조. 출처에 없는 수치가 있으면 빌드하지 않음
7. **렌더링** — `scripts/build_deck.js`(pptxgenjs)가 brand 토큰 + 내용으로 PPTX 생성
8. **시각 검수** — `scripts/preview.sh`로 PNG 미리보기 후 넘침·겹침 수정
9. **면접관 리뷰 루프 (최대 3회)** — `portfolio-reviewer`가 슬라이드 PNG와 채용공고**만** 보고 7개 기준(35점)으로 평가
   - `[수정]` 지적은 바로 고치고, `[질문]` 지적은 사실 출처에서 먼저 답을 찾은 뒤 남은 것만 사용자에게 묻는다
   - 리뷰어가 인용한 문장이 덱에 실제로 있는지 `check_facts.py --find`로 확인하고, 사용자가 "그대로 둘게요"라고 한 지적은 거절 목록으로 걸러낸다

### 사실 출처

지원자 경험·수치는 `profile/notion_profile.md`와 `profile/supplements.md`에 있는 것만 쓴다. 과장·창작하지 않고, 팀 성과는 팀 성과로 표기한다 (`CLAUDE.md` 규칙).
출처 수치로 계산한 값(감소율 등)은 `deck.json`의 `derived`에 근거를 적어야 수치 검사를 통과한다.

```bash
python3 scripts/check_facts.py companies/<slug>                 # 수치 검사
python3 scripts/check_facts.py companies/<slug> --find "<문장>"  # 문장이 몇 번 슬라이드에 있는지
```

## 구조

```
.claude/agents/            company-researcher, brand-researcher, portfolio-reviewer 서브에이전트
.claude/skills/            company-portfolio 스킬 (전체 절차, 스키마)
scripts/                   notion_export.py, check_facts.py, build_deck.js, preview.sh
profile/                   notion_profile.md, supplements.md (지원자 사실 출처)
companies/<slug>/review/   posting.md(리뷰어용 공고), reviewer-<n>.md, loop.md(점수·거절 목록)
companies/_sample/         brand.json / deck.json 예시
output/_sample_portfolio.pptx
```

`profile/`, `companies/<기업>/`, `output/`의 실제 지원 자료는 `.gitignore`로 제외한다.

## 요구 사항

- [Claude Code](https://claude.com/claude-code)
- Node.js (`npm install`), Python 3
- 미리보기·리뷰: LibreOffice + poppler(`brew install --cask libreoffice && brew install poppler`) 또는 Keynote. 리뷰 루프는 미리보기 PNG가 있어야 돌아간다
