#!/usr/bin/env python3
"""논문 태그와 CMS 목록을 자동으로 맞춘다. GitHub Actions 에서 실행된다.

두 가지를 한다.

1. members 와 first(제1저자) 태그 자동 보완
   저자를 이니셜로 맞추면 'Lim, J.' 가 임지수인지 임종연인지 알 수 없다.
   그래서 이름 전체가 확인되는 경우에만 붙인다.
     - 국문 인용문: 한글 이름 전체가 들어 있으면 그 사람
     - DOI 가 있는 논문: Crossref 가 주는 given name 전체를 대조
   이미 members 를 지정한 논문은 건드리지 않는다. 사람이 고른 것이 우선이다.
   first 는 인용문의 첫 저자를 members 중에서 가려낸 값이다.
   개인 프로필은 first 가 자기인 논문만 보여 준다. 공저까지 넣으면 목록이 과도해진다.

2. CMS 선택 목록 동기화
   .pages.yml 의 _lab_members 와 _research_pages 를 members.json 과
   실제 연구 페이지 id 에서 다시 만든다. 학생이 들어오거나 연구 페이지가
   생기면 CMS 드롭다운에 자동으로 나타난다.

어느 쪽이든 결과가 이상하면 아무것도 쓰지 않고 끝낸다.
"""
import json, glob, os, re, sys, time, urllib.request, urllib.parse

MAILTO = "ecosoop@gmail.com"
DOI_RE = re.compile(r'(10\.\d{4,9}/[^\s"\'<>?&]+)')

# 로마자 이름. 성만으로는 부족하므로 이름 전체를 함께 본다.
ROMAN = {
    'doyeon':  ('lee',  ['doyeon']),
    'inseob':  ('kim',  ['inseop', 'inseob']),
    'jiyoung': ('kim',  ['jiyoung']),
    'sangmin': ('lee',  ['sangmin']),
    'junghyun':('cho',  ['junghyun', 'jeonghyun']),
    'jaeuk':   ('baek', ['jaeuk', 'jaewook']),
    'jiung':   ('han',  ['jiung', 'jiwoong']),
    'jungyun': ('hwang',['jeongyun', 'jungyun']),
    'jisu':    ('lim',  ['jisoo', 'jisu']),
    'hyunsu':  ('lee',  ['hyunsu']),
    'seyeon':  ('kim',  ['seyeon']),
    'junho':   ('song', ['junho']),
    'kyungjae':('lee',  ['kyungjae']),
}


INITIAL = {
    'doyeon': 'Lee, D.', 'inseob': 'Kim, I.', 'jiyoung': 'Kim, J.', 'sangmin': 'Lee, S.',
    'junghyun': 'Cho, J.', 'jaeuk': 'Baek, J.', 'jiung': 'Han, J.', 'jungyun': 'Hwang, J.',
    'jisu': 'Lim, J.', 'hyunsu': 'Lee, H.', 'seyeon': 'Kim, S.', 'junho': 'Song, J.',
    'kyungjae': 'Lee, K.',
}


def first_author(e, names, cache):
    """인용문의 첫 저자가 members 중 누구인지. 못 정하면 None."""
    ms = e.get('members') or []
    if not ms:
        return None
    head = (re.match(r'^(.*?)\s*\(\d{4}\)', e.get('citation', '')) or [None, ''])[1]
    if re.search(r'[가-힣]', head):
        m = re.match(r'\s*([가-힣]{2,4})', head)
        return next((s for s in ms if names.get(s) == m.group(1)), None) if m else None
    d = DOI_RE.search(e.get('doi') or '')
    rec = crossref(d.group(1).rstrip('.,;)'), cache) if d else None
    if rec and rec.get('author'):
        a = rec['author'][0]
        fam = (a.get('family') or '').lower()
        giv = (a.get('given') or '').lower().replace('-', '').replace(' ', '')
        for s in ms:
            f, gs = ROMAN[s]
            if f == fam and any(g in giv for g in gs):
                return s
        return None
    m = re.match(r"\s*([A-Z][A-Za-z\-']+,\s*(?:[A-Z]\.[\s\-]*)+)", head)
    if not m:
        return None
    tok = re.sub(r'\s+', ' ', m.group(1)).strip()
    cand = [s for s in ms if tok.startswith(INITIAL.get(s, '\x00'))]
    return cand[0] if len(cand) == 1 else None


def people_from_members():
    mem = json.load(open('members.json', encoding='utf-8'))
    order, names = [], {}
    for g in mem['researchers']:
        for m in g['members']:
            order.append(m['slug']); names[m['slug']] = m['name']
    alumni = []
    for m in mem['alumni']:
        alumni.append(m['slug']); names[m['slug']] = m['name']
    return order, alumni, names


def research_page_ids():
    """실제로 존재하는 연구 상세 페이지. 정적 컨테이너와 research.json 을 합친다."""
    html = open('index.html', encoding='utf-8').read()
    ids = set(re.findall(r'id="page-(research-[a-z0-9-]+)"', html))
    ids.discard('research-topics')
    titles = {}
    for m in re.finditer(r'id="page-(research-[a-z0-9-]+)"', html):
        seg = html[m.start(): m.start() + 4000]
        t = re.search(r'<h1[^>]*>(.*?)</h1>', seg, re.S)
        if t:
            titles[m.group(1)] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', t.group(1))).strip()
    for r in json.load(open('research-content/research.json', encoding='utf-8')):
        ids.add(r['id'])
        if r.get('title'):
            titles[r['id']] = r['title']
    return sorted(ids), titles


def crossref(doi, cache):
    if doi in cache:
        return cache[doi]
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={
        "User-Agent": f"bee-lab-site/1.0 (mailto:{MAILTO})"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            cache[doi] = json.load(r)["message"]
    except Exception as e:
        print(f"    Crossref 실패 {doi}: {e}", file=sys.stderr)
        cache[doi] = None
    time.sleep(0.4)
    return cache[doi]


def auto_tag_members(names):
    """이름 전체가 확인될 때만 태그를 붙인다. 이미 지정된 논문은 그대로 둔다."""
    cache, added, looked = {}, [], 0
    for f in sorted(glob.glob('publications/*.json')):
        arr = json.load(open(f, encoding='utf-8'))
        changed = False
        for e in arr:
            if 'members' in e:          # 사람이 이미 골랐다. 존중한다.
                continue
            cit = e.get('citation', '')
            head = (re.match(r'^(.*?)\s*\(\d{4}\)', cit) or [None, ''])[1]
            found = set()

            if re.search(r'[가-힣]', head):
                for slug, nm in names.items():
                    if nm and nm in head:
                        found.add(slug)
            else:
                m = DOI_RE.search(e.get('doi') or '')
                if m:
                    looked += 1
                    rec = crossref(m.group(1).rstrip('.,;)'), cache)
                    if rec:
                        auth = [((a.get('family') or '').lower(),
                                 (a.get('given') or '').lower().replace('-', '').replace(' ', ''))
                                for a in rec.get('author', [])]
                        for slug, (fam, givens) in ROMAN.items():
                            if any(af == fam and any(g in ag for g in givens) for af, ag in auth):
                                found.add(slug)
            if found:
                e['members'] = sorted(found)
                changed = True
                added.append((sorted(found), cit[:70]))
        # members 가 있는데 first 가 비어 있으면 채운다
        for e in arr:
            if e.get('members') and not e.get('first'):
                fa = first_author(e, names, cache)
                if fa:
                    e['first'] = fa
                    changed = True
                    print(f"    first={fa}  {e.get('citation','')[:62]}")
        if changed:
            json.dump(arr, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"  members 자동 부여 {len(added)}건 (Crossref 조회 {looked}회)")
    for who, cit in added:
        print(f"    + {who}  {cit}")
    return len(added)


def sync_pages_yml(order, alumni, names, pages, titles):
    """CMS 선택 목록을 다시 만든다. 망가질 것 같으면 쓰지 않는다."""
    src = open('.pages.yml', encoding='utf-8').read()

    def blk(items):
        out = []
        for v, l in items:
            out.append(f"  - value: {v}")
            out.append(f"  " + f"  label: {json.dumps(l, ensure_ascii=False)}")
        return "\n".join(out)

    members = [(s, names[s]) for s in order] + [(s, names[s] + ' (졸업)') for s in alumni]
    new_m = "_lab_members: &LAB_MEMBERS\n" + blk(members) + "\n"
    new_r = "_research_pages: &RESEARCH_PAGES\n" + blk(
        [(p, (titles.get(p, p))[:52]) for p in pages]) + "\n"

    out = re.sub(r'_lab_members: &LAB_MEMBERS\n(?:  - value:.*\n|    label:.*\n|  {4}label:.*\n)+',
                 new_m, src)
    out = re.sub(r'_research_pages: &RESEARCH_PAGES\n(?:  - value:.*\n|    label:.*\n|  {4}label:.*\n)+',
                 new_r, out)
    if out == src:
        print("  CMS 목록 변경 없음")
        return 0
    # 검증: YAML 이 파싱되고 항목 6개가 그대로 살아 있어야 한다
    try:
        import yaml
        d = yaml.safe_load(out)
        assert len(d['content']) == 6, "content 항목 수가 달라짐"
        for c in d['content']:
            if c['name'].startswith('pub-'):
                mf = [x for x in c['fields'] if x['name'] == 'members'][0]
                rf = [x for x in c['fields'] if x['name'] == 'research'][0]
                assert len(mf['options']['values']) == len(members)
                assert len(rf['options']['values']) == len(pages)
    except Exception as ex:
        print(f"  CMS 목록 동기화 취소 (검증 실패: {ex})", file=sys.stderr)
        return 0
    open('.pages.yml', 'w', encoding='utf-8').write(out)
    print(f"  CMS 목록 갱신: 구성원 {len(members)}명, 연구 페이지 {len(pages)}개")
    return 1


def main():
    order, alumni, names = people_from_members()
    pages, titles = research_page_ids()
    print("1) members 태그 자동 보완")
    a = auto_tag_members(names)
    print("2) CMS 선택 목록 동기화")
    b = sync_pages_yml(order, alumni, names, pages, titles)
    summary = f"members 태그 {a}건 보완, CMS 목록 {'갱신' if b else '변경 없음'}"
    print("\n" + summary)
    with open('/tmp/sync-summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary + "\n")


if __name__ == '__main__':
    main()
