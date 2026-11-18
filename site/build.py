#!/usr/bin/env python3
"""lewiskim7.github.io 빌드: 포트폴리오 첫 화면(/) + 네이버 블로그 글 모음(/blog/).

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
:root{--bg:#fff;--fg:#1d1d1f;--sub:#6e6e73;--line:#e5e5ea;--accent:#03a94d}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#e8e8ed;--sub:#9a9aa0;--line:#2c2c2e;--accent:#3ccf7a}}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;max-width:760px;margin:0 auto;padding:32px 16px 48px;line-height:1.65;color:var(--fg);background:var(--bg)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:1.6em;margin:0 0 4px}h2{font-size:1.1em;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
ul{padding:0;margin:0}li{list-style:none;margin:0 0 18px}
.m{color:var(--sub);font-size:.85em}.p{color:var(--sub);font-size:.92em;margin:4px 0 0}
nav{font-size:.9em;margin-bottom:24px}nav a{margin-right:14px}
"""


def page(title: str, desc: str, body: str, canonical: str, extra_head: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
{extra_head}<style>{CSS}</style></head><body>
<nav><a href="{SITE}/">Lewis Kim</a><a href="{SITE}/blog/">블로그</a></nav>
{body}
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
    return (f'<li><a href="{SITE}/blog/posts/{p["log_no"]}.html">{e(p["title"])}</a>'
            f'<div class="m">{p["date"][:10]} · {e(p["category"])}</div>'
            f'<p class="p">{e(p["excerpt"])}</p></li>')


def build(posts: dict[str, dict]) -> None:
    (OUT / "blog" / "posts").mkdir(parents=True, exist_ok=True)
    items = sorted(posts.values(), key=lambda p: p["date"], reverse=True)

    for p in items:
        tags = " ".join(f"#{e(t)}" for t in p["tags"])
        body = (f'<p class="m"><a href="{SITE}/blog/">← 전체 글 목록</a></p>'
                f'<h1>{e(p["title"])}</h1><div class="m">{p["date"][:10]} · {e(p["category"])}</div>'
                f'<p>{e(p["excerpt"])}</p>'
                f'<p><a href="{naver_url(p["log_no"])}">네이버 블로그에서 전체 글 읽기 →</a></p>'
                f'<p class="m">{tags}</p>')
        jsonld = json.dumps({"@context": "https://schema.org", "@type": "BlogPosting",
                             "headline": p["title"], "datePublished": p["date"],
                             "url": naver_url(p["log_no"]), "description": p["excerpt"]},
                            ensure_ascii=False)
        (OUT / "blog" / "posts" / f'{p["log_no"]}.html').write_text(
            page(f'{p["title"]} | 루이스킴 블로그', p["excerpt"] or p["title"], body,
                 f'{SITE}/blog/posts/{p["log_no"]}.html',
                 f'<script type="application/ld+json">{jsonld}</script>\n'),
            encoding="utf-8")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    blog_body = (f'<h1>{e(CFG["blog_title"])}</h1><p>{e(CFG["blog_description"])}</p>'
                 f'<p><a href="https://m.blog.naver.com/{BLOG}">네이버 블로그 바로가기 →</a></p>'
                 f'<ul>{"".join(post_li(p) for p in items)}</ul>'
                 f'<p class="m">총 {len(items)}개 글 · 자동 갱신 {stamp} UTC</p>')
    (OUT / "blog" / "index.html").write_text(
        page(CFG["blog_title"], CFG["blog_description"], blog_body, f"{SITE}/blog/"), encoding="utf-8")

    projects = "".join(
        f'<li><a href="{e(p["url"])}">{e(p["name"])}</a>'
        + (f' · <a href="{e(p["code"])}">코드</a>' if p.get("code") else "")
        + f'<p class="p">{e(p["desc"])}</p></li>'
        for p in CFG["projects"])
    home_body = (f'<h1>{e(CFG["name"])}</h1><p class="m">{e(CFG["tagline"])}</p>'
                 f'<p>{e(CFG["intro"])}</p>'
                 f'<h2>프로젝트</h2><ul>{projects}</ul>'
                 f'<h2>최근 블로그 글</h2><ul>{"".join(post_li(p) for p in items[:5])}</ul>'
                 f'<p><a href="{SITE}/blog/">전체 글 {len(items)}개 보기 →</a></p>')
    (OUT / "index.html").write_text(
        page(CFG["site_title"], CFG["site_description"], home_body, f"{SITE}/", verification_meta()),
        encoding="utf-8")

    urls = [(f"{SITE}/", None), (f"{SITE}/blog/", items[0]["date"][:10] if items else None)]
    urls += [(f'{SITE}/blog/posts/{p["log_no"]}.html', p["date"][:10]) for p in items]
    sm = "".join(f"<url><loc>{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>" for u, d in urls)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n',
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")


def main() -> int:
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "posts.json"
    old = json.loads(data.read_text(encoding="utf-8")) if data.exists() else {}
    new = parse(fetch_rss(sys.argv[2] if len(sys.argv) > 2 else None))
    merged = {**old, **new}  # RSS는 최근 50개만 주므로 예전 글은 누적 보존
    data.write_text(json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    build(merged)
    print(f"posts total={len(merged)} from_rss={len(new)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
