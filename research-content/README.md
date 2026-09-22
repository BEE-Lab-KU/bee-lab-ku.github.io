# 개인연구(Individual Research) 관리 가이드

개인연구 상세 페이지는 더 이상 `index.html`을 직접 고치지 않습니다.
**`research.json` + 그림 폴더**만 수정하면 페이지가 자동 생성됩니다.

## 구조
```
research-content/
  research.json     ← 개인연구 데이터 (이 파일만 수정)
  forms/            ← 멤버가 제출한 Word 개인양식 원본 보관
  README.md         ← (이 문서)
Photos/research-figs/
  <figure>.png      ← 연구별 대표 그림
```

## 새 개인연구 추가 / 수정하기
1. 멤버가 Word 개인양식(`forms/`에 보관)을 작성·제출.
2. `research.json` 배열에 항목을 추가하거나 기존 항목을 수정:
   ```json
   {
     "id": "research-elevator",            // 라우팅 id (showPage('research-elevator'))
     "title": "연구 제목",
     "titleEn": "Research Title",          // 한글 title이 있으면 필수
     "group": "Building Systems",          // 뒤로가기 라벨 (← Building Systems)
     "back": "main",                       // 뒤로 갈 그룹 페이지: main | data-analysis | urban-modeling
     "status": "진행 중 · 2025–",
     "statusEn": "Ongoing · 2025–",        // 한글 status가 있으면 필수
     "completed": false,                   // true면 회색 상태점
     "researchers": [
       { "slug": "junghyun", "name": "조정현", "nameEn": "Junghyun Cho", "role": "Master's Student",
         "avatar": "Photos/members/junghyun.jpg" }
     ],
     "background": "연구 배경 …",
     "backgroundEn": "Research background …", // 한글 background가 있으면 필수
     "goal": "연구 목표 …",
     "goalEn": "Research goal …",         // 한글 goal이 있으면 필수
     "keywords": ["Stack effect", "Stratification"],
     "tools": ["EnergyPlus", "CONTAM"],
     "figure": "Photos/research-figs/elevator.png"  // 그림 없으면 null
   }
   ```
   - `titleEn`: 기존 한글 `title`이 있으면 필수
   - `statusEn`: 기존 한글 `status`가 있으면 필수
   - `backgroundEn`: 기존 한글 `background`가 있으면 필수
   - `goalEn`: 기존 한글 `goal`이 있으면 필수
   - 각 연구자의 `nameEn`: 한글 `name`이 있으면 필수
3. 그림이 있으면 `Photos/research-figs/`에 ASCII 파일명으로 저장하고 `figure` 경로를 적습니다(없으면 `"figure": null`).

> **관련 논문은 여기에 적지 않습니다.** `papers` 필드는 없어졌습니다.
> 논문은 `publications/`에만 두고, CMS의 **관련 연구 주제**에서 이 연구의 `id`를 고르면
> 상세 페이지에 자동으로 표시됩니다. [Publications 가이드](../publications/README.md) 참고.
4. **멤버 프로필 페이지의 연결**: `index.html`의 해당 멤버 카드에서 `showPage('<id>')`와 `<h4>제목</h4>`이 `research.json`의 `id`·`title`과 맞는지만 확인(신규 연구면 멤버 페이지에 `profile-research-item` 한 줄 추가).

## 언어 지원

개인연구 페이지는 한글을 기본으로 합니다. 기존 한글 데이터가 있으면 영어 필드도 함께 있어야 하며, 한글을 수정하면 영어도 함께 수정해야 합니다.

**필수 필드**
- 기존 한글 `title`이 있으면 `titleEn` 필수
- 기존 한글 `status`가 있으면 `statusEn` 필수
- 기존 한글 `background`가 있으면 `backgroundEn` 필수
- 기존 한글 `goal`이 있으면 `goalEn` 필수
- 한글 `name`(연구자)이 있으면 `nameEn` 필수

**입력 방식**: `research.json`을 직접 고쳐서 한글과 영어를 함께 입력합니다. CMS 입력이 아닙니다. 한글 필드를 바꿨는데 영어를 갱신하지 않으면 배포 시 검증 실패입니다.

## 동작 원리
- 페이지 로드 시 `loadResearch()`가 `research.json`을 읽어 각 항목을 `#page-<id>` 상세 페이지로 렌더링합니다.
- `index.html`에 같은 id의 빈 셸(`<div id="page-<id>" class="page-view"></div>`)이 있으면 그 안을 채우고, 없으면 새로 만들어 붙입니다.
- 그림 경로(`figure`)가 404면 자동으로 숨겨집니다.
- 관련 논문은 상세 페이지의 `<div data-research="<id>">` 칸에 `publications/*.json`에서 자동으로 채워집니다.
  `index.html`에 하드코딩된 연구 페이지도 같은 칸을 쓰므로 방식이 동일합니다.
- **새 연구 페이지를 만들면 CMS 드롭다운에 자동으로 나타납니다.** `.pages.yml`을 손댈 필요가 없습니다.
  자동화가 실제 존재하는 `research-*` 페이지 id를 훑어 목록을 다시 만듭니다.

## 현재 이관된 연구(파일럿)
`research-elevator`(조정현) · `research-da-preprocessing`·`research-da-thermal-seat`(김지영·이현수) · `research-um-ubem`(황정윤) ·
`research-whr-dc`·`research-ai`·`research-cascade-hp`(한지웅, 3개).
나머지 기존 개인연구는 아직 `index.html`에 하드코딩돼 있으며, 양식이 들어오는 대로 이 방식으로 점진 이관합니다.

> Word → JSON 변환은 관리자가 수행합니다. 멤버는 양식만 작성하면 됩니다.
