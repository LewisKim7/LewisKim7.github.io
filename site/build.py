#!/usr/bin/env python3
"""lewiskim7.github.io 빌드: 네이버 '루이스킴 블로그' 글 모음(/ = 전체 목록, /blog/posts/<번호>.html = 글별 요약).

네이버 PC 글 주소는 noindex라 구글에 잘 안 잡힌다. 이 사이트는 우리 소유라
서치콘솔·서치어드바이저·Bing에 등록할 수 있고, 각 글 페이지가 색인 허용되는
모바일 주소(m.blog.naver.com)로 연결해 검색엔진이 원문을 찾아가게 한다.

사용: python3 build.py [posts.json 경로] [RSS 파일(선택, 없으면 네이버에서 받음)]
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
BLOG = CFG["blog_id"]
SITE = CFG["site_url"].rstrip("/")
BLOG_HOME = f"https://m.blog.naver.com/{BLOG}"
OUT = HERE.parent / "_site"
e = html.escape


def fetch_rss(src: str | None) -> str:
    if src:
        return Path(src).read_text(encoding="utf-8")
    req = urllib.request.Request(
        f"https://rss.blog.naver.com/{BLOG}.xml",
        headers={"User-Agent": "Mozilla/5.0 (blog-archive; GitHub Actions)"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def clean(text: str, limit: int = 160) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def parse(xml_text: str) -> dict[str, dict]:
    posts = {}
    for it in ET.fromstring(xml_text).iter("item"):
        guid = (it.findtext("guid") or it.findtext("link") or "").strip()
        m = re.search(r"/(\d{6,})", guid)
        if not m:
            continue
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            dt = datetime.now(timezone.utc)
        posts[m.group(1)] = {
            "log_no": m.group(1),
            "title": (it.findtext("title") or "").strip(),
            "category": (it.findtext("category") or "").strip(),
            "date": dt.isoformat(),
            "excerpt": clean(it.findtext("description") or ""),
            "tags": [t.strip() for t in (it.findtext("tag") or "").split(",") if t.strip()][:10],
        }
    return posts


def naver_url(log_no: str) -> str:
    return f"https://m.blog.naver.com/{BLOG}/{log_no}"  # 모바일 주소 = 색인 허용


CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--chip:#f2f2f5;--accent:#03a94d}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#e8e8ed;--sub:#9a9aa0;--line:#2c2c2e;--chip:#1e1e20;--accent:#3ccf7a}}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;max-width:760px;margin:0 auto;padding:28px 16px 48px;line-height:1.65;color:var(--fg);background:var(--bg);word-break:keep-all;overflow-wrap:anywhere}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{margin-bottom:8px}header .brand{font-weight:700;color:var(--fg);font-size:1.05em}
h1{font-size:1.55em;line-height:1.35;margin:18px 0 6px}
.lead{color:var(--sub);margin:0 0 14px}
.cats{display:flex;flex-wrap:wrap;gap:6px;margin:18px 0 22px;padding:0}
.cats button{border:1px solid var(--line);background:var(--chip);color:var(--fg);border-radius:999px;padding:4px 12px;font:inherit;font-size:.85em;cursor:pointer}
.cats button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:#fff}
ul.posts{padding:0;margin:0;border-top:1px solid var(--line)}
ul.posts li{list-style:none;padding:16px 0;border-bottom:1px solid var(--line)}
ul.posts li a.t{font-weight:600;color:var(--fg);font-size:1.02em}
.m{color:var(--sub);font-size:.84em}.p{color:var(--sub);font-size:.92em;margin:4px 0 0}
.cta{display:inline-block;margin:10px 0;padding:8px 16px;border-radius:8px;background:var(--accent);color:#fff;font-weight:600}
.cta:hover{text-decoration:none;opacity:.9}
footer{margin-top:32px;color:var(--sub);font-size:.82em}
"""

FILTER_JS = """<script>
(function(){var bs=document.querySelectorAll('.cats button'),li=document.querySelectorAll('ul.posts li');
bs.forEach(function(b){b.addEventListener('click',function(){var c=b.dataset.c;
bs.forEach(function(x){x.setAttribute('aria-pressed',x===b)});
li.forEach(function(l){l.hidden=!!c&&l.dataset.c!==c})})})})();
</script>"""


def page(title: str, desc: str, body: str, canonical: str, extra_head: str = "", og_type: str = "website") -> str:
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{e(CFG["blog_name"])}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}"><meta property="og:locale" content="ko_KR">
<link rel="alternate" type="application/rss+xml" title="{e(CFG["blog_name"])}" href="https://rss.blog.naver.com/{BLOG}.xml">
{extra_head}<style>{CSS}</style></head><body>
<header><a class="brand" href="{SITE}/">{e(CFG["blog_name"])}</a></header>
{body}
<footer>© {e(CFG["author"])} · 모든 글의 원문은 <a href="{BLOG_HOME}">네이버 블로그</a>에 있습니다.</footer>
</body></html>
"""


def verification_meta() -> str:
    out = ""
    for key, name in (("google_site_verification", "google-site-verification"),
                      ("naver_site_verification", "naver-site-verification"),
                      ("bing_site_verification", "msvalidate.01")):
        if CFG.get(key):
            out += f'<meta name="{name}" content="{e(CFG[key])}">\n'
    return out


def post_li(p: dict) -> str:
    return (f'<li data-c="{e(p["category"])}"><a class="t" href="{SITE}/blog/posts/{p["log_no"]}.html">{e(p["title"])}</a>'
            f'<div class="m">{p["date"][:10]} · {e(p["category"])}</div>'
            f'<p class="p">{e(p["excerpt"])}</p></li>')


def build(posts: dict[str, dict]) -> None:
    (OUT / "blog" / "posts").mkdir(parents=True, exist_ok=True)
    items = sorted(posts.values(), key=lambda p: p["date"], reverse=True)

    for p in items:
        tags = " ".join(f"#{e(t)}" for t in p["tags"])
        body = (f'<p class="m"><a href="{SITE}/">← 전체 글</a></p>'
                f'<h1>{e(p["title"])}</h1><div class="m">{p["date"][:10]} · {e(p["category"])}</div>'
                f'<p>{e(p["excerpt"])}</p>'
                f'<a class="cta" href="{naver_url(p["log_no"])}">네이버 블로그에서 전체 글 읽기 →</a>'
                f'<p class="m">{tags}</p>')
        jsonld = json.dumps({"@context": "https://schema.org", "@type": "BlogPosting",
                             "headline": p["title"], "datePublished": p["date"],
                             "author": {"@type": "Person", "name": CFG["author"]},
                             "mainEntityOfPage": naver_url(p["log_no"]),
                             "url": naver_url(p["log_no"]), "description": p["excerpt"]},
                            ensure_ascii=False)
        (OUT / "blog" / "posts" / f'{p["log_no"]}.html').write_text(
            page(f'{p["title"]} | {CFG["blog_name"]}', p["excerpt"] or p["title"], body,
                 f'{SITE}/blog/posts/{p["log_no"]}.html',
                 f'<script type="application/ld+json">{jsonld}</script>\n', "article"),
            encoding="utf-8")

    counts: dict[str, int] = {}
    for p in items:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    chips = (f'<button type="button" data-c="" aria-pressed="true">전체 {len(items)}</button>'
             + "".join(f'<button type="button" data-c="{e(c)}" aria-pressed="false">{e(c)} {n}</button>'
                       for c, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])) if c))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    home_body = (f'<h1>{e(CFG["blog_tagline"])}</h1>'
                 f'<p class="lead">{e(CFG["site_description"])}</p>'
                 f'<a class="cta" href="{BLOG_HOME}">네이버 블로그 바로가기 →</a>'
                 f'<div class="cats" role="group" aria-label="카테고리">{chips}</div>'
                 f'<ul class="posts">{"".join(post_li(p) for p in items)}</ul>'
                 f'<p class="m">총 {len(items)}개 글 · {stamp} 기준 자동 갱신</p>{FILTER_JS}')
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Blog", "name": CFG["blog_name"],
                         "url": f"{SITE}/", "description": CFG["site_description"], "inLanguage": "ko",
                         "author": {"@type": "Person", "name": CFG["author"]}, "sameAs": [BLOG_HOME]},
                        ensure_ascii=False)
    (OUT / "index.html").write_text(
        page(CFG["site_title"], CFG["site_description"], home_body, f"{SITE}/",
             verification_meta() + f'<script type="application/ld+json">{jsonld}</script>\n'),
        encoding="utf-8")
    # 예전 /blog/ 주소는 첫 화면으로 보낸다(검색엔진에 이미 알린 주소 보존)
    (OUT / "blog" / "index.html").write_text(
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{e(CFG["blog_name"])}</title>'
        f'<link rel="canonical" href="{SITE}/"><meta http-equiv="refresh" content="0; url={SITE}/">'
        f'</head><body><a href="{SITE}/">{e(CFG["blog_name"])}</a></body></html>\n', encoding="utf-8")

    urls = [(f"{SITE}/", items[0]["date"][:10] if items else None)]
    urls += [(f'{SITE}/blog/posts/{p["log_no"]}.html', p["date"][:10]) for p in items]
    sm = "".join(f"<url><loc>{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>" for u, d in urls)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n',
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    if CFG.get("indexnow_key"):  # IndexNow(Bing·네이버 등) 소유 확인용 공개 키 파일
        (OUT / f'{CFG["indexnow_key"]}.txt').write_text(CFG["indexnow_key"], encoding="utf-8")


def main() -> int:
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "posts.json"
    old = json.loads(data.read_text(encoding="utf-8")) if data.exists() else {}
    new = parse(fetch_rss(sys.argv[2] if len(sys.argv) > 2 else None))
    merged = {**old, **new}  # RSS는 최근 50개만 주므로 예전 글은 누적 보존
    data.write_text(json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    build(merged)
    # IndexNow로 알릴 주소: 새 글만(전체 재알림은 INDEXNOW_ALL=1)
    import os
    ids = merged if os.environ.get("INDEXNOW_ALL") == "1" else {k: v for k, v in new.items() if k not in old}
    urls = ([f"{SITE}/"] if ids else []) + [f"{SITE}/blog/posts/{k}.html" for k in ids]
    (HERE.parent / "indexnow_urls.json").write_text(json.dumps(urls), encoding="utf-8")
    print(f"indexnow urls={len(urls)}")
    print(f"posts total={len(merged)} from_rss={len(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
