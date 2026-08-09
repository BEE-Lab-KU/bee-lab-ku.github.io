// ===== BEE Lab scripts (extracted from index.html) =====
  // ===== 메인 페이지 전용 동작: 최신 News/Blog 로드 + 스크롤 등장 =====
  window.addEventListener('load', function () {
    // 1) 최신 News/Blog 3개씩 렌더 (기존 buildCard / bnData / 클릭 핸들러 재사용)
    function renderHomeLatest(jsonPath, type, targetId) {
      fetch(jsonPath)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var box = document.getElementById(targetId);
          if (!box) return;
          data = bnSortByDate(data);
          if (typeof bnData !== 'undefined') { bnData[type] = data; }
          box.innerHTML = data.slice(0, 4).map(function (item, i) {
            return buildCard(item, i, type);
          }).join('');
        })
        .catch(function (e) { console.error('home ' + type + ' load error:', e); });
    }
    renderHomeLatest('News_Blog_JPG/beelab_content/news.json', 'News', 'main-news-grid');
    renderHomeLatest('News_Blog_JPG/beelab_content/blog.json', 'Blog', 'main-blog-grid');

    // 2) 스크롤 시 섹션 페이드인
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('#page-intro .home-reveal, #page-intro .reveal').forEach(function (el) { io.observe(el); });

    // 3) 메인 배경 슬라이드쇼 (순차 전환 + 하단 진행 바)
    (function () {
      var hero = document.querySelector('#page-intro .home-hero');
      if (!hero) return;
      var slides = hero.querySelectorAll('.home-hero-slide');
      var fills = hero.querySelectorAll('.home-hero-seg-fill');
      var segs = hero.querySelectorAll('.home-hero-seg');
      var n = slides.length;
      if (n < 2) return;
      var DUR = 6000;     // 슬라이드 표시 시간(ms)
      var cur = 0, timer;

      function show(i) {
        cur = (i + n) % n;
        slides.forEach(function (s, k) { s.classList.toggle('active', k === cur); });
        // 진행 바: 현재 슬라이드만 0% → 100%로 채워 남은 시간 표시
        fills.forEach(function (f) {
          f.style.transition = 'none';
          f.style.width = '0%';
        });
        void hero.offsetWidth; // reflow로 애니메이션 리셋
        var f = fills[cur];
        f.style.transition = 'width ' + DUR + 'ms linear';
        f.style.width = '100%';
      }
      function next() { show(cur + 1); }
      function start() { clearInterval(timer); timer = setInterval(next, DUR); }

      segs.forEach(function (seg, k) {
        seg.addEventListener('click', function () { show(k); start(); });
      });

      show(0);
      start();
    })();

    // 4) About 우측 사진 슬라이드
    (function () {
      var slides = document.querySelectorAll('#page-intro .about-slide');
      var dots = document.querySelectorAll('#page-intro .about-dot');
      if (slides.length < 2) return;
      var n = slides.length, cur = 0, timer;
      function show(i) {
        cur = (i + n) % n;
        slides.forEach(function (s, k) { s.classList.toggle('active', k === cur); });
        dots.forEach(function (d, k) { d.classList.toggle('active', k === cur); });
      }
      function start() { clearInterval(timer); timer = setInterval(function () { show(cur + 1); }, 4500); }
      dots.forEach(function (d) { d.addEventListener('click', function () { show(+d.dataset.i); start(); }); });
      start();
    })();
  });

var scrollPositions = {};
var tabState = {};
var navStack = [];
var currentPage = 'intro';

// 떠나는 페이지의 스크롤 위치 + 활성 탭(rp-panel) 상태 저장
function captureState(pageId) {
  scrollPositions[pageId] = window.scrollY;
  var el = document.getElementById('page-' + pageId);
  if (el) {
    var active = [];
    el.querySelectorAll('.rp-panel.active').forEach(function (p) { if (p.id) active.push(p.id); });
    tabState[pageId] = active;
  }
}

// 되돌아온 페이지의 탭 상태(pill + panel) 복원
function restoreTabs(pageId) {
  var saved = tabState[pageId];
  if (!saved || !saved.length) return;
  var el = document.getElementById('page-' + pageId);
  if (!el) return;
  saved.forEach(function (pid) {
    var panel = document.getElementById(pid);
    if (!panel) return;
    panel.parentElement.querySelectorAll('.rp-panel').forEach(function (p) { p.classList.remove('active'); });
    panel.classList.add('active');
    el.querySelectorAll('.pill').forEach(function (pill) {
      var oc = pill.getAttribute('onclick') || '';
      if (oc.indexOf("'" + pid + "'") > -1) {
        pill.parentElement.querySelectorAll('.pill').forEach(function (x) { x.classList.remove('active'); });
        pill.classList.add('active');
      }
    });
  });
}

function showPage(id, opts) {
  opts = opts || {};
  // 떠나기 전 현재 페이지 상태 저장
  captureState(currentPage);

  // 앞으로 이동: 돌아올 수 있도록 현재 페이지를 스택에 기록
  if (!opts.isBack && id !== currentPage) { navStack.push(currentPage); }

  document.querySelectorAll('.page-view').forEach(function (p) { p.classList.remove('active'); });
  var el = document.getElementById('page-' + id);
  if (el) {
    el.classList.add('active');
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = 'fadeIn 0.35s ease-out';

    // Research 그룹 페이지: 히어로 아래 섹션에 reveal 부여 + observer 등록 (전환 후에도 동작)
    if (RESEARCH_PAGES[id]) {
      el.querySelectorAll(':scope > .section').forEach(function (s) { s.classList.add('reveal'); });
    }
    observeReveals(el);

    // 뒤로가기면 탭 상태 먼저 복원 → 그 다음 스크롤 위치 복원 (레이아웃 안정화 위해 다음 프레임에 재적용)
    if (opts.isBack) restoreTabs(id);
    var y = (opts.isBack && scrollPositions[id] !== undefined) ? scrollPositions[id] : 0;
    window.scrollTo({ top: y, behavior: 'instant' });
    requestAnimationFrame(function () { window.scrollTo({ top: y, behavior: 'instant' }); });
  }
  currentPage = id;
  updateNav();
  closeMenu();
  history.pushState(null, '', '#' + id);
}

// ===== 모바일 햄버거 메뉴 토글 =====
function toggleMenu() {
  var t = document.querySelector('.nav-toggle');
  var n = document.getElementById('nav-right');
  if (!n || !t) return;
  var open = n.classList.toggle('open');
  t.classList.toggle('open', open);
  t.setAttribute('aria-expanded', open);
}
function closeMenu() {
  var t = document.querySelector('.nav-toggle');
  var n = document.getElementById('nav-right');
  if (n) n.classList.remove('open');
  if (t) { t.classList.remove('open'); t.setAttribute('aria-expanded', 'false'); }
}

function goBack(fallbackId) {
  // 실제로 들어왔던 이전 페이지로 복귀(스크롤·탭 위치 포함). 기록이 없을 때만 fallback 사용.
  var target = navStack.length ? navStack.pop() : fallbackId;
  showPage(target, { isBack: true });
}

function switchRP(btn, panelId) {
  btn.parentElement.querySelectorAll('.pill').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');
  var container = btn.parentElement.parentElement;
  container.querySelectorAll('.rp-panel').forEach(function(p){p.classList.remove('active');});
  document.getElementById(panelId).classList.add('active');
}

// rp-panel 안쪽의 하위 탭 전환. 바깥 switchRP와 클래스를 분리해 서로 간섭하지 않는다.
function switchSub(btn, panelId) {
  var wrap = btn.closest('.rp-panel');
  if (!wrap) return;
  btn.parentElement.querySelectorAll('.pill').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');
  wrap.querySelectorAll('.sub-panel').forEach(function(p){p.classList.remove('active');});
  var el = document.getElementById(panelId);
  if (el) el.classList.add('active');
}

// ===== Research 그룹 히어로: nav 투명 전환 + 스크롤 reveal (한 번만 등록) =====
var RESEARCH_PAGES = { 'main': 1, 'data-analysis': 1, 'urban-modeling': 1 };
// 풀스크린 히어로가 있어 nav가 처음엔 투명해야 하는 페이지 (메인 intro 포함)
var HERO_PAGES = { 'main': 1, 'data-analysis': 1, 'urban-modeling': 1, 'intro': 1 };

var revealIO = new IntersectionObserver(function (entries) {
  entries.forEach(function (en) {
    if (en.isIntersecting) { en.target.classList.add('in'); revealIO.unobserve(en.target); }
  });
}, { threshold: 0.12 });

function observeReveals(scope) {
  (scope || document).querySelectorAll('.reveal:not(.in)').forEach(function (el) { revealIO.observe(el); });
}

// 현재 페이지가 세 Research 그룹 중 하나이고 스크롤이 히어로 높이 안일 때만 nav 투명
function updateNav() {
  var bar = document.querySelector('.top-bar');
  if (!bar) return;
  var transparent = false;
  if (HERO_PAGES[currentPage]) {
    var page = document.getElementById('page-' + currentPage);
    var hero = page ? page.querySelector('.rhero, .home-hero') : null;
    var h = hero ? hero.offsetHeight : window.innerHeight;
    if (window.scrollY < h - 70) transparent = true;
  }
  bar.classList.toggle('rhero-transparent', transparent);
}
window.addEventListener('scroll', updateNav, { passive: true });
window.addEventListener('resize', updateNav);
updateNav();

window.addEventListener('popstate',function(){
  var h=location.hash.replace('#','');
  if(h)showPage(h, {isBack:true}); else showPage('intro', {isBack:true});
});
if(location.hash){var h=location.hash.replace('#','');if(h)showPage(h);}

function sendContactEmail(e) {
  e.preventDefault();
  var name = document.getElementById('cf-name').value;
  var email = document.getElementById('cf-email').value;
  var subject = document.getElementById('cf-subject').value;
  var message = document.getElementById('cf-message').value;
  var body = 'From: ' + name + ' (' + email + ')%0A%0A' + message;
  window.location.href = 'mailto:beelab.ku@gmail.com,hyunwoolim@konkuk.ac.kr?subject=' + encodeURIComponent('[BEE Lab Contact] ' + subject) + '&body=' + body;
}


// ====== BLOG & NEWS DYNAMIC LOADER ======
var bnData = { Blog: [], News: [] };

// 날짜(date) 내림차순 정렬: 최신이 위로. 안정 정렬이라 같은(또는 없는) 날짜는 기존 배열 순서 유지.
function bnSortByDate(items) {
  return (items || [])
    .map(function (it, i) { return { it: it, i: i }; })
    .sort(function (a, b) {
      var da = a.it.date || '', db = b.it.date || '';
      if (da === db) return a.i - b.i;   // 동일/빈 날짜 → 원래 순서 유지
      if (!da) return 1;                  // 날짜 없는 항목은 뒤로
      if (!db) return -1;
      return da < db ? 1 : -1;            // ISO 날짜 문자열 내림차순
    })
    .map(function (x) { return x.it; });
}

function loadBlogNews() {
  fetch('News_Blog_JPG/beelab_content/blog.json')
    .then(function(r) { return r.json(); })
    .then(function(data) { data = bnSortByDate(data); bnData.Blog = data; renderBNPage('blog', data, 'Blog'); })
    .catch(function(e) { console.error('Blog load error:', e); });
  fetch('News_Blog_JPG/beelab_content/news.json')
    .then(function(r) { return r.json(); })
    .then(function(data) { data = bnSortByDate(data); bnData.News = data; renderBNPage('news', data, 'News'); })
    .catch(function(e) { console.error('News load error:', e); });
}

function renderBNPage(prefix, items, type) {
  var featured = document.getElementById(prefix + '-featured');
  var grid = document.getElementById(prefix + '-grid');
  if (!featured || !grid) return;
  var top3 = items.slice(0, 3);
  var rest = items.slice(3);
  featured.innerHTML = top3.map(function(item, i) {
    return buildCard(item, i, type);
  }).join('');
  grid.innerHTML = rest.map(function(item, i) {
    return buildCard(item, i + 3, type);
  }).join('');
}

// 이미지 로드 실패 시: 숨기고, 바로 뒤에 placeholder(.bn-no-img)가 있으면 표시
function bnImgHide(img) {
  img.style.display = 'none';
  var ph = img.nextElementSibling;
  if (ph && ph.classList && ph.classList.contains('bn-no-img')) ph.style.display = 'flex';
  img.onerror = null;
}

// 이미지 항목에서 경로 추출 (객체 {src,caption} 또는 구버전 문자열 모두 지원)
function bnImgSrc(im) {
  return (typeof im === 'string') ? im : (im && im.src ? im.src : '');
}
// 첫 이미지 경로 (대표 썸네일)
function bnFirstImage(item) {
  return (item.images && item.images.length) ? bnImgSrc(item.images[0]) : '';
}

function buildCard(item, idx, type) {
  var first = bnFirstImage(item);
  var html = '<div class="bn-card" data-type="' + type + '" data-idx="' + idx + '">';
  if (first) {
    html += '<img class="bn-card-img" src="' + encodeURI(first) + '" alt="" loading="lazy" onerror="bnImgHide(this)">';
    html += '<div class="bn-no-img" style="display:none;">📷</div>';
  } else {
    html += '<div class="bn-no-img">📷</div>';
  }
  html += '<div class="bn-card-body">';
  html += '<div class="bn-card-title">' + escapeHtml(item.title) + '</div>';
  html += '</div></div>';
  return html;
}

function escapeHtml(t) {
  var d = document.createElement('div');
  d.textContent = t;
  return d.innerHTML;
}

function cleanBody(item) {
  var body = item.body || '';
  if (!body) return '';
  // Remove title if duplicated at start
  if (item.title && body.indexOf(item.title) === 0) {
    body = body.substring(item.title.length).replace(/^\s*\n/, '');
  }
  // Remove date/location that duplicate the separate fields
  if (item.date) {
    body = body.replace(new RegExp(item.date.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), 'g'), '');
  }
  if (item.location) {
    body = body.replace(new RegExp('@?\\s*' + item.location.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), 'g'), '');
  }
  // Remove trailing date patterns like "November\n28, 2025 @Seoul,  Korea"
  body = body.replace(/\n?(January|February|March|April|May|June|July|August|September|October|November|December)\s*\n?\s*\d{1,2}(?:-\d{1,2})?\s*,?\s*\d{4}\s*@[^\n]*/gi, '');
  // Clean up
  body = body.replace(/\n\s*@\s*\n/g, '\n');
  body = body.replace(/\n{3,}/g, '\n\n');
  body = body.trim();
  return body;
}

document.addEventListener('click', function(e) {
  var card = e.target.closest('.bn-card');
  if (!card) return;
  var type = card.getAttribute('data-type');
  var idx = parseInt(card.getAttribute('data-idx'));
  if (bnData[type] && bnData[type][idx]) openBNDetail(type, bnData[type][idx]);
});

function openBNDetail(type, item) {
  var m = document.getElementById('bn-modal');
  if (!m) { m = document.createElement('div'); m.id = 'bn-modal'; document.body.appendChild(m); }
  var imgs = '';
  (item.images || []).forEach(function (im) {
    var src = bnImgSrc(im);
    if (!src) return;
    var cap = (im && im.caption) ? im.caption : '';
    imgs += '<img src="' + encodeURI(src) + '" style="width:100%;border-radius:8px;margin-bottom:' + (cap ? '6px' : '12px') + ';" loading="lazy" onerror="bnImgHide(this)">';
    if (cap) imgs += '<div style="font-size:13px;color:var(--text-mid);line-height:1.6;margin-bottom:16px;text-align:center;">' + escapeHtml(cap) + '</div>';
  });
  var body = cleanBody(item);
  body = body.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  m.style.display = 'block';
  document.body.style.overflow = 'hidden';
  m.innerHTML = '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;overflow-y:auto;padding:40px 20px;-webkit-overflow-scrolling:touch;" onclick="if(event.target===this){closeBNModal();}">' +
    '<div style="max-width:700px;margin:0 auto;background:#fff;border-radius:14px;padding:36px;position:relative;">' +
    '<div onclick="closeBNModal()" style="position:absolute;top:16px;right:20px;font-size:20px;cursor:pointer;color:#999;z-index:1;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:#f5f5f5;">✕</div>' +
    '<h2 style="font-size:22px;font-weight:800;margin-bottom:10px;letter-spacing:-0.02em;line-height:1.35;padding-right:40px;">' + escapeHtml(item.title) + '</h2>' +
    (item.date ? '<div style="font-size:13px;color:#999;margin-bottom:4px;">📅 ' + escapeHtml(item.date) + '</div>' : '') +
    (item.location ? '<div style="font-size:13px;color:#999;margin-bottom:20px;">📍 ' + escapeHtml(item.location) + '</div>' : '<div style="margin-bottom:20px;"></div>') +
    (body ? '<div style="font-size:14px;color:#444;line-height:1.85;margin-bottom:24px;white-space:pre-line;border-top:1px solid #eee;padding-top:20px;">' + body + '</div>' : '') +
    imgs + '</div></div>';
}

function closeBNModal() {
  var m = document.getElementById('bn-modal');
  if (m) { m.style.display = 'none'; m.innerHTML = ''; }
  document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeBNModal();
});

loadBlogNews();

// ===== 개인연구: research-content/research.json 으로 상세 페이지 자동 생성 =====
function rEsc(t) { return String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function rParas(t) {
  return String(t == null ? '' : t).split(/\n+/)
    .map(function (s) { return s.trim(); })
    .filter(Boolean)
    .map(function (s) { return '<p>' + rEsc(s) + '</p>'; })
    .join('');
}
function buildResearchPage(r) {
  var fig = r.figure ? '<img class="research-fig" src="' + rEsc(r.figure) + '" alt="' + rEsc(r.title) + '" loading="lazy" onerror="this.style.display=\'none\'">' : '';
  var researchers = (r.researchers || []).map(function (p) {
    return '<div class="sidebar-person" onclick="showPage(\'member-' + rEsc(p.slug) + '\')"><img src="' + rEsc(p.avatar) + '" alt=""/><div><div class="name">' + rEsc(p.name) + '</div><div class="role">' + rEsc(p.role) + '</div></div></div>';
  }).join('');
  var rLabel = (r.researchers && r.researchers.length > 1) ? 'Researchers' : 'Researcher';
  var tools = (r.tools || []).map(function (t) { return '<span class="sidebar-tag">' + rEsc(t) + '</span>'; }).join('');
  var kw = (r.keywords || []).map(rEsc).join(' · ');
  var dot = r.completed ? '<span class="status-dot" style="background:#999999;"></span>' : '<span class="status-dot"></span>';
  // 관련 논문은 publications/*.json 의 research 태그에서 자동으로 채워진다.
  var papers = '<div data-research="' + rEsc(r.id) + '" style="margin-top:64px;"></div>';
  return '<div class="detail-page fade-in">' +
    '<div class="back-link" onclick="goBack(\'' + rEsc(r.back) + '\')">← ' + rEsc(r.group) + '</div>' +
    '<div class="detail-grid"><div>' +
      '<h1 style="font-size:32px;">' + rEsc(r.title) + '</h1>' +
      '<div class="detail-meta">' + dot + '<span class="status-text">' + rEsc(r.status) + '</span></div>' +
      fig +
      '<div class="detail-content">' +
        '<h3>연구배경</h3>' + rParas(r.background) +
        '<h3>연구목표</h3>' + rParas(r.goal) +
        '<h3>Keywords</h3><p>' + kw + '</p>' +
      '</div>' +
    '</div><div>' +
      '<div class="sidebar-block"><div class="sidebar-label">' + rLabel + '</div>' + researchers + '</div>' +
      (tools ? '<div class="sidebar-block"><div class="sidebar-label">Tools</div><div class="sidebar-tags">' + tools + '</div></div>' : '') +
    '</div></div>' +
    papers +
  '</div>';
}
function loadResearch() {
  return fetch('research-content/research.json')
    .then(function (r) { return r.json(); })
    .then(function (list) {
      list.forEach(function (r) {
        var el = document.getElementById('page-' + r.id);
        if (!el) { el = document.createElement('div'); el.id = 'page-' + r.id; el.className = 'page-view'; document.body.appendChild(el); }
        el.innerHTML = buildResearchPage(r);
      });
      // 딥링크 보정: 현재 해시가 방금 만든 연구 페이지면 다시 표시
      var h = location.hash.replace('#', '');
      if (h && document.getElementById('page-' + h)) { showPage(h); }
    })
    .catch(function (e) { console.error('research load error:', e); });
}
window._researchReady = loadResearch();

// DOI 는 이제 데이터(publications/*.json, members.json, research.json)에 직접 들어 있다.
// 예전에는 Publications 페이지의 화면 텍스트를 대조해 연결했는데, 인용문 형식으로 바뀌면서
// 그 방식이 성립하지 않는다. 렌더링 시점에 doi 필드를 그대로 링크로 만든다.

// ===== 프로젝트 상세 갤러리: Photos/projects/<key>-1.jpg, -2.jpg … 자동 탐색 (연속 번호) =====
function openProjImg(src) {
  var lb = document.getElementById('proj-lightbox');
  if (!lb) return;
  lb.querySelector('img').src = src;
  lb.classList.add('open');
}
function loadProjGallery(key, containerId) {
  var box = document.getElementById(containerId);
  if (!box) return;
  // 캐러셀 구조 생성
  var track = document.createElement('div'); track.className = 'pc-track';
  var prev = document.createElement('button'); prev.className = 'pc-arrow pc-prev hidden'; prev.setAttribute('aria-label', '이전'); prev.innerHTML = '‹';
  var next = document.createElement('button'); next.className = 'pc-arrow pc-next hidden'; next.setAttribute('aria-label', '다음'); next.innerHTML = '›';
  var dots = document.createElement('div'); dots.className = 'pc-dots';
  box.appendChild(track); box.appendChild(prev); box.appendChild(next); box.appendChild(dots);

  var srcs = [], cur = 0;
  function go(i) {
    cur = (i + srcs.length) % srcs.length;
    track.style.transform = 'translateX(-' + (cur * 100) + '%)';
    Array.prototype.forEach.call(dots.children, function (d, k) { d.classList.toggle('active', k === cur); });
  }
  prev.onclick = function () { go(cur - 1); };
  next.onclick = function () { go(cur + 1); };

  var exts = ['.jpg', '.png', '.jpeg', '.webp'];
  (function tryIndex(i) {
    var ei = 0;
    (function attempt() {
      var src = 'Photos/projects/' + key + '-' + i + exts[ei];
      var img = new Image();
      img.onload = function () {
        srcs.push(src);
        box.classList.remove('empty');
        var slide = document.createElement('div'); slide.className = 'pc-slide';
        slide.onclick = function () { openProjImg(src); };
        var im = document.createElement('img'); im.src = src; im.alt = key + ' ' + i; im.loading = 'lazy';
        slide.appendChild(im); track.appendChild(slide);
        var dot = document.createElement('div'); dot.className = 'pc-dot' + (srcs.length === 1 ? ' active' : '');
        (function (idx) { dot.onclick = function () { go(idx); }; })(srcs.length - 1);
        dots.appendChild(dot);
        if (srcs.length > 1) { prev.classList.remove('hidden'); next.classList.remove('hidden'); }
        tryIndex(i + 1);
      };
      img.onerror = function () {
        if (++ei < exts.length) { attempt(); }
        // i===1 실패 → 이미지 없음, .empty 유지(숨김)
      };
      img.src = src;
    })();
  })(1);
}
['datanet', 'green', 'lh', 'carbon'].forEach(function (k) { loadProjGallery(k, 'proj-gallery-' + k); });
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') { var lb = document.getElementById('proj-lightbox'); if (lb) lb.classList.remove('open'); }
});


// ===== Publications 배지 =====
// 사람이 고르는 값은 저널의 SCIE / SCOPUS / KCI 뿐이다.
// 학회의 국제와 국내는 카테고리가 이미 결정하므로 입력받지 않고 유도한다.
// badge를 비워두면 카테고리 기본값이 붙으므로 기존 데이터를 고칠 필요가 없다.
var PUB_BADGE_CLASS = {
  'SCIE':       'sci',
  'SCOPUS':     'scopus',
  'KCI':        'kci',
  'INT. CONF.': 'int-conf',
  'DOM. CONF.': 'dom-conf'
};
function pubBadgeLabel(e){
  var b = String((e && e.badge) || '').trim().toUpperCase();
  if (b === 'SCIE' || b === 'SCOPUS' || b === 'KCI') return b;   // 지정값 우선
  switch (e && e.category) {
    case 'international': return 'SCIE';
    case 'domestic':      return 'KCI';
    case 'int-conf':      return 'INT. CONF.';
    case 'dom-conf':      return 'DOM. CONF.';
  }
  // 프로필과 연구 페이지에는 category가 없다. 저널은 항상 배지를 갖고 있으므로
  // 여기까지 온 항목은 학회다. 인용문의 언어로 국제와 국내를 가른다.
  var txt = String((e && (e.citation || e.venue)) || '');
  if (!txt) return b;   // 알 수 없는 값은 그대로 노출해서 조용히 사라지지 않게 한다
  return /[가-힣]/.test(txt) ? 'DOM. CONF.' : 'INT. CONF.';
}
function pubBadgeHtml(e){
  var label = pubBadgeLabel(e);
  if (!label) return '';
  var cls = PUB_BADGE_CLASS[label] || 'conf';
  return '<span class="pub-badge '+cls+'">'+label.replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</span>';
}

// ===== 인용문 표시 =====
// citation 은 APA 형태의 한 줄이다. 끝부분의 저널명(또는 학회명)만 찾아 이탤릭으로 강조한다.
// 매칭에 실패하면 원문을 그대로 내보내므로 표시가 깨지지 않는다.
var PUB_VENUE_RE = /\.\s*([^.]+?)(?:,\s*\d+(?:\(\d+\))?)?(?:,\s*(?:Article\s+)?[\d–-]+)?\.\s*$/;
function pubEsc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function citationHtml(cite){
  var raw = String(cite || '');
  var m = PUB_VENUE_RE.exec(raw);
  if (!m) return pubEsc(raw);
  var start = m.index + m[0].indexOf(m[1]);
  var end = start + m[1].length;
  return pubEsc(raw.slice(0, start)) + '<em>' + pubEsc(raw.slice(start, end)) + '</em>' + pubEsc(raw.slice(end));
}
function pubDoiHtml(url){
  if (!url) return '';
  return '<a href="'+pubEsc(url)+'" target="_blank" rel="noopener" class="pub-doi-link" style="font-size:12px;color:#000;font-weight:600;text-decoration:underline;text-underline-offset:2px;">🔗 DOI</a>';
}
// 수상은 이름을 데이터에 담는다. 우수논문상과 우수논문발표상은 다른 상이다.
// 예전 데이터의 true 는 학회 발표에만 붙어 있었으므로 우수논문발표상으로 본다.
function pubAwardHtml(a){
  if (!a) return '';
  var name = (a === true) ? '우수논문발표상' : String(a).replace(/^🏆\s*/, '').trim();
  if (!name) return '';
  return '<span style="margin-left:8px;font-size:11px;font-weight:600;color:#D4A017;">🏆 '+pubEsc(name)+'</span>';
}

// 논문은 publications/*.json 이 유일한 출처다.
// 각 항목의 members 와 research 태그를 보고 프로필과 연구 페이지가 알아서 골라 간다.
function pubByDateDesc(a, b){
  var da = String(a.date||''), db = String(b.date||'');
  return da < db ? 1 : (da > db ? -1 : 0);
}
function pubsFor(key, value){
  return (window.PUBLICATIONS || []).filter(function(e){
    var arr = e[key];
    return Array.isArray(arr) && arr.indexOf(value) >= 0;
  }).sort(pubByDateDesc);
}
function researchPaperCard(e){
  var meta = pubBadgeHtml(e) + pubDoiHtml(e.doi) + pubAwardHtml(e.award);
  return '<div style="padding:16px;border:1px solid var(--border);border-radius:8px;margin:8px 0;">'
    + '<div style="font-size:14px;line-height:1.55;">' + citationHtml(e.citation) + '</div>'
    + (meta ? '<div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">' + meta + '</div>' : '')
    + '</div>';
}
// 연구 상세 페이지의 [data-research] 칸을 채운다. 정적 페이지와 research.json 페이지 모두 같은 방식이다.
function fillResearchPapers(){
  document.querySelectorAll('[data-research]').forEach(function(box){
    var items = pubsFor('research', box.getAttribute('data-research'));
    box.innerHTML = items.length
      ? '<h3>관련 논문</h3>' + items.map(researchPaperCard).join('')
      : '';
  });
}

// ===== Publications: publications/<종류>.json 4개로 목록 자동 생성 =====
(function () {
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function rowHtml(e){
    return '<div class="pub-row">'
      + '<div class="pub-year">'+esc(String(e.date||'').slice(0,4))+'</div>'
      + '<div><div class="pub-title">'+citationHtml(e.citation)+'</div>'
      + pubDoiHtml(e.doi)+pubAwardHtml(e.award)+'</div>'
      + '<div>'+pubBadgeHtml(e)+'</div>'
      + '</div>';
  }
  function groupHeader(y, first){
    var style = first ? 'font-size:20px;font-weight:700;margin-bottom:20px;'
                      : 'font-size:20px;font-weight:700;margin:40px 0 20px;';
    return '<div style="'+style+'">'+esc(y)+'</div>';
  }
  function renderFlat(entries){
    var html = '', curGroup = null, first = true;
    entries.forEach(function(e){
      var g = String(e.date||'').slice(0,4);
      if(g !== curGroup){ html += groupHeader(g, first); curGroup = g; first = false; }
      html += rowHtml(e);
    });
    return html;
  }
  function set(id, html){ var el = document.getElementById(id); if(el) el.innerHTML = html; }

  // 종류별로 파일이 나뉘어 있다. 어느 파일에서 왔는지가 곧 category 이므로
  // 데이터에 category 를 저장하지 않고 불러올 때 붙인다.
  var PUB_SOURCES = [
    { cat: 'international', panel: 'pub-international' },
    { cat: 'domestic',      panel: 'pub-domestic' },
    { cat: 'int-conf',      panel: 'pub-int-conf' },
    { cat: 'dom-conf',      panel: 'pub-dom-conf' }
  ];
  window._pubReady = Promise.all(PUB_SOURCES.map(function(src){
    return fetch('publications/'+src.cat+'.json')
      .then(function(r){ return r.json(); })
      .then(function(list){
        if(!Array.isArray(list)) list = [];
        list.forEach(function(e){ e.category = src.cat; });
        list.sort(pubByDateDesc);
        set(src.panel, renderFlat(list));
        return list;
      })
      .catch(function(err){ console.error('publications load failed: '+src.cat, err); return []; });
  })).then(function(groups){
    // 프로필과 연구 페이지가 여기서 논문을 가져간다. 유일한 출처다.
    window.PUBLICATIONS = groups.reduce(function(a,b){ return a.concat(b); }, []).sort(pubByDateDesc);
    return window.PUBLICATIONS;
  });
})();

// ===== Members: members.json 으로 리스팅 + 프로필 페이지 자동 생성 =====
(function () {
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // --- 공통: 프로필/논문 행 ---
  function pubRow(e){
    return '<div class="pub-row"><div class="pub-year">'+esc(String(e.date||e.year||'').slice(0,4))+'</div>'
      + '<div><div class="pub-title">'+citationHtml(e.citation)+'</div>'
      + pubDoiHtml(e.doi)+pubAwardHtml(e.award)+'</div>'
      + '<div>'+pubBadgeHtml(e)+'</div></div>';
  }

  // --- 카드 (researchers / alumni) ---
  // 사진이 아직 없을 때(로드 실패) 깨진 이미지 아이콘 대신 회색 원(1x1 투명 + 배경색) 표시
  var AVATAR_FALLBACK = "this.onerror=null;this.src='data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=='";
  // subtitle을 주면 카드 두 번째 줄을 그것으로 바꾼다. 학위별 보기에서는 역할 대신 연구분야를 보여준다.
  function card(m, subtitle){
    var sub = (subtitle == null) ? m.role : subtitle;
    return '<div class="member-card" onclick="showPage(\'member-'+m.slug+'\')">'
      + '<img class="member-avatar" src="'+esc(m.avatar)+'" alt="'+esc(m.name)+'" onerror="'+AVATAR_FALLBACK+'"/>'
      + '<div class="name">'+esc(m.name)+'</div><div class="role">'+esc(sub)+'</div>'
      + '<div class="arrow-hint">View Profile →</div></div>';
  }
  function cardOnly(m){ return card(m); }   // map()의 index가 subtitle로 새는 것 방지

  // --- 교수 패널 ---
  function renderProfessor(p){
    var links = (p.links||[]).map(function(l){
      return '<a href="'+esc(l.url)+'" target="_blank" style="font-size:13px;padding:6px 14px;border:1px solid var(--border);border-radius:100px;color:var(--text-mid);text-decoration:none;">'+esc(l.label)+'</a>';
    }).join('');
    var header = '<div class="prof-header" style="display:flex;gap:48px;align-items:flex-start;padding:40px;border:1px solid var(--border);border-radius:12px;margin-bottom:40px;">'
      + '<img class="prof-photo" src="'+esc(p.avatar)+'" alt="'+esc(p.nameKr)+'" style="width:180px;height:220px;object-fit:cover;border-radius:12px;flex-shrink:0;background:#E0E0E0;">'
      + '<div>'
      + '<div style="font-size:14px;font-weight:600;color:var(--text-muted);margin-bottom:8px;">Professor:</div>'
      + '<div style="font-size:32px;font-weight:900;letter-spacing:-0.03em;margin-bottom:4px;">'+esc(p.name)+'</div>'
      + '<div style="font-size:15px;color:var(--text-muted);margin-bottom:8px;">'+esc(p.title)+'</div>'
      + '<div style="font-size:15px;color:var(--text-mid);margin-bottom:20px;">'+esc(p.affiliation)+'</div>'
      + '<div style="display:flex;gap:12px;flex-wrap:wrap;">'+links+'</div>'
      + '</div></div>';
    var secs = (p.sections||[]).map(function(s, i){
      var last = (i === p.sections.length - 1);
      var mb = last ? 'margin-bottom:20px;' : 'margin-bottom:40px;';
      var lines = (s.lines||[]).map(function(x){ return '<div>'+x+'</div>'; }).join('');
      return '<div style="'+mb+'">'
        + '<div style="font-size:20px;font-weight:800;letter-spacing:-0.02em;margin-bottom:16px;">'+esc(s.title)+'</div>'
        + '<div style="font-size:14px;color:var(--text-mid);line-height:2.2;">'+lines+'</div>'
        + '</div>';
    }).join('');
    return header + secs;
  }

  function sectionHead(label, n){
    return '<div style="font-size:20px;font-weight:700;margin-bottom:8px;color:var(--text-muted);">'
      + esc(label) + (n ? ' <span style="font-weight:500;">('+n+')</span>' : '') + '</div>';
  }

  // --- 연구원 패널: 연구분야별 ---
  function renderResearchers(groups){
    return (groups||[]).map(function(g){
      var cards = (g.members||[]).map(cardOnly).join('');
      return sectionHead(g.group, (g.members||[]).length)
        + '<div class="members-grid" style="margin-bottom:40px;">'+cards+'</div>';
    }).join('');
  }

  // --- 연구원 패널: 학위별 ---
  // 학위는 role 문자열에서 유도한다. members.json에 별도 필드를 두지 않으므로
  // 표기가 바뀌어도(Ph.D. Student / 박사과정 등) 같은 칸에 들어가도록 폭넓게 매칭한다.
  var DEGREE_ORDER = [
    { key: 'phd',      label: 'Ph.D. Students' },
    { key: 'master',   label: "Master's Students" },
    { key: 'bachelor', label: 'Undergraduate Researchers' },
    { key: 'other',    label: 'Others' }
  ];
  function degreeKey(role){
    var r = String(role||'').toLowerCase();
    if (/ph\.?\s*d|doctoral|박사/.test(r)) return 'phd';
    if (/master|\bm\.\s*s\.?|석사/.test(r)) return 'master';
    if (/undergrad|bachelor|\bb\.\s*s\.?|학부|학사/.test(r)) return 'bachelor';
    return 'other';
  }
  function renderByDegree(groups){
    var buckets = {};
    (groups||[]).forEach(function(g){
      (g.members||[]).forEach(function(m){
        var k = degreeKey(m.role);
        (buckets[k] = buckets[k] || []).push({ m: m, group: g.group });
      });
    });
    return DEGREE_ORDER.map(function(d){
      var arr = buckets[d.key];
      if (!arr || !arr.length) return '';
      var cards = arr.map(function(x){ return card(x.m, x.group); }).join('');
      return sectionHead(d.label, arr.length)
        + '<div class="members-grid" style="margin-bottom:40px;">'+cards+'</div>';
    }).join('');
  }

  // --- 졸업생 패널 ---
  function renderAlumni(list){
    return '<div class="members-grid">'+(list||[]).map(cardOnly).join('')+'</div>';
  }

  // --- 개인 프로필 페이지 ---
  function renderProfile(slug, p){
    var bioStyle = p.bioStyle ? ' style="'+p.bioStyle+'"' : '';
    var top = '<div class="profile-top">'
      + '<img class="profile-avatar" src="'+esc(p.avatar)+'" alt="" onerror="'+AVATAR_FALLBACK+'"/>'
      + '<div class="profile-info"><h1>'+esc(p.name)+'</h1><div class="role-line">'+esc(p.roleLine)+'</div>'
      + '<div class="bio"'+bioStyle+'>'+(p.bio||'')+'</div></div>'
      + '</div>';
    var research = '';
    if(p.research && p.research.length){
      var items = p.research.map(function(r){
        return '<div class="profile-research-item" onclick="showPage(\''+r.page+'\')"><h4>'+esc(r.title)+'</h4><p>'+esc(r.tags)+'</p></div>';
      }).join('');
      research = '<div class="profile-research-list"><h3>Research</h3>'+items+'</div>';
    }
    // 논문은 publications/*.json 에서 members 태그로 골라 온다. members.json 에 따로 두지 않는다.
    var mine = pubsFor('members', slug);
    var pubs = mine.length
      ? '<div class="profile-research-list" style="margin-top:48px;"><h3>Publications</h3>'+mine.map(pubRow).join('')+'</div>'
      : '';
    return '<div class="profile-page fade-in">'
      + '<div class="back-link" onclick="goBack(\'members-all\')">← People</div>'
      + top + research + pubs
      + '</div>';
  }

  function set(id, html){ var el = document.getElementById(id); if(el) el.innerHTML = html; }

  window._memReady = Promise.all([
      fetch('members.json').then(function(r){ return r.json(); }),
      window._pubReady
    ])
    .then(function(res){
      var data = res[0];
      set('mem-professor', renderProfessor(data.professor || {}));
      set('mem-by-area',   renderResearchers(data.researchers || []));
      set('mem-by-degree', renderByDegree(data.researchers || []));
      set('mem-alumni', renderAlumni(data.alumni || []));
      var profs = data.profiles || {};
      Object.keys(profs).forEach(function(slug){
        set('page-member-'+slug, renderProfile(slug, profs[slug]));
      });
    })
    .catch(function(err){ console.error('members load failed', err); });
})();

// 세 데이터가 모두 로드되면 준비 완료. 후처리로 연결할 것이 더는 없다.
window._siteReady = Promise.all([window._pubReady, window._memReady, window._researchReady])
  .then(function(){ fillResearchPapers(); });
