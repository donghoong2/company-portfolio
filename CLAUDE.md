# 기업 맞춤 포트폴리오 생성기

지원 기업명을 입력하면 인재상·지원자격·우대사항·브랜드 디자인을 조사하고, 지원자의 Notion 프로필 경험을 그에 맞춰 재구성한 포트폴리오 PPTX를 만든다.

**사용법:** `/company-portfolio <기업명> [직무] [채용공고 URL]` — 전체 절차는 `.claude/skills/company-portfolio/SKILL.md`.

## 구조

```
profile/notion_profile.md      Notion에서 내보낸 지원자 프로필 (사실 출처)
profile/supplements.md         Notion 밖에서 사용자에게 직접 받은 사실 (사실 출처, 기업 간 재사용)
companies/<slug>/              기업별 작업물
  research.md                  인재상·채용공고 조사 (company-researcher)
  brand.json                   컬러·폰트·스타일 토큰 (brand-researcher)
  mapping.md                   경험 ↔ 인재상/자격 매칭 분석
  deck.json                    슬라이드 내용
  review/                      면접관 리뷰 (posting.md, reviewer-<n>.md, loop.md)
  assets/                      덱에 쓰는 이미지
companies/_sample/             렌더러 예시 (스키마 참고용)
output/<slug>_portfolio.pptx   결과물
output/preview/<name>/         검수용 PNG
scripts/notion_export.py       공개 Notion 페이지 → Markdown (DB·하위 페이지 포함)
scripts/check_facts.py         deck.json 수치 ↔ 사실 출처 대조 (빌드 전 필수)
scripts/build_deck.js          brand.json + deck.json → PPTX (pptxgenjs)
scripts/preview.sh             PPTX → PNG (LibreOffice 또는 Keynote)
```

## 규칙

- 지원자 경험·수치는 `profile/notion_profile.md`·`profile/supplements.md`에 있는 것만 쓴다. 과장·창작 금지, 팀 성과는 팀 성과로 표기. 빌드 전에 `check_facts.py`를 통과시킨다.
- 덱 품질은 `portfolio-reviewer`(PNG + 채용공고만 보는 블라인드 면접관)로 검증한다. 리뷰어에게 작성 의도나 매칭 분석을 넘기지 않는다.
- 덱 디자인 변경은 `brand.json`(토큰)과 `deck.json`(내용)으로 해결하고, 새 레이아웃이 꼭 필요할 때만 `build_deck.js`에 slide 타입을 추가한다 (추가 시 `reference/schemas.md`도 갱신).
- 브랜드 폰트는 자동 설치하지 않는다. 미설치 시 빌드가 fallback으로 대체하므로 사용자에게 설치를 안내한다.
- Keynote 첫 실행은 느리다 — preview.sh에 충분한 timeout(600s)을 준다.
