---
name: company-resume
description: 지원 기업명(+직무)을 받아 인재상·지원자격·우대사항을 조사하고, Notion 프로필 경험을 그 기준에 맞춰 골라 범용 표준 양식(사진·인적사항 표 + 학력·교육·활동·자격·기술 표 + 프로젝트 경험) 이력서 PDF를 만든다. 기업명 없이 부르면 범용 이력서. "OO 이력서 만들어줘", "/company-resume 토스 백엔드" 같은 요청에 사용.
argument-hint: [기업명] [직무] [채용공고 URL]
---

# 기업 맞춤 이력서 PDF 생성

입력: `$ARGUMENTS` — 기업명(선택, 없으면 범용 이력서), 직무(선택, 기본값은 프로필의 `Backend Engineer`), 채용공고 URL(선택).

모든 경로는 프로젝트 루트 기준이다. `<slug>` 규칙은 company-portfolio와 같다(`.claude/skills/company-portfolio/SKILL.md`). 기업명이 없으면 `<slug>` = `general`.
스키마: `reference/resume-schema.md`.

## 0. 준비

1. **자료와 사실 출처**: company-portfolio 0단계(자료 갱신 · 사실 출처 읽기 · 참고 자료 규칙)를 그대로 따른다. 사실 출처(`profile/notion_profile.md`, `profile/supplements.md`)에 없는 경험·수치·기술은 쓰지 않는다.
2. **인적사항**: `python3 scripts/personal.py check`. 미입력 항목이 있으면 사용자에게 **한 번에** 묻는다(성명·영문 성명·생년월일·휴대폰·이메일·주소·증명사진 파일 경로·링크). 받은 값은
   `python3 scripts/personal.py set --birth … --phone … --email … --address … --photo <경로> [--link GitHub=…]`로 저장한다.
   - 인적사항은 `profile/personal.json`·`profile/photo.*`에만 둔다(gitignore). resume.json·supplements.md·커밋·PR에 적지 않는다.
   - 사용자가 터미널에서 직접 넣고 싶어 하면 `python3 scripts/personal.py`(대화형)를 안내한다.
3. `companies/<slug>/` 디렉터리를 만든다.

## 1. 기업 조사 (기업명이 있을 때만)

`companies/<slug>/research.md`가 30일 이내면 재사용한다(포트폴리오를 먼저 만든 기업은 이미 있다). 없으면 `company-researcher` 서브에이전트로 만든다 — 프롬프트에 기업명, 직무, 채용공고 URL(있으면), 출력 경로를 넣는다. 이력서는 브랜드 디자인을 쓰지 않으므로 `brand-researcher`는 부르지 않는다.

## 2. 매칭 분석 + 보충 질문

- 기업명이 있으면: `mapping.md`가 research.md보다 새것이면 재사용, 아니면 company-portfolio 2단계대로 만든다. 이어서 company-portfolio **2-B(보충 질문 → supplements.md)**를 그대로 따른다.
- 범용(`general`)이면: 매칭 분석 없이, 직무(기본 Backend Engineer)에 가까운 경험을 앞에 둔다. 2-B는 이력서 bullet에 넣을 성과의 빈 곳(전후 수치·측정 조건)에만 적용한다.
- 0단계의 인적사항 질문과 2-B 질문이 둘 다 있으면 **한 메시지로 합쳐** 묻는다.

## 3. 이력서 구성 → `companies/<slug>/resume.json`

`reference/resume-schema.md`의 "표준 양식 순서와 분량"대로 쓴다: 핵심 역량(3줄) → 학력 → (병역) → (경력) → 교육 → 자격 → 보유기술 → 대외활동·수상 → (새 쪽) 프로젝트 경험. 확인 문구·날짜는 렌더러가 붙인다.

작성 규칙:
- **표 항목(학력·병역·교육·활동·자격)**: 사실 출처에 있는 것만, 최근 것부터. 출처에 없는 값(자격 취득일, 병역 등)은 0단계·2-B 질문에 넣어 받고 supplements.md에 적는다. 끝내 모르는 값은 빈칸으로 두지 말고 그 열이나 행을 뺀다.
- **핵심 역량**: 1쪽 인적사항 아래 3줄. 프로젝트 bullet 중 가장 강한 성과를 기업 어휘로 요약한다(새 사실 금지).
- **보유기술**: 4~7 그룹. 기업 기술 스택(research.md)과 겹치는 기술을 각 그룹 앞에. 프로젝트 bullet에서 쓴 근거가 보이는 기술만.
- **프로젝트 경험**: 2~3개, 기업 관련도 순. 프로젝트마다 `period`·`team`(인원과 구성)·`role`을 반드시 쓴다.
  - bullet은 **"무엇을 했나 — 어떻게 → 결과(수치)"** 한 문장. 가장 강한 성과를 첫 bullet에, 핵심 어구와 수치를 `**굵게**`.
  - **이력서는 요약이다**: 프로젝트마다 bullet 2~3개(주력도 4개 이하), 한 bullet 1~2줄. 원인 분석·대안 비교·측정 맥락 같은 상세는 포트폴리오에 두고 이력서에 덕지덕지 붙이지 않는다. 같은 기업 포트폴리오를 함께 내면 이력서 bullet은 포트폴리오 슬라이드 제목 수준으로 줄인다.
  - "구현", "적용"으로만 끝나는 bullet은 결과나 이유를 붙이거나 뺀다.
  - 역할 줄(`role`)에는 사실 출처의 담당 영역을 모두 남긴다 — 관련 업무를 bullet로 앞세우더라도 기여 범위를 줄이지 않는다.
  - 러닝 포인트 절(`text`, 3~4줄)은 공고가 러닝 포인트·배운 점을 요구할 때만 넣는다. 사실 출처에 있는 교훈만, 어느 프로젝트의 것인지 괄호로 붙인다.
  - 팀 성과는 `(팀 검색 평가 R@5 0.894)`처럼 팀 성과로 표기한다. 기업 어휘(research.md)를 bullet에 자연스럽게 쓴다. 인재상 태그를 붙이지는 않는다(이력서는 덱보다 짧다).
- 사실 출처의 수치를 계산한 값은 deck.json과 같이 최상위 `derived`에 근거를 적는다.
- 분량: 1쪽 = 인적사항~대외활동, 새 쪽부터 프로젝트. 쪽 수 제한은 없다(3쪽도 괜찮다). 억지로 줄이지 말고, 한두 줄만 넘어간 쪽·빈 공간만 정리한다.

## 4. 빌드

```bash
python3 scripts/check_facts.py companies/<slug> --file resume.json
node scripts/build_resume.js companies/<slug>        # 제출용 PDF
node scripts/build_resume_docx.js companies/<slug>   # 편집용 Word(.docx)
```

- `check_facts.py`가 `출처에 없음`을 내면 빌드하지 않는다(company-portfolio 4단계와 같은 규칙).
- 인적사항 미입력으로 멈추면 0단계로 돌아간다. 사용자가 빈칸 초안을 원할 때만 `--allow-missing`.
- 렌더러는 Chrome(또는 Chromium·Edge) 헤드리스로 인쇄한다. 없으면 설치를 안내한다.
- 출력: `output/<slug>_resume.pdf`와 `output/<slug>_resume.docx` (개인정보 포함 — output/은 gitignore). 같은 resume.json에서 같은 양식으로 그린다. Word본은 표·글머리표·링크가 실제 요소라 Word·한컴오피스·Pages·Google Docs에서 고칠 수 있다(글꼴 한글 맑은 고딕·영문 Arial, `style.font`·`style.latinFont`로 바꿈). 사용자가 Word본을 직접 고쳤다면 그 파일이 최신이므로 다시 빌드해 덮어쓰기 전에 묻는다. 몇 쪽인지 출력한다(`meta.maxPages`를 지정했을 때만 넘으면 경고).

## 5. 시각 검수

```bash
bash scripts/preview.sh output/<slug>_resume.pdf
```

`output/preview/<slug>_resume/page.*.png`를 모두 Read로 확인한다: 쪽 수(넘쳐서 한두 줄만 다음 쪽으로 간 곳), 1쪽 아래 빈 공간 과다, 표 칸 안 어색한 줄바꿈, 빈칸, 사진 잘림.
한두 줄만 다음 쪽으로 넘어갔으면 문장을 다듬어 정리한다. 쪽 수를 맞추려고 내용을 빼지는 않는다. 최대 3회 반복.
첫 실행은 PDF 변환기 컴파일에 2~3분 걸린다 — timeout을 600s로 준다.

## 6. 서류 심사관 리뷰 루프 (최대 3회)

company-portfolio 6단계와 같은 절차를 따르되 아래만 다르다:
- 리뷰어: `resume-reviewer` 서브에이전트. 프롬프트에는 **PNG 폴더 절대 경로와 posting.md 절대 경로만** 넣는다. 범용이면 posting.md 대신 `공고 없음 — <직무> 신입`. (에이전트 타입이 아직 로드되지 않았으면 general-purpose에 `.claude/agents/resume-reviewer.md`를 읽고 따르라고 하고, 같은 입력만 준다.)
- 파일: `companies/<slug>/review/posting.md`(포트폴리오와 공유, 없으면 company-portfolio 6단계대로 만든다), `review/resume-<회차>.md`, 거절 목록은 `review/resume-loop.md`.
- 인용 확인: `python3 scripts/check_facts.py companies/<slug> --file resume.json --find "<인용>"`. 인적사항 표·확인 문구 속 글자는 resume.json에 없으니 PNG로 확인한다.
- 다시 만들기: 4(check_facts → build) → 5(preview).
- 리뷰어가 인적사항(사진·생년월일·주소)을 빼라고 하면 거절 목록에 넣는다 — 사용자가 넣기로 정한 항목이다.

## 7. 보고

- 출력 파일 경로와 쪽 수
- 기업 맞춤으로 바꾼 것 (프로젝트·bullet 순서, 앞으로 뺀 기술) — 범용이면 생략
- 지원자격·우대사항 중 이력서에 근거가 없는 항목 (mapping.md의 미충족)
- 리뷰: 회차별 총점(/35), 마지막 한 줄 판단, 남은 지적(거절 포함), 면접에서 물어볼 질문
- 이번에 supplements.md에 새로 쌓인 사실
- 개인정보가 담긴 파일(`output/<slug>_resume.pdf`, `profile/personal.json`)은 저장소에 올라가지 않는다는 점
