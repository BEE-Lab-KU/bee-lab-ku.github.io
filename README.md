# BEE Lab 홈페이지

건국대학교 건축대학 건축환경 및 에너지 연구실(Building Energy & Environment Laboratory) 사이트입니다.
<https://beelab.kr> (= <https://bee-lab-ku.github.io>)

## 무엇을 하려고 오셨나요

| 하려는 일 | 어디로 |
|---|---|
| News, Blog 글 올리기 | [News와 Blog 가이드](News_Blog_JPG/README.md) |
| 논문 등록하기 | [Publications 가이드](publications/README.md) |
| 연구 상세 페이지 만들기 | [연구 페이지 가이드](research-content/README.md) |
| 사진 바꾸기, 새 멤버 사진 | [이미지 가이드](Photos/IMAGES.md) |

글과 논문은 **Pages CMS**(<https://app.pagescms.org>)에서 올립니다. GitHub 계정으로 로그인하면 됩니다. git이나 JSON을 직접 다룰 일이 없습니다.

## 언어 지원: 한글 기본, 영어 함께 관리

사이트는 한국어를 기본으로 하고, 방문자가 화면 오른쪽 상단에서 English로 전환할 수 있습니다. 한 번 선택하면 이후 방문까지 그 언어로 유지됩니다.

**작성 원칙**: 모든 항목은 한글과 영어를 함께 입력합니다. CMS 저장은 사람의 검토와 승인입니다.

**필수 필드**

- **News와 Blog**:
  - `title`(한글) + `titleEn`(영어) 모두 필수
  - `body`(한글)가 있으면 `bodyEn`(영어)도 필수. 예외는 이미지만 있는 Blog 게시물(body/bodyEn 모두 비울 수 있음)
  - `caption`(한글)이 있으면 `captionEn`(영어)도 필수
  - 영어가 모자라면 배포 실패(한글 fallback 게시 없음)

- **논문**:
  - 국제 저널/학회: 영어 `citation` 그대로 유지
  - 국내 저널/학회: 한글 `citation` + 영어 `citationEn` 모두 필수

- **연구 페이지** (`research.json` 직접 입력):
  - 기존 한글 `title`이 있으면 `titleEn` 필수
  - 기존 한글 `status`가 있으면 `statusEn` 필수
  - 기존 한글 `background`가 있으면 `backgroundEn` 필수
  - 기존 한글 `goal`이 있으면 `goalEn` 필수
  - 한글 이름 `name`이 있으면 영어 이름 `nameEn` 필수

**배포**: CMS 저장 또는 JSON 커밋 후 검증이 자동 실행됩니다. 모든 필수 영어 필드가 있어야만 배포됩니다. 한글 원문을 바꾼 뒤 영어를 갱신하지 않아도 검증 실패입니다.

## 사이트 구조

빌드 과정이 없는 정적 사이트입니다. `index.html` 하나에 모든 페이지가 들어 있고, 자바스크립트가 JSON을 읽어 목록을 채웁니다.

```
index.html                        모든 페이지의 뼈대
css/styles.css
js/app.js                         JSON 로딩과 렌더링

publications/                     논문. 종류별 4개 파일
  international.json  domestic.json  int-conf.json  dom-conf.json
members.json                      구성원과 프로필
research-content/research.json    연구 상세 페이지
News_Blog_JPG/beelab_content/     news.json, blog.json
Photos/                           고정 이미지
.pages.yml                        Pages CMS 설정
```

## 논문은 한 곳에만 적습니다

`publications/`의 네 파일이 유일한 출처입니다. 논문 하나를 CMS에 넣으면 세 화면에 자동으로 나타납니다.

| 화면 | 기준 |
|---|---|
| Publications 탭 | 전부 |
| 멤버 개인 프로필 | 그 사람이 **제1저자**인 논문 |
| 연구 상세 페이지 | 그 연구 주제로 태그한 논문 |

프로필이나 연구 페이지에 논문을 따로 적지 않습니다.

## 자동으로 도는 것

손댈 필요 없이 배경에서 동작합니다. 결과는 GitHub 저장소의 **Actions** 탭에서 볼 수 있습니다.

**언어 검증** (`.github/scripts/validate_translations.py`)
CMS 저장 또는 JSON 커밋 후 자동 실행됩니다. 모든 필수 언어 필드가 있는지 확인합니다.
- 검증 기준: News/Blog `titleEn` 필수, 한글 body 있으면 `bodyEn` 필수, 한글 caption 있으면 `captionEn` 필수. 국내 저널/학회 `citationEn` 필수. 연구 JSON의 한글 필드 변경 시 대응 `*En` 필드도 필수.
- 실패 시: 기존 배포가 그대로 유지되고, Actions 탭 로그에서 어느 항목이 문제인지 확인한 뒤 수정합니다. 한글 원문을 바꿨는데 영어를 갱신하지 않았다면 영어도 함께 수정해야 합니다.

**배포** (`.github/workflows/deploy-pages.yml`)
검증 성공 후 공개 사이트에 필요한 HTML, CSS, JavaScript, JSON, 이미지만 모아 배포합니다. 관리 설정과 자동화 스크립트는 공개 파일에 포함하지 않습니다. 사진 최적화나 논문 태그 동기화가 새 커밋을 만들면 그 작업이 끝난 뒤 최신 커밋을 다시 배포합니다.

**사진 최적화** (`.github/workflows/optimize-images.yml`)
사진이 올라오면 용도에 맞게 줄입니다. 휴대폰 원본을 그냥 올려도 됩니다. 확장자가 바뀌면 참조 경로도 함께 고칩니다.

**논문 태그와 CMS 목록 동기화** (`.github/workflows/sync-publications.yml`)
논문의 저자를 자동으로 채우고, CMS 드롭다운의 구성원 명단과 연구 주제 목록을 실제 데이터에서 다시 만듭니다. 학생이 들어오면 `members.json`에만 추가하면 됩니다.

저자 판별은 이름 전체가 확인될 때만 합니다. 이니셜만으로는 `Lim, J.`가 누구인지 알 수 없어서, 국문은 한글 이름으로 영문은 Crossref의 저자 이름 전체로 대조합니다. **CMS에서 사람이 고른 값은 절대 덮어쓰지 않습니다.**

이 세 가지가 모두 멈춰도 사이트는 정상입니다. 자동 보완과 최적화만 안 될 뿐입니다.

## 알아두면 좋은 것

**파일명에 한글을 쓰지 마세요.** NFD와 NFC 차이로 GitHub Pages에서 조용히 404가 납니다. 실제로 두 번 겪었습니다.

**DOI는 `https://doi.org/10....` 형태로 넣으세요.** 저널 사이트 주소를 넣으면 외부 접속이 막혀 링크가 열리지 않습니다.

**`.pages.yml` 맨 위의 `_lab_members`와 `_research_pages`는 자동 생성됩니다.** 손으로 고쳐도 다음 실행 때 덮어써집니다. 명단을 바꾸려면 `members.json`을 고치세요.

**Actions 탭에서 실패를 확인하고 고치는 방법**

1. GitHub 저장소 → **Actions** 탭 → 빨간색 X 표시된 실행(run) 클릭
2. 실패한 작업 → 로그에서 어느 항목이 문제인지 확인. 예: "titleEn 필드가 없습니다", "한글 body 있는데 bodyEn이 없습니다"
3. Pages CMS로 돌아가 해당 항목을 수정 후 저장하거나, JSON을 고쳐 커밋
4. 자동으로 다시 실행되어 성공하면 배포 완료

**번역 자동화 없음**: 한글을 쓰면 자동으로 영어로 번역되지 않습니다. 한글과 영어를 직접 입력해야 합니다. 번역 API나 외부 유료 서비스는 쓰지 않으며, CMS 저장이 사람의 검토와 승인입니다.

**되돌리기는 git으로 합니다.** 별도 백업 폴더를 두지 않습니다. 지운 파일도 커밋 해시로 꺼낼 수 있습니다.

```
git show <커밋>:<경로> > 복구본
```
