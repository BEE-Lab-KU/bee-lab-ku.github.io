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
  history.pushState(null, '', '#' + id);
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
  window.location.href = 'mailto:hjw970301@gmail.com?subject=' + encodeURIComponent('[BEE Lab Contact] ' + subject) + '&body=' + body;
}


// ====== BLOG & NEWS DYNAMIC LOADER ======
var bnData = { Blog: [], News: [] };

function loadBlogNews() {
  fetch('News_Blog_JPG/beelab_content/blog.json')
    .then(function(r) { return r.json(); })
    .then(function(data) { bnData.Blog = data; renderBNPage('blog', data, 'Blog'); })
    .catch(function(e) { console.error('Blog load error:', e); });
  fetch('News_Blog_JPG/beelab_content/news.json')
    .then(function(r) { return r.json(); })
    .then(function(data) { bnData.News = data; renderBNPage('news', data, 'News'); })
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

// Image extension fallback: .jpg -> .png -> .jpeg -> .webp
var bnExtFallbacks = ['.png', '.jpeg', '.webp'];

function bnImgFallback(img) {
  var bp = img.getAttribute('data-basepath');
  var tried = parseInt(img.getAttribute('data-ext-idx') || '0');
  if (tried >= bnExtFallbacks.length) {
    img.style.display = 'none';
    var ph = img.nextElementSibling;
    if (ph) ph.style.display = 'flex';
    img.onerror = null;
    return;
  }
  img.setAttribute('data-ext-idx', tried + 1);
  img.src = bp + bnExtFallbacks[tried];
}

function buildCard(item, idx, type) {
  var hasImg = item.image_count > 0;
  var basePath = 'News_Blog_JPG/beelab_images/' + type + '/' + encodeURIComponent(item.folder) + '/001';
  var dateStr = item.date ? item.date : '';
  var html = '<div class="bn-card" data-type="' + type + '" data-idx="' + idx + '">';
  if (hasImg) {
    html += '<img class="bn-card-img" data-basepath="' + escapeHtml(basePath) + '" src="' + basePath + '.jpg" alt="" loading="lazy" onerror="bnImgFallback(this)">';
    html += '<div class="bn-no-img" style="display:none;">📷</div>';
  } else {
    html += '<div class="bn-no-img">📷</div>';
  }
  html += '<div class="bn-card-body">';
  html += '<div class="bn-card-title">' + escapeHtml(item.title) + '</div>';
  if (dateStr) html += '<div class="bn-card-date">' + escapeHtml(dateStr) + '</div>';
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
  for (var i = 1; i <= item.image_count; i++) {
    var num = String(i).padStart(3, '0');
    var bp = 'News_Blog_JPG/beelab_images/' + type + '/' + encodeURIComponent(item.folder) + '/' + num;
    imgs += '<img data-basepath="' + escapeHtml(bp) + '" src="' + bp + '.jpg" style="width:100%;border-radius:8px;margin-bottom:12px;" loading="lazy" onerror="bnImgFallback(this)">';
  }
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
  var papers = '';
  if (r.papers && r.papers.length) {
    papers = '<div style="margin-top:64px;border-top:1px solid var(--border);padding-top:48px;"><h3>관련 논문</h3>' +
      r.papers.map(function (p) {
        return '<div style="padding:16px;border:1px solid var(--border);border-radius:8px;margin:8px 0;">' +
          '<div style="font-size:14px;font-weight:600;">' + rEsc(p.title) + '</div>' +
          '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">' + rEsc(p.authors) + '</div>' +
          (p.venue ? '<div style="font-size:12px;color:var(--text-muted);margin-top:2px;">' + rEsc(p.venue) + '</div>' : '') +
          '</div>';
      }).join('') + '</div>';
  }
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
  fetch('research-content/research.json')
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
loadResearch();

// ===== 개인 프로필 논문 → DOI 링크 연결 (Publications 페이지를 단일 출처로 사용) =====
function linkProfilePapersToDOI() {
  var norm = function (s) { return String(s || '').replace(/\s+/g, ' ').trim().toLowerCase(); };
  var pubPage = document.getElementById('page-publications');
  if (!pubPage) return;
  // 1) Publications 페이지에서 "논문 제목 → DOI URL" 맵 구축
  var doiMap = {};
  pubPage.querySelectorAll('.pub-row').forEach(function (row) {
    var titleEl = row.querySelector('.pub-title');
    var link = row.querySelector('a[href^="http"]');
    if (titleEl && link) { doiMap[norm(titleEl.textContent)] = link.href; }
  });
  // 2) 멤버 프로필의 논문 제목에 매칭되는 DOI가 있으면 제목 자체를 링크로 변환
  document.querySelectorAll('[id^="page-member-"] .pub-title').forEach(function (titleEl) {
    if (titleEl.querySelector('a')) return; // 이미 링크면 건너뜀
    var url = doiMap[norm(titleEl.textContent)];
    if (!url) return;
    var a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.className = 'pub-doi-link';
    a.textContent = titleEl.textContent;
    titleEl.textContent = '';
    titleEl.appendChild(a);
  });
}
linkProfilePapersToDOI();

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


// ===== Publications: publications.json 으로 목록 자동 생성 =====
(function () {
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function badgeHtml(b){
    if(!b) return '';
    var cls = (b === 'SCIE') ? 'sci' : 'conf';
    return '<span class="pub-badge '+cls+'">'+esc(b)+'</span>';
  }
  function doiHtml(url){
    if(!url) return '';
    return '<a href="'+esc(url)+'" target="_blank" style="font-size:12px;color:#000;font-weight:600;text-decoration:underline;text-underline-offset:2px;">🔗 DOI</a>';
  }
  function awardHtml(a){
    if(!a) return '';
    return '<span style="margin-left:8px;font-size:11px;font-weight:600;color:#D4A017;">'+esc(a)+'</span>';
  }
  function rowHtml(e){
    return '<div class="pub-row">'
      + '<div class="pub-year">'+esc(e.year)+'</div>'
      + '<div><div class="pub-title">'+esc(e.title)+'</div>'
      + '<div class="pub-journal">'+esc(e.venue)+'</div>'+doiHtml(e.doi)+awardHtml(e.award)+'</div>'
      + '<div>'+badgeHtml(e.badge)+'</div>'
      + '</div>';
  }
  function groupHeader(y, first){
    var style = first ? 'font-size:20px;font-weight:700;margin-bottom:20px;'
                      : 'font-size:20px;font-weight:700;margin:40px 0 20px;';
    return '<div style="'+style+'">'+esc(y)+'</div>';
  }
  function sectionHeader(s, first){
    var style = first ? 'font-size:24px;font-weight:800;margin-bottom:32px;letter-spacing:-0.02em;'
                      : 'font-size:24px;font-weight:800;margin:64px 0 32px;letter-spacing:-0.02em;border-top:2px solid var(--border);padding-top:48px;';
    return '<div style="'+style+'">'+esc(s)+'</div>';
  }
  function renderFlat(entries){
    var html = '', curGroup = null, first = true;
    entries.forEach(function(e){
      if(e.group !== curGroup){ html += groupHeader(e.group, first); curGroup = e.group; first = false; }
      html += rowHtml(e);
    });
    return html;
  }
  function renderConferences(entries){
    var html = '', curSec = null, curGroup = null, firstSec = true, firstGroup = true;
    entries.forEach(function(e){
      if(e.section !== curSec){
        html += sectionHeader(e.section, firstSec);
        curSec = e.section; firstSec = false; curGroup = null; firstGroup = true;
      }
      if(e.group !== curGroup){ html += groupHeader(e.group, firstGroup); curGroup = e.group; firstGroup = false; }
      html += rowHtml(e);
    });
    return html;
  }
  function set(id, html){ var el = document.getElementById(id); if(el) el.innerHTML = html; }

  fetch('publications.json')
    .then(function(r){ return r.json(); })
    .then(function(data){
      set('pub-international', renderFlat(data.international || []));
      set('pub-domestic',     renderFlat(data.domestic || []));
      set('pub-conferences',  renderConferences(data.conferences || []));
    })
    .catch(function(err){ console.error('publications load failed', err); });
})();

// ===== Members: members.json 으로 리스팅 + 프로필 페이지 자동 생성 =====
(function () {
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  // --- 공통: 프로필/논문 행 ---
  function badgeHtml(b){ if(!b) return ''; var cls=(b==='SCIE')?'sci':'conf'; return '<span class="pub-badge '+cls+'">'+esc(b)+'</span>'; }
  function awardHtml(a){ if(!a) return ''; return '<span style="margin-left:8px;font-size:11px;font-weight:600;color:#D4A017;">'+esc(a)+'</span>'; }
  function pubRow(e){
    return '<div class="pub-row"><div class="pub-year">'+esc(e.year)+'</div>'
      + '<div><div class="pub-title">'+esc(e.title)+'</div>'
      + '<div class="pub-journal">'+esc(e.venue)+'</div>'+awardHtml(e.award)+'</div>'
      + '<div>'+badgeHtml(e.badge)+'</div></div>';
  }

  // --- 카드 (researchers / alumni) ---
  function card(m){
    return '<div class="member-card" onclick="showPage(\'member-'+m.slug+'\')">'
      + '<img class="member-avatar" src="'+esc(m.avatar)+'" alt="'+esc(m.name)+'"/>'
      + '<div class="name">'+esc(m.name)+'</div><div class="role">'+esc(m.role)+'</div>'
      + '<div class="arrow-hint">View Profile →</div></div>';
  }

  // --- 교수 패널 ---
  function renderProfessor(p){
    var links = (p.links||[]).map(function(l){
      return '<a href="'+esc(l.url)+'" target="_blank" style="font-size:13px;padding:6px 14px;border:1px solid var(--border);border-radius:100px;color:var(--text-mid);text-decoration:none;">'+esc(l.label)+'</a>';
    }).join('');
    var header = '<div style="display:flex;gap:48px;align-items:flex-start;padding:40px;border:1px solid var(--border);border-radius:12px;margin-bottom:40px;">'
      + '<img src="'+esc(p.avatar)+'" alt="'+esc(p.nameKr)+'" style="width:180px;height:220px;object-fit:cover;border-radius:12px;flex-shrink:0;background:#E0E0E0;">'
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

  // --- 연구원 패널 (그룹별) ---
  function renderResearchers(groups){
    return (groups||[]).map(function(g){
      var cards = (g.members||[]).map(card).join('');
      return '<div style="font-size:20px;font-weight:700;margin-bottom:8px;color:var(--text-muted);">'+esc(g.group)+'</div>'
        + '<div class="members-grid" style="margin-bottom:40px;">'+cards+'</div>';
    }).join('');
  }

  // --- 졸업생 패널 ---
  function renderAlumni(list){
    return '<div class="members-grid">'+(list||[]).map(card).join('')+'</div>';
  }

  // --- 개인 프로필 페이지 ---
  function renderProfile(slug, p){
    var bioStyle = p.bioStyle ? ' style="'+p.bioStyle+'"' : '';
    var top = '<div class="profile-top">'
      + '<img class="profile-avatar" src="'+esc(p.avatar)+'" alt=""/>'
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
    var pubs = '';
    if(p.publications && p.publications.length){
      pubs = '<div class="profile-research-list" style="margin-top:48px;"><h3>Publications</h3>'+p.publications.map(pubRow).join('')+'</div>';
    }
    return '<div class="profile-page fade-in">'
      + '<div class="back-link" onclick="goBack(\'members-all\')">← People</div>'
      + top + research + pubs
      + '</div>';
  }

  function set(id, html){ var el = document.getElementById(id); if(el) el.innerHTML = html; }

  fetch('members.json')
    .then(function(r){ return r.json(); })
    .then(function(data){
      set('mem-professor', renderProfessor(data.professor || {}));
      set('mem-researchers', renderResearchers(data.researchers || []));
      set('mem-alumni', renderAlumni(data.alumni || []));
      var profs = data.profiles || {};
      Object.keys(profs).forEach(function(slug){
        set('page-member-'+slug, renderProfile(slug, profs[slug]));
      });
    })
    .catch(function(err){ console.error('members load failed', err); });
})();
