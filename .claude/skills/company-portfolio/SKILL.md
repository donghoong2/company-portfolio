---
name: company-portfolio
description: 지원 기업명(+직무)을 받아 인재상·지원자격·우대사항·브랜드 디자인(색상/폰트/톤)을 조사하고, Notion 프로필의 활동·프로젝트를 그 기준에 맞춰 재구성한 기업 맞춤 포트폴리오 PPTX를 만든다. "OO 기업 포트폴리오 만들어줘", "/company-portfolio 토스 백엔드" 같은 요청에 사용.
argument-hint: <기업명> [직무] [채용공고 URL]
---

# 기업 맞춤 포트폴리오 PPT 생성

입력: `$ARGUMENTS` — 기업명(필수), 직무(선택, 기본값은 프로필의 `Backend Engineer`), 채용공고 URL(선택).

모든 경로는 프로젝트 루트 기준이다.
`<slug>`는 기업명을 소문자 영문 kebab-case로 바꾼 것 (예: 토스 → `toss`, 카카오뱅크 → `kakaobank`). 직무가 기본값과 다르면 `<slug>-<직무>` (예: `naver-data`).

## 0. 준비

1. `profile/notion_profile.md`가 없거나 사용자가 "노션 새로고침/업데이트"를 요청했거나 파일이 7일 이상 지났으면 갱신한다:
   ```bash
   python3 scripts/notion_export.py "https://app.notion.com/p/Lee-Donghyeong-321c46c483db800f9f24c544837f9b9d"
   ```
2. `profile/notion_profile.md` 전체를 읽는다. **이 파일이 지원자에 대한 유일한 사실 출처다.** 여기에 없는 경험·수치·기술은 절대 만들지 않는다.
3. `companies/<slug>/` 디렉터리를 만든다. 이미 `research.md`/`brand.json`이 있으면 재사용할지 사용자에게 묻지 말고, 30일 이내면 재사용·그 이상이면 재조사한다.

## 1. 기업 조사 (병렬 서브에이전트 2개)

한 메시지에서 두 에이전트를 동시에 실행한다:

- `company-researcher` — 인재상·핵심가치, 해당 직무 채용공고의 주요업무/지원자격/우대사항, 기술 스택, 최근 이슈.
  → `companies/<slug>/research.md`
- `brand-researcher` — 브랜드 컬러(HEX), 전용/권장 폰트, 디자인 톤, 레이아웃 성향.
  → `companies/<slug>/brand.json`

프롬프트에 기업명, 직무, 채용공고 URL(있으면), 출력 경로, `<slug>`를 반드시 포함한다.
두 결과 파일이 생성됐는지 확인하고, `brand.json`은 `reference/schemas.md`의 스키마대로인지 검증한다.

## 2. 매칭 분석 → `companies/<slug>/mapping.md`

`research.md`와 `notion_profile.md`를 대조해 아래를 작성한다:

1. **인재상 매핑 표** — 인재상 키워드마다 가장 강한 근거 1~2개 (프로젝트/활동 + 구체 행동 + 수치).
2. **지원자격·우대사항 매핑 표** — 항목마다 `충족 / 부분 충족 / 미충족` + 근거. 미충족은 숨기지 말고 표시하되 PPT에는 넣지 않는다 (사용자에게 보고).
3. **스토리 우선순위** — 이 기업에 가장 어필할 프로젝트 순서와 각 프로젝트에서 강조할 트러블슈팅 1~2개. 기업 기술 스택/도메인과 겹치는 것을 앞으로.
4. **헤드라인 후보 3개** — 기업 인재상 언어 + 지원자의 정체성("약속을 끝까지 책임지는 개발자")을 결합.

원칙:
- 기업이 쓰는 **어휘를 그대로** 쓴다 (예: 토스 "Go for 10x" → 근거에 그 단어를 태그로 붙임).
- 같은 경험이라도 기업에 따라 다른 측면을 강조한다 (예: 금융사 → 정합성·보안·PII 마스킹 / 커머스 → 트래픽·성능 / AI 기업 → RAG·OCR 파이프라인).
- 수치는 notion_profile.md에 있는 것만, 측정 범위(팀 공동 성과 여부 등)를 왜곡하지 않는다.

## 3. 덱 구성 → `companies/<slug>/deck.json`

`reference/schemas.md`의 slide 타입으로 작성한다. 기본 흐름 (12~18장):

1. `cover` — 헤드라인(기업 인재상 + 나의 정체성)
2. `profile` — 소개, 키워드(기업 인재상 어휘), 핵심 역량 3개
3. `fit` — 인재상 × 나의 경험 (인재상 3~4개)
4. `requirements` — 지원자격·우대사항 매칭 표 (충족/부분 충족만, 최대 7행)
5. 프로젝트마다: `section` → `project` → `star` 1~2장 (→ 필요시 `architecture` / `image`)
6. `activities` — 기업과 관련성 높은 순, 최대 5개
7. `skills` — 기업 기술 스택과 겹치는 기술을 각 그룹 앞쪽에
8. `closing` — 기업에 대한 한 문장 포부

작성 규칙:
- 모든 `project`/`star`/`activities` 항목에 `fitTag(s)`로 연결된 인재상 키워드를 붙인다.
- 한 슬라이드 = 한 메시지. 텍스트 박스당 2~4줄, bullet은 3~5개, 문장은 명사형/간결체.
- `cover.headline`, `closing.message`, `section.title`은 의미 단위로 `\n`을 직접 넣어 줄바꿈한다 (한 줄 한글 18자 이내). Keynote는 한글을 글자 단위로 줄바꿈하므로 자동 줄바꿈에 맡기면 단어가 잘린다.
- 각 슬라이드 `notes`에 면접에서 말할 30초 설명을 넣는다.
- 이미지가 필요하면 notion_profile.md의 공개 이미지 URL(raw.githubusercontent.com 등)을 `companies/<slug>/assets/`에 내려받아 `image` 슬라이드나 `project.image`로 쓴다. 내려받은 파일은 이미지인지(`file` 명령) 확인한다.
- 로고는 사용자가 `companies/<slug>/logo.png`를 넣어둔 경우에만 `brand.logo`로 사용한다. 임의로 내려받지 않는다.

## 4. 빌드

```bash
node scripts/build_deck.js companies/<slug>
```

- 폰트 미설치 경고가 나오면 `brand.json`의 `fonts.downloadUrl`을 사용자에게 안내한다 (자동 설치하지 않는다). 설치 후 재빌드하면 브랜드 폰트가 적용된다.
- 출력: `output/<slug>_portfolio.pptx`

## 5. 시각 검수

```bash
bash scripts/preview.sh output/<slug>_portfolio.pptx
```

생성된 `output/preview/<slug>_portfolio/*.png`를 모두 Read로 확인하고 다음을 점검한다:
텍스트 넘침/잘림, 겹침, 대비(배경 대비 글자색), 빈 공간 과다, 브랜드 색 사용이 과하거나 부족한지.
문제가 있으면 `deck.json`(텍스트 줄이기, 항목 수 조정) 또는 `brand.json`(style 변경)을 고쳐 재빌드한다. 최대 3회 반복.
`preview.sh`가 렌더러를 찾지 못하면 그 사실을 보고하고 넘어간다.

## 6. 보고

사용자에게 간결하게 보고한다:
- 출력 파일 경로
- 적용한 브랜드 요소 (색상, 폰트 — 대체된 경우 대체 폰트와 설치 안내)
- 인재상/자격요건 매칭 요약, **미충족 항목**과 보완 제안
- 조사 출처 중 확신도가 낮은 부분 (예: 채용공고를 못 찾아 일반 직무 요건으로 대체)
