# News / Blog 관리 가이드

News·Blog 글은 **Pages CMS(웹 편집기)** 로 올리는 것을 권장합니다. git이나 JSON을 직접 다룰 필요가 없습니다.

## 웹에서 올리기 (Pages CMS)

1. <https://app.pagescms.org> 접속 → **GitHub로 로그인**
2. 처음 한 번 `BEE-Lab-KU/bee-lab-ku.github.io` 저장소 **권한 승인**
3. 왼쪽에서 **News** 또는 **Blog** 선택 → **새 항목 추가**
4. 입력:
   - **제목**
   - **본문** (짧은 글)
   - **사진**: "사진 추가"로 여러 장 등록 (첫 장이 카드 대표 이미지)
     - 각 사진마다 **설명글(선택)** 을 달 수 있어요 → 상세보기에서 해당 사진 아래에 표시됩니다
5. **저장** → 자동으로 저장소에 커밋되고, 1~2분 뒤 사이트에 반영

> 항목 순서는 목록에서 드래그로 바꿀 수 있고, 위쪽이 최신으로 표시됩니다.

## 데이터 구조 (참고)

- 글 목록: `beelab_content/news.json`, `beelab_content/blog.json`
  - 각 항목: `{ "title": ..., "body": ..., "images": [{ "src": "경로", "caption": "설명글" }, ...] }`
- 사진 파일: `beelab_images/News/...`, `beelab_images/Blog/...`
  - `images` 배열의 경로가 그대로 화면에 사용됩니다 (폴더명 규칙·개수 입력 불필요).

## 직접 편집할 때 주의

CMS 대신 파일을 직접 고칠 경우, `images`의 각 경로는 **실제 파일이 있는 저장소 경로**여야 하며 대소문자까지 정확해야 합니다 (GitHub Pages는 대소문자를 구분).

설정 파일: 저장소 루트의 `.pages.yml`
