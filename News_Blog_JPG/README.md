# News / Blog 관리 가이드

News와 Blog 글은 **Pages CMS(웹 편집기)** 로 올리는 것을 권장합니다. git이나 JSON을 직접 다룰 필요가 없습니다.

> 논문 등록은 별도 가이드를 보세요. [Publications 관리 가이드](../publications/README.md)

## CMS에 무엇이 있나

Pages CMS 왼쪽 목록은 여섯 개입니다.

- **News**, **Blog**: 이 가이드에서 다룹니다
- **International / Domestic Publications**, **International / Domestic Conferences**: 논문 등록. [Publications 가이드](../publications/README.md) 참고

## 웹에서 올리기 (Pages CMS)

1. <https://app.pagescms.org> 접속 → **GitHub로 로그인**
2. 처음 한 번 `BEE-Lab-KU/bee-lab-ku.github.io` 저장소 **권한 승인**
3. 왼쪽에서 **News** 또는 **Blog** 선택 → **새 항목 추가**
4. 입력:
   - **제목**
   - **날짜**: 선택한 날짜 기준으로 **최신이 자동으로 맨 위**에 표시됩니다
   - **본문** (짧은 글)
   - **사진**: "사진 추가"로 여러 장 등록 (첫 장이 카드 대표 이미지)
     - 각 사진마다 **설명글(선택)** 을 달 수 있어요 → 상세보기에서 해당 사진 아래에 표시됩니다
5. **저장** → 자동으로 저장소에 커밋되고, 1~2분 뒤 사이트에 반영

> 목록에서 항목을 드래그해 순서를 바꿀 수 있지만 **사이트 표시 순서에는 영향이 없습니다.** 화면 순서는 오직 날짜가 결정합니다. 순서를 바꾸고 싶으면 날짜를 고치세요.

## 사진 올릴 때

**그냥 올리셔도 됩니다.** 사진이 저장소에 들어오면 자동으로 줄여 주는 장치가 걸려 있습니다.
휴대폰 원본(4032×3024, 3MB 안팎)을 올리면 2000px, 600KB 정도로 바뀌고 커밋이 하나 더 생깁니다.
화면에 보이는 화질은 그대로입니다. 카드에서 350px, 확대해서 봐도 1800px을 넘지 않기 때문입니다.

동작 방식은 이렇습니다.

- 사진은 JPEG로 바꾸고 긴 쪽 2000px까지 줄입니다
- 투명 배경을 쓰는 그림과 글자가 있는 도표는 PNG 그대로 둡니다
- 이미 충분히 작은 사진은 건드리지 않습니다
- `.png`가 `.jpg`로 바뀌면 `news.json`과 `blog.json`의 경로도 같이 고쳐 줍니다

설정은 `.github/workflows/optimize-images.yml`입니다.

> **한 가지만 기억하세요.** 자동 처리는 저장소에 들어온 뒤에 작동합니다. 원본은 git 이력에 한 번
> 기록되고 지워지지 않습니다. 저장소 용량 자체를 아끼려면 올리기 전에 줄이는 편이 낫습니다.
> macOS는 미리보기에서 도구 > 크기 조절로 긴 쪽을 2000px으로 맞추면 됩니다. 필수는 아닙니다.

사진이 안 줄어든 것 같으면 GitHub 저장소의 **Actions** 탭에서 실행 기록을 확인하세요.
이 장치가 멈춰도 글과 사진은 정상적으로 올라갑니다. 용량만 안 줄어들 뿐입니다.

## 데이터 구조 (참고)

- 글 목록: `beelab_content/news.json`, `beelab_content/blog.json`
  - 각 항목: `{ "title": ..., "date": "YYYY-MM-DD", "body": ..., "images": [{ "src": "경로", "caption": "설명글" }, ...] }`
  - 사이트는 `date` 내림차순(최신 먼저)으로 자동 정렬합니다.
- 사진 파일: `beelab_images/News/...`, `beelab_images/Blog/...`
  - `images` 배열의 경로가 그대로 화면에 사용됩니다 (폴더명 규칙·개수 입력 불필요).

## 직접 편집할 때 주의

CMS 대신 파일을 직접 고칠 경우, `images`의 각 경로는 **실제 파일이 있는 저장소 경로**여야 하며 대소문자까지 정확해야 합니다 (GitHub Pages는 대소문자를 구분).

설정 파일: 저장소 루트의 `.pages.yml`

---

관련 가이드: [Publications](../publications/README.md), [연구 상세 페이지](../research-content/README.md)
