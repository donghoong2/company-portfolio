# 데이터 스키마

## brand.json

```json
{
  "company": "토스",
  "colors": {
    "primary": "#3182F6",      // 메인 브랜드 컬러 (표지, 강조, 지표 카드)
    "secondary": "#1B64DA",    // 보조 컬러
    "accent": "#F04452",       // 포인트 (우대사항 라벨 등 소량)
    "background": "#FFFFFF",   // 슬라이드 배경
    "surface": "#F2F4F6",      // 카드 배경 (background와 미세하게 구분)
    "text": "#191F28",         // 본문
    "muted": "#8B95A1",        // 캡션/보조 텍스트
    "onPrimary": "#FFFFFF",    // primary 위 글자색 (대비 4.5:1 이상)
    "border": "#E5E8EB"
  },
  "fonts": {
    "heading": "Toss Product Sans",  // fc-list에 나오는 family 이름 그대로
    "body": "Pretendard",
    "fallback": "Apple SD Gothic Neo", // 미설치 시 대체 (macOS 기본 한글 폰트)
    "downloadUrl": "https://...",     // 무료 배포처 (공식만, 없으면 null)
    "note": "Toss Product Sans는 비공개 → 유사한 Pretendard 사용"
  },
  "style": {
    "corner": "rounded",        // rounded | sharp | pill
    "coverStyle": "split",      // split(좌측 컬러 패널) | solid(전면 컬러) | minimal(흰 배경+세로 바)
    "accentShape": "bar",       // bar | dot | none (제목 위 장식)
    "sectionStyle": "solid"     // solid(컬러 배경) | light(surface 배경)
  },
  "logo": null,                 // 사용자가 넣은 경우만: "logo.png" (companies/<slug>/ 기준)
  "tone": "간결하고 친근한 문장, 큰 숫자 강조, 여백 넉넉",
  "sources": ["https://..."]
}
```

색상은 `#` 유무 상관없이 6자리 HEX. JSON에 주석은 넣지 않는다 (위는 설명용).

## deck.json

```json
{
  "meta": { "author": "이동형", "role": "Backend Engineer", "contact": "github.com/donghoong2", "date": "2026.10", "title": "..." },
  "slides": [ /* 아래 타입들 */ ]
}
```

모든 슬라이드 공통(선택): `label`(제목 위 작은 영문 라벨), `title`, `lead`(제목 아래 한 줄 요약), `notes`(발표자 노트).
`cover`, `section`, `closing`은 공통 헤더/푸터가 없는 전면 디자인.

| type | 필드 | 권장 분량 |
|---|---|---|
| `cover` | `headline`, `subhead`, `label?` | headline 2줄 이내 |
| `profile` | `name`, `role`, `intro`, `keywords[]`, `info[{label,value}]`, `competencies[{title,desc}]` | intro 3~4문장, keywords ≤5, competencies 3 |
| `fit` | `items[{value, desc, evidence}]` | 2~4개, evidence 2문장 이내 |
| `requirements` | `rows[{kind:"필수"\|"우대", req, evidence, project}]` | ≤7행 |
| `section` | `no`, `title`, `subtitle`, `tags[]` | |
| `project` | `summary`, `period`, `team`, `role`, `stack[]`, `metrics[{value,label}]`, `contributions[]`, `fitTags[]`, `image?` | metrics ≤3 (value 8자 이내), contributions 3~5 |
| `star` | `context`, `problem`, `action[]`, `result[]`, `fitTag` | 각 열 bullet 2~4개 |
| `architecture` | `layers[{name, items[]}]`, `caption` | layers ≤5, items ≤5 |
| `activities` | `items[{period, name, role, desc, fitTag}]` | ≤5 |
| `skills` | `groups[{name, items[]}]` | 4~6 그룹 |
| `image` | `path`, `caption` | |
| `closing` | `message`, `sub?`, `contacts[]` | |

`image`/`project.image` 경로는 프로젝트 루트 기준 (예: `companies/toss/assets/flow.png`).
