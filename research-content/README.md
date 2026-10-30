# 개인연구(Individual Research) 관리 가이드

개인연구는 **Pages CMS의 "Research (개인 연구)" 항목**에서 등록하고 수정합니다. `index.html`이나 `members.json`을 손댈 필요가 없습니다.

**연구 하나를 한 번만 입력하면 세 곳에 나옵니다.**

| 화면 | 무엇이 나오나 |
|---|---|
| 연구 그룹 페이지의 연구 카드 | 고른 **연구 그룹**의 Research 탭에 카드가 생깁니다 |
| 연구 상세 페이지 | 카드를 누르면 열리는 페이지. 연구배경·연구목표·Keywords·Tools·연구자·관련 논문 |
| 멤버 개인 프로필의 Research 목록 | **연구자**로 고른 사람마다 자동으로 올라갑니다 |

데이터는 `research-content/research.json` 한 파일에만 있습니다. 연구 그룹을 바꾸면 카드가 그 그룹 페이지로 옮겨 가고, 진행 완료를 체크하면 카드가 회색으로 바뀌어 목록 뒤로 갑니다. 연구자를 추가하면 그 사람 프로필에 바로 뜹니다.

## 입력 항목

| 항목 | 필수 | 설명 |
|---|---|---|
| 페이지 주소 (`id`) | 예 | `research-`로 시작, 영문 소문자·숫자·하이픈만. 예: `research-cascade-hp`. **한 번 정하면 바꾸지 마세요.** 논문의 "관련 연구 주제" 연결과 외부 링크가 끊어집니다 |
| 제목 / 영문 제목 | 예 | 상세 페이지와 개인 프로필에 표시 |
| 카드용 짧은 제목 (한/영) | 아니오 | 그룹 페이지 카드에만 쓰는 짧은 제목. 비우면 제목이 그대로 쓰임 |
| 연구 그룹 | 예 | Building Energy Systems / Building Data Analytics & AI / Urban Building Energy Modeling (UBEM). 이 그룹의 Research 페이지에 카드가 생김 |
| 진행 완료 | 아니오 | 체크하면 카드가 회색이 되고 목록 뒤로 감 |
| 기간 표시 (한/영) | 아니오 | 예: `진행 중 · 2025–` / `In Progress, 2025–`, `진행 완료 · 2024–2025` / `Completed, 2024–2025` |
| 연구자 | 아니오 | 구성원 명단에서 고름. 이름·사진·직위는 `members.json`에서 자동으로 가져옴 |
| 카드 요약 (한/영) | 아니오 | 카드에 보이는 한두 문장 |
| 카드 태그 | 아니오 | 3개 안팎. 개인 프로필에는 `#태그` 형태로 표시 |
| 연구배경 / 연구목표 (한/영) | 아니오 | 문단을 나누려면 빈 줄을 한 줄 넣음 |
| Keywords, Tools | 아니오 | 상세 페이지에 표시 |
| 대표 그림 | 아니오 | `Photos/research-figs/`에 올라감. **파일명은 영문으로** |

### 한글과 영어는 짝으로

한글 항목을 입력하면 짝이 되는 영문 항목도 넣어야 합니다. 한글을 고쳤는데 영문을 그대로 두면 배포가 막힙니다. 짝은 제목·카드용 짧은 제목·기간 표시·카드 요약·연구배경·연구목표입니다.

## 새 연구를 만들면

1. CMS에서 Research 항목에 추가하고 저장합니다.
2. 1~2분 뒤 자동화가 `.pages.yml`의 "관련 연구 주제" 목록에 이 연구를 추가합니다. 그 뒤 논문 입력에서 이 연구를 고를 수 있습니다.
3. 논문에서 이 연구를 고르면 상세 페이지의 "관련 논문"에 자동으로 나옵니다. 연구 쪽에는 논문을 적지 않습니다.

## 동작 원리 (참고)

- `js/app.js`의 `loadResearch()`가 `research.json`과 `members.json`을 읽습니다.
- 그룹 페이지의 `<div class="project-grid" data-research-grid="main|data-analysis|urban-modeling">` 안에 카드를 그립니다. 진행 중이 앞, 진행 완료가 뒤이고, 같은 상태 안에서는 `research.json`의 순서(CMS 목록 순서)를 따릅니다.
- `#page-<id>` 요소가 있으면 그 안을, 없으면 새로 만들어 상세 페이지를 그립니다.
- 개인 프로필은 `researchers`에 자기 slug가 있는 연구를 모아 Research 목록을 만듭니다.
- 관련 논문은 상세 페이지의 `<div data-research="<id>">` 칸에 `publications/*.json`에서 채워집니다.

### 데이터 구조

```json
{
  "id": "research-elevator",
  "title": "엘리베이터 샤프트 내 균일 냉각을 위한 급배기 위치 최적화",
  "titleEn": "Optimization of Supply and Exhaust Locations for Uniform Cooling in Elevator Shafts",
  "cardTitle": "엘리베이터 샤프트 냉각 시스템을 통한 연돌효과 저감 연구",
  "cardTitleEn": "A Study on Stack Effect Mitigation Using an Elevator Shaft Cooling System",
  "group": "Building Energy Systems",
  "status": "진행 중 · 2025–",
  "statusEn": "In Progress, 2025–",
  "completed": false,
  "researchers": ["junghyun"],
  "summary": "고층 건물에서 발생하는 연돌효과의 영향을 줄이고 …",
  "summaryEn": "Reduces the impact of the stack effect in high-rise buildings …",
  "tags": ["Stack Effect", "EnergyPlus", "Shaft Cooling"],
  "background": "…",
  "backgroundEn": "…",
  "goal": "…",
  "goalEn": "…",
  "keywords": ["Stack Effect", "Elevator Shaft Cooling"],
  "tools": ["EnergyPlus", "CONTAM"],
  "figure": "Photos/research-figs/elevator.png"
}
```

`researchers`는 slug 배열입니다. slug는 `members.json`의 구성원 slug와 같습니다.
