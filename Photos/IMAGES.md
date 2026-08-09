# 이미지 관리 가이드 (Photos/)

이 사이트는 빌드 과정이 없는 정적 `index.html`입니다. 이미지는 두 곳에서 관리합니다.

- **`Photos/`** 사이트 고정 이미지(로고, 배경, 연구, 멤버). 아래 폴더 구조를 따릅니다.
- **`News_Blog_JPG/`** 뉴스와 블로그 행사 사진. Pages CMS로 올립니다. [News와 Blog 가이드](../News_Blog_JPG/README.md) 참고.

## 사진 용량은 신경 쓰지 않아도 됩니다

저장소에 사진이 올라오면 **자동으로 줄어듭니다.** 휴대폰 원본을 그대로 넣어도 됩니다.

용도별로 다르게 처리합니다. 표시 크기의 2배(레티나)까지만 줄이므로 화질 손실이 보이지 않습니다.

| 폴더 | 처리 | 이유 |
|---|---|---|
| `backgrounds/` | JPEG, 긴 쪽 2560px | 화면 전체를 채움 |
| `research/` | JPEG, 1800px | 본문 표시 폭 약 800px |
| `research-figs/` | **PNG 유지**, 1800px | 작은 글자가 JPEG로 바뀌면 번짐 |
| `projects/` | **PNG 유지**, 1200px | 도표 |
| `members/` | JPEG, 600px | 화면 표시 88~200px |
| `brand/` | 손대지 않음 | 로고. 투명 배경 필요 |
| `News_Blog_JPG/` | JPEG, 2000px | 카드 350px, 확대 최대 1800px |

투명 배경을 실제로 쓰는 그림은 PNG로 남습니다. 알파 채널이 있어도 전부 불투명하면 사진으로 보고 JPEG로 바꿉니다.

이미 충분히 작은 파일은 건드리지 않습니다. 설정은 `.github/workflows/optimize-images.yml`입니다.

> 자동 처리는 저장소에 들어온 **뒤에** 작동합니다. 원본은 git 이력에 한 번 기록되고 지워지지 않습니다. 저장소 용량까지 아끼려면 올리기 전에 줄이는 편이 낫지만 필수는 아닙니다.

## 핵심 규칙

1. **파일명은 ASCII 소문자와 하이픈.** 한글, 공백, 특수문자 금지. 한글 파일명은 NFD와 NFC 차이로 GitHub Pages에서 조용히 404가 납니다. 실제로 두 번 겪었습니다.
2. **교체는 같은 이름으로 덮어쓰기.** 파일명을 그대로 두고 내용만 바꾸면 HTML을 건드릴 필요가 없습니다.
3. **확장자가 바뀌면 참조도 바뀝니다.** 자동 최적화가 PNG를 JPEG로 바꾸면 `index.html`과 `members.json`의 경로도 함께 고쳐 줍니다. 손으로 맞출 필요 없습니다.
4. **멤버 파일명은 슬러그와 같습니다.** `members/<slug>.<ext>`의 `<slug>`가 `showPage('member-<slug>')`의 그 슬러그입니다.

## 폴더 구조

```
Photos/
  brand/         logo.png                        로고 (파비콘, 네비, 푸터 공용)
  backgrounds/   home-1.jpg ~ home-4.jpg          메인 히어로 슬라이드
                 about-1.jpg ~ about-4.jpg        Introduce 페이지 슬라이드
  research/      data.webp    data-wide.jpg       Building Data Analytics & AI
                 systems.webp systems-wide.jpg    Building Energy Systems
                 urban.webp   urban-wide.jpg      Urban Building Energy Modeling
                                                  (.webp = 카드, -wide.jpg = 상세 배너)
  research-figs/ <이름>.png                        연구 상세 페이지의 도표
  projects/      <key>-1.png <key>-2.png …        프로젝트 갤러리 (연속 번호, 자동 표시)
  members/       professor.jpg                    교수님
                 <slug>.jpg                       프로필 사진
  _archive/                                       미사용 보관
```

### 멤버 슬러그

| 이름 | slug | 파일 |
|---|---|---|
| 이도연 | doyeon | `members/doyeon.jpg` |
| 김인섭 | inseob | `members/inseob.jpg` |
| 김지영 | jiyoung | `members/jiyoung.jpg` |
| 이상민 | sangmin | `members/sangmin.jpg` |
| 조정현 | junghyun | `members/junghyun.jpg` |
| 백재욱 | jaeuk | `members/jaeuk.jpg` |
| 한지웅 | jiung | `members/jiung.png` |
| 황정윤 | jungyun | `members/jungyun.jpg` |
| 임지수 | jisu | `members/jisu.jpg` |
| 이현수 | hyunsu | `members/hyunsu.jpg` |
| 김세연 | seyeon | `members/seyeon.jpg` (**파일 없음**) |
| 송준호 | junho | `members/junho.jpg` (**파일 없음**) |
| 이경재 (졸업) | kyungjae | `members/kyungjae.jpg` |
| 임현우 (교수) | professor | `members/professor.jpg` |

사진이 없으면 회색 원으로 대체 표시됩니다. 김세연과 송준호 사진을 넣으면 바로 반영됩니다.

`<slug>-sm.jpg` 파일이 남아 있는데 **어디에서도 쓰지 않습니다.** 예전 캐리커처이며 실제 사진으로 교체했습니다.

## 자주 하는 작업

### 멤버 사진 바꾸기

`Photos/members/<slug>.jpg`를 같은 이름으로 덮어쓰면 됩니다. HTML 수정이 필요 없습니다.

### 새 멤버 추가하기

1. 사진을 `members/<새slug>.jpg`로 저장
2. `members.json`의 `researchers`에 추가하고, 프로필을 만들려면 `profiles`에도 추가
3. `index.html`에 `<div id="page-member-<새slug>" class="page-view"></div>` 빈 껍데기 추가

논문은 따로 적지 않습니다. Publications에서 제1저자로 잡히면 자동으로 프로필에 나옵니다. CMS 드롭다운의 구성원 명단도 자동으로 갱신됩니다. [Publications 가이드](../publications/README.md) 참고.

### 연구 대표 이미지 바꾸기

- 카드용: `research/<topic>.webp`
- 상세 배너: `research/<topic>-wide.jpg`
- `topic`은 `data`, `systems`, `urban` 중 하나

### 배경 슬라이드 바꾸기

`backgrounds/home-1.jpg` ~ `home-4.jpg`를 덮어쓰면 됩니다. Introduce 페이지는 `about-1.jpg` ~ `about-4.jpg`입니다.

### 연구 도표 넣기

`research-figs/<이름>.png`로 저장하고 `research-content/research.json`의 `figure`에 경로를 적습니다. 도표는 PNG로 유지되므로 글자가 번지지 않습니다. 경로가 404면 자동으로 숨겨집니다.

### 프로젝트 갤러리에 사진 추가하기

`projects/<key>-1.png`, `<key>-2.png` 처럼 **1부터 연속 번호**로 저장합니다. 중간 번호가 비면 거기서 멈춥니다. 확장자는 `.jpg`, `.png`, `.jpeg`, `.webp`를 자동 인식합니다.

프로젝트별 `<key>`는 DataNet이 `datanet`, 그린리모델링이 `green`, LH 지열 모니터링이 `lh`, 탄소중립 도시 시뮬레이션이 `carbon`입니다.

사진이 하나도 없으면 그 갤러리 영역은 자동으로 숨겨집니다.

---

관련 가이드: [News와 Blog](../News_Blog_JPG/README.md), [Publications](../publications/README.md), [연구 상세 페이지](../research-content/README.md)
