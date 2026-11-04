# 기업 맞춤 포트폴리오 생성기

지원 기업명을 입력하면 인재상·지원자격·우대사항·브랜드 디자인을 조사하고, 지원자의 Notion 프로필 경험을 그에 맞춰 재구성한 포트폴리오 PPTX와 표준 양식 이력서 PDF를 만든다.

**사용법:**
- `/company-portfolio <기업명> [직무] [채용공고 URL]` — 덱. 절차는 `.claude/skills/company-portfolio/SKILL.md`.
- `/company-resume [기업명] [직무] [채용공고 URL]` — 이력서(기업명 없으면 범용 `companies/general/`). 절차는 `.claude/skills/company-resume/SKILL.md`.

## 구조

```
profile/sources.json           자료 위치 (Notion 프로필·팀 Notion URL, GitHub 조직·커밋 이메일)
profile/notion_profile.md      Notion에서 내보낸 지원자 프로필 (사실 출처)
profile/supplements.md         Notion 밖에서 사용자에게 직접 받은 사실 (사실 출처, 기업 간 재사용)
profile/personal.json, photo.* 이력서 인적사항·증명사진 (scripts/personal.py로만 입력, 개인정보)
profile/team_notion.md         팀 Notion (참고 자료 — 팀 성과로만 표기)
profile/github/                팀 저장소·위키 클론 + index.md (참고 자료 — 본인 커밋만 본인 기여)
profile/assets/<출처>/          Notion 이미지 + index.md (위치·캡션)
companies/<slug>/              기업별 작업물
  research.md                  인재상·채용공고 조사 (company-researcher)
  brand.json                   컬러·폰트·스타일 토큰 (brand-researcher)
  mapping.md                   경험 ↔ 인재상/자격 매칭 분석
  deck.json                    슬라이드 내용
  resume.json                  이력서 내용 (인적사항 제외)
  review/                      면접관 리뷰 (posting.md, reviewer-<n>.md, loop.md, resume-<n>.md, resume-loop.md)
  assets/                      덱에 쓰는 이미지
companies/_sample/             렌더러 예시 (스키마 참고용)
output/<slug>_portfolio.pptx   결과물
output/<slug>_resume.pdf       이력서 결과물 (개인정보 포함)
output/preview/<name>/         검수용 PNG
scripts/notion_export.py       공개 Notion 페이지 → Markdown (DB·하위 페이지·이미지 포함)
scripts/github_export.py       GitHub 저장소·위키 클론, 내 커밋·문서·이미지 목록
scripts/check_facts.py         deck.json·resume.json(--file) 수치 ↔ 사실 출처 대조 (빌드 전 필수)
scripts/build_deck.js          brand.json + deck.json → PPTX (pptxgenjs)
scripts/personal.py            이력서 인적사항·사진 입력 → profile/personal.json
scripts/build_resume.js        resume.json + personal.json → PDF (Chrome 헤드리스)
scripts/pdf2png.swift          PDF → PNG (macOS PDFKit, preview.sh가 scripts/.bin/에 컴파일)
scripts/preview.sh             PPTX/PDF → PNG
```

## 규칙

- 지원자 경험·수치는 `profile/notion_profile.md`·`profile/supplements.md`에 있는 것만 쓴다. 과장·창작 금지, 팀 성과는 팀 성과로 표기. 빌드 전에 `check_facts.py`를 통과시킨다.
- 팀 Notion·GitHub는 참고 자료다. 본인 기여는 사실 출처 또는 본인 커밋(`git log --author`)으로만 주장하고, 팀 문서·팀 수치는 팀 성과로 표기한다. 원본 서류 이미지 등 개인정보가 담긴 이미지는 쓰지 않는다.
- 덱 품질은 `portfolio-reviewer`, 이력서 품질은 `resume-reviewer`(PNG + 채용공고만 보는 블라인드 심사관)로 검증한다. 리뷰어에게 작성 의도나 매칭 분석을 넘기지 않는다.
- 인적사항(사진·생년월일·주소·연락처)은 `profile/personal.json`·`profile/photo.*`에만 둔다. resume.json·supplements.md·커밋·PR·공개 저장소에 쓰지 않는다. 공개 저장소에는 입력·렌더 코드만 올린다.
- 덱 디자인 변경은 `brand.json`(토큰)과 `deck.json`(내용)으로 해결하고, 새 레이아웃이 꼭 필요할 때만 `build_deck.js`에 slide 타입을 추가한다 (추가 시 `reference/schemas.md`도 갱신).
- 브랜드 폰트는 자동 설치하지 않는다. 미설치 시 빌드가 fallback으로 대체하므로 사용자에게 설치를 안내한다.
- Keynote 첫 실행은 느리다 — preview.sh에 충분한 timeout(600s)을 준다.
