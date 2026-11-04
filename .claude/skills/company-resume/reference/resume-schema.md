# 이력서 데이터 스키마

## profile/personal.json — 인적사항 (gitignore, 기업 간 공용)

`python3 scripts/personal.py`로만 만든다 (직접 편집해도 되지만 형식 검사를 거치지 않는다).

```json
{
  "name": "홍길동",
  "nameEn": "Hong Gildong",
  "birth": "2000-01-01",            // YYYY-MM-DD, 이력서에는 2000.01.01
  "phone": "010-1234-5678",
  "email": "me@example.com",
  "address": "서울특별시 …",
  "photo": "profile/photo.jpg",      // 증명사진 3:4, 이력서에 30×40mm로 들어간다
  "links": [{ "label": "GitHub", "url": "https://github.com/me" }]   // 인적사항 표 아래 행으로 하나씩
}
```

필수: `name`, `birth`, `phone`, `email`, `address`, `photo`. 하나라도 없으면 빌드가 멈춘다(`--allow-missing`이면 빈칸으로 초안).

## companies/<slug>/resume.json — 이력서 내용

인적사항은 넣지 않는다. 렌더러가 `profile/personal.json`에서 채운다.

```json
{
  "meta": {
    "role": "Backend Engineer",     // 인적사항 표의 "지원분야"
    "company": "토스",              // 기록용 (렌더하지 않음), 범용 이력서는 null
    "maxPages": 3,                  // 선택 — 지정하면 넘을 때 빌드가 경고 (기본: 제한 없음)
    "title": "이력서",              // 선택, 기본 "이력서"
    "date": "2026년 11월 4일",      // 선택, 확인 문구 날짜 (기본: 빌드한 날)
    "declaration": true             // 선택, false면 "위의 기재 사항은 …" 확인 문구를 뺀다,
    "info": [{ "label": "근무 가능", "value": "2027.01.04 ~ 02.26" }]   // 선택, 공고가 요구하는 조건을 인적사항 표에 행으로 (주소 아래)
  },
  "style": { "font": "Pretendard", "latinFont": "Arial", "accent": "#2B2B2B" },   // 선택. PDF 기본 폰트 Pretendard → Nanum Gothic → Apple SD Gothic Neo, Word본 기본 한글 맑은 고딕·영문 Arial
  "sections": [ /* 아래 타입, 위에서부터 순서대로 */ ],
  "derived": [{ "value": "42.2", "from": "52.6분 → 30.4분" }]  // 선택, check_facts.py용 (deck.json과 같음)
}
```

모든 섹션 공통: `type`, `title`, `pageBreak?`(true면 이 섹션부터 새 쪽).
글자 안의 `**굵게**`와 `\n`(줄바꿈)이 반영된다.

| type | 필드 | 렌더 |
|---|---|---|
| `table` | `columns[]`, `rows[][]`, `widths?[]`(%), `align?[]`(`c`\|`l`) | 머리글 행이 있는 표. 정렬을 안 주면 24자 넘는 칸이 있는 열만 왼쪽 정렬 |
| `skills` | `groups[{name, items[]}]` | 왼쪽 분야·오른쪽 기술(` · `로 연결) 2열 표 |
| `projects` | `items[{name, summary?, org?, period, team, role?, stack?[], bullets?[], link?}]` | 프로젝트마다 표 하나: 프로젝트명+한 줄 소개(오른쪽에 `org`) / 기간·팀 구성 / 역할 / 기술 / 주요 내용 / 링크 |
| `text` | `body?`(문자열 또는 문단 배열), `items?[]`(bullet) | 테두리 상자 안 문단·bullet. "핵심 역량" 요약(3줄)에 쓴다 |

## 표준 양식 순서와 분량

범용 표준 이력서(인적사항 표 + 항목별 표) 순서를 따른다. 해당 내용이 없는 섹션은 만들지 않는다(빈 표 금지).

| 순서 | 섹션 | type | columns 예시 |
|---|---|---|---|
| — | 인적사항 (자동) | — | 사진·성명·영문·생년월일·지원분야·휴대폰·이메일·주소·링크 |
| 0 | 핵심 역량 | `text`(`items`) | 가장 강한 성과 3줄 — 프로젝트가 뒤쪽이라 1쪽에서 직무 적합성이 보이게 한다 |
| 1 | 학력사항 | `table` | 기간 · 학교명 · 전공 · 구분(졸업/재학/졸업예정) |
| 1-1 | 병역사항 | `table` | 구분(병역필/미필/면제) · 복무기간 · 복무형태 (해당자만, 사실 출처에 있을 때) |
| 2 | 경력사항 | `table` | 기간 · 회사명 · 직위 · 담당업무 (경력이 있을 때만) |
| 3 | 교육사항 | `table` | 기간 · 교육과정 · 내용 |
| 4 | 자격사항·어학 | `table` | 자격명 · 발행처 · 취득일 |
| 5 | 보유기술 | `skills` | 4~7 그룹. 프로젝트에서 쓴 근거가 있는 기술만 |
| 6 | 대외활동·수상 | `table` | 기간 · 활동명 · 내용 — 직무 관련이 낮으면 1쪽 끝에 한 줄씩 |
| 7 | 프로젝트 경험 | `projects` (`pageBreak: true`) | 2~3개, 프로젝트당 bullet 2~6개 |
| — | 확인 문구·날짜·작성자 (자동) | — | |

- 1쪽 = 인적사항 ~ 대외활동, 새 쪽부터 프로젝트 경험. 쪽 수 제한은 없다 — 분량은 내용으로 정하고, 한두 줄만 다음 쪽으로 넘어간 곳·빈 공간 과다만 정리한다.
- 이력서의 프로젝트는 요약이다: 프로젝트마다 bullet 2~3개(주력도 4개 이하), 한 bullet 1~2줄. 원인 분석·대안 비교·수치 맥락 같은 상세는 포트폴리오에 둔다.
- 기간은 `YYYY.MM ~ YYYY.MM`으로 통일하고, 진행 중이면 `YYYY.MM ~ 현재`. 표 행은 최근 것부터.
- 가운뎃점은 글 안에서 띄우지 않는다(`Kubernetes·GitOps`). ` · `(띄움)는 렌더러가 기술 목록을 이을 때만 쓴다.
- 기술 목록(`skills.items`, `projects.stack`)의 한 항목 안에는 `·`를 쓰지 않는다 — 렌더러의 ` · `와 섞여 경계가 흐려진다. 묶음은 괄호와 쉼표로: `AWS(EC2, RDS)`, `PostgreSQL(pgvector)`.
- 실사용자 운영·트래픽은 사실 출처에 근거가 있을 때만 쓴다. dev·스테이징 운영을 운영 경험처럼 쓰지 않는다.
