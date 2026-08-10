#!/usr/bin/env python3
"""저장소에 올라온 사진을 용도별 규칙으로 줄인다. GitHub Actions 에서 자동 실행된다.

원칙
 - 사진은 JPEG. 화면 표시 크기의 2배(레티나)까지만 줄인다.
 - 도표와 로고는 PNG 유지. 글자가 번지지 않게 하고 투명도를 지킨다.
 - 알파 채널이 있어도 전부 불투명하면 사진으로 보고 JPEG 로 바꾼다.
 - 줄인 결과가 원본보다 크면 원본을 그대로 둔다.
 - 휴대폰 사진은 회전을 픽셀이 아니라 EXIF 에 담는다. 다시 저장하면 EXIF 가 사라져
   사진이 뒤집혀 보인다. 그래서 저장 전에 회전을 픽셀에 구워 넣는다.

확장자가 png 에서 jpg 로 바뀌면 참조하는 파일(json, html)도 함께 고친다.
"""
import os, sys, glob, json, re
from PIL import Image, ImageOps

# (경로 접두어, 최대 긴변, JPEG 품질, PNG 유지 여부)
RULES = [
    ("Photos/brand",          None, None, True),   # 로고. 손대지 않는다
    ("Photos/research-figs",  1800,   90, True),   # 도표. 작은 글자가 있다
    ("Photos/projects",       1200,   90, True),   # 도표
    ("Photos/backgrounds",    2560,   85, False),  # 전체화면 배경
    ("Photos/research",       1800,   85, False),
    ("Photos/members",         600,   88, False),  # 화면 표시 88~200px
    ("Photos/_archive",       1200,   85, False),
    ("News_Blog_JPG",         2000,   85, False),
]
EXT = (".jpg", ".jpeg", ".png")

# 이미 최적화된 파일을 매번 다시 인코딩하면 커밋만 늘고 화질이 조금씩 나빠진다.
# 확장자가 바뀌지 않는 경우에는 아래 두 조건을 모두 넘길 때만 다시 저장한다.
MIN_GAIN_RATIO = 0.15     # 15% 이상 줄어야 한다
MIN_GAIN_BYTES = 40 * 1024
REFERRERS = [
    "index.html", "css/styles.css", "js/app.js", "members.json",
    "research-content/research.json",
    "News_Blog_JPG/beelab_content/news.json",
    "News_Blog_JPG/beelab_content/blog.json",
]


def rule_for(path):
    for pre, w, q, keep in RULES:
        if path.startswith(pre):
            return w, q, keep
    return 2000, 85, False


def uses_alpha(im):
    """실제로 투명 픽셀을 쓰는가. 알파가 있어도 전부 불투명이면 False."""
    if im.mode == "P":
        if "transparency" not in im.info:
            return False
        im = im.convert("RGBA")
    if im.mode not in ("RGBA", "LA"):
        return False
    lo, _ = im.getchannel("A").getextrema()
    return lo < 250


def upright(im):
    """EXIF 회전 정보를 픽셀에 반영한다.

    다시 저장하면 EXIF 가 날아가므로, 그 전에 실제로 돌려 놓아야 한다.
    이걸 빠뜨려서 세로 사진 4장과 뒤집힌 사진 2장이 잘못 표시된 적이 있다.
    """
    try:
        return ImageOps.exif_transpose(im)
    except Exception:
        return im


def fit(im, maxw):
    if maxw and max(im.size) > maxw:
        r = maxw / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    return im


def save_png(im, dst, maxw):
    im = fit(upright(im), maxw)
    best, bestsize = None, None
    for cand in ("quant", "plain"):
        tmp = dst + "." + cand
        try:
            if cand == "quant":
                im.convert("RGBA").quantize(colors=256, method=Image.FASTOCTREE).save(
                    tmp, "PNG", optimize=True)
            else:
                im.save(tmp, "PNG", optimize=True)
        except Exception:
            continue
        s = os.path.getsize(tmp)
        if bestsize is None or s < bestsize:
            if best:
                os.remove(best)
            best, bestsize = tmp, s
        else:
            os.remove(tmp)
    if not best:
        raise RuntimeError("png 저장 실패")
    os.replace(best, dst)
    return bestsize


def save_jpeg(im, dst, maxw, q):
    im = upright(im)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.getchannel("A"))
        im = bg
    else:
        im = im.convert("RGB")
    im = fit(im, maxw)
    im.save(dst, "JPEG", quality=q, optimize=True, progressive=True, subsampling=1)
    return os.path.getsize(dst)


def update_refs(renames):
    """확장자가 바뀐 파일을 가리키던 참조를 고친다."""
    n = 0
    for t in REFERRERS:
        if not os.path.exists(t):
            continue
        s = open(t, encoding="utf-8").read()
        orig = s
        for old, new in renames.items():
            s = s.replace(old, new)
            eo, en = json.dumps(old)[1:-1], json.dumps(new)[1:-1]
            if eo != old:
                s = s.replace(eo, en)
        if s != orig:
            open(t, "w", encoding="utf-8").write(s)
            n += 1
    return n


def main():
    files = []
    for pat in ("Photos/**/*", "News_Blog_JPG/**/*"):
        for p in glob.glob(pat, recursive=True):
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in EXT:
                files.append(p)

    renames, before, after, done = {}, 0, 0, 0
    for p in sorted(files):
        maxw, q, keep_png = rule_for(p)
        osz = os.path.getsize(p)
        before += osz
        if maxw is None:
            after += osz
            continue
        try:
            im = Image.open(p)
            to_png = keep_png or uses_alpha(im)
            dst = os.path.splitext(p)[0] + (".png" if to_png else ".jpg")
            tmp = dst + ".tmp"
            nsz = save_png(im, tmp, maxw) if to_png else save_jpeg(im, tmp, maxw, q)
        except Exception as e:
            print(f"  건너뜀 {p}: {e}", file=sys.stderr)
            after += osz
            continue
        # 확장자가 그대로면 이득이 뚜렷할 때만 교체한다. 그래야 재실행해도 커밋이 안 생긴다.
        gain = osz - nsz
        # 회전 정보가 있는 사진은 이득이 작아도 반드시 다시 저장한다.
        # 안 그러면 EXIF 만 믿고 있던 사진이 계속 뒤집힌 채로 남는다.
        rotated = False
        try:
            rotated = Image.open(p).getexif().get(274, 1) not in (0, 1)
        except Exception:
            pass
        enough = (dst != p) or rotated or (gain >= MIN_GAIN_BYTES and gain / osz >= MIN_GAIN_RATIO)
        if nsz >= osz or not enough:
            os.remove(tmp)
            after += osz
            continue
        os.replace(tmp, dst)
        if dst != p:
            os.remove(p)
            renames[p] = dst
        after += nsz
        done += 1

    changed = update_refs(renames) if renames else 0
    saved = (before - after) / 1048576
    summary = (f"{done}장 최적화, {saved:.1f}MB 절감 "
               f"({before/1048576:.0f}MB -> {after/1048576:.0f}MB)")
    if renames:
        summary += f", 확장자 변경 {len(renames)}건, 참조 갱신 {changed}개 파일"
    print(summary)
    with open("/tmp/optimize-summary.txt", "w", encoding="utf-8") as f:
        f.write(summary + "\n")


if __name__ == "__main__":
    main()
