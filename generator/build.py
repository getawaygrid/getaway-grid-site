"""Turn data/channel.json + data/videos.json into a static site in _site/.

SITE_URL (env) is the public address, e.g. https://name.github.io/getaway-grid-site
The GitHub workflow fills it in automatically. Only stdlib.
"""
import html
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
CHANNEL = json.loads((ROOT / "data" / "channel.json").read_text(encoding="utf-8"))
VIDEOS = json.loads((ROOT / "data" / "videos.json").read_text(encoding="utf-8"))

SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")
BASE = urlparse(SITE_URL).path.rstrip("/")          # "" or "/repo-name"
NAME = CONFIG["site_name"]
CID = CHANNEL["id"]
CHANNEL_URL = f"https://www.youtube.com/channel/{CID}"
SUB_URL = CHANNEL_URL + "?sub_confirmation=1"
BUILD_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

LONG = [v for v in VIDEOS if not v["short"]]
SHORTS = [v for v in VIDEOS if v["short"]]
esc = html.escape


def u(path=""):
    """Site-internal link."""
    return f"{BASE}/{path}"


def absu(path=""):
    return f"{SITE_URL}/{path}"


def vpath(v):
    return f"v/{v['id']}/"


def fmt_date(iso):
    d = datetime.strptime(iso[:10], "%Y-%m-%d")
    return d.strftime("%b %d, %Y").replace(" 0", " ")


def fmt_dur(s):
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def iso_dur(s):
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"PT{h}H{m}M{sec}S"


def short_desc(v, n=155):
    text = re.sub(r"https?://\S+|#\w+", "", v["description"])
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = f"Watch {v['title']} on {NAME}."
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def thumb_hq(v):
    return f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"


def banner_url():
    b = CHANNEL.get("banner") or ""
    if b and "=" not in b.rsplit("/", 1)[-1]:
        b += "=w2120-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj"
    return b


# ---------- description → HTML (links, timestamps, hashtags) ----------
TOKEN = re.compile(
    r"(?P<url>https?://[^\s<>()\"']+[^\s<>()\"'.,;:!?])"
    r"|(?P<ts>(?<![\w:])(?:\d{1,2}:)?\d{1,2}:\d{2}(?![\w:]))"
    r"|(?P<tag>(?<![\w&])#[A-Za-z][\w]*)")


def ts_seconds(t):
    secs = 0
    for part in t.split(":"):
        secs = secs * 60 + int(part)
    return secs


def render_desc(text):
    out, pos = [], 0
    for m in TOKEN.finditer(text):
        out.append(esc(text[pos:m.start()]))
        tok = m.group(0)
        if m.group("url"):
            out.append(f'<a href="{esc(tok)}" target="_blank" rel="noopener nofollow">{esc(tok)}</a>')
        elif m.group("ts"):
            s = ts_seconds(tok)
            out.append(f'<a href="#t={s}" class="ts" data-t="{s}">{tok}</a>')
        else:
            out.append(f'<a href="https://www.youtube.com/hashtag/{quote(tok[1:].lower())}" '
                       f'target="_blank" rel="noopener">{esc(tok)}</a>')
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


CHAPTER_LINE = re.compile(r"^\s*[\[(]?((?:\d{1,2}:)?\d{1,2}:\d{2})[\])]?\s*[-–—:|]?\s*(.+?)\s*$")


def chapters(text):
    found = []
    for line in text.splitlines():
        m = CHAPTER_LINE.match(line)
        if m:
            found.append((ts_seconds(m.group(1)), m.group(1), m.group(2)))
    # YouTube's own rule: chapters start at 0:00 and there are at least 3.
    if len(found) >= 3 and found[0][0] == 0:
        return found
    return []


# ---------- page shell ----------
def page(path, title, desc, body, og_image=None, og_type="website", extra_head="", active=""):
    canonical = absu(path)
    og_image = og_image or absu("assets/og-default.jpg")
    full_title = title if title == NAME else f"{title} | {NAME}"

    def nav(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{u(href)}"{cur}>{label}</a>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#0b0614">
<meta property="og:site_name" content="{NAME}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{esc(og_image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{esc(og_image)}">
<link rel="icon" type="image/png" href="{u('assets/favicon.png')}">
<link rel="apple-touch-icon" href="{u('assets/apple-touch-icon.png')}">
<link rel="preconnect" href="https://i.ytimg.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;600;800&display=swap">
<link rel="stylesheet" href="{u('assets/style.css')}?v={BUILD_TIME[:13]}">
{extra_head}
</head>
<body>
<header class="top">
  <a class="brand" href="{u()}"><img src="{u('assets/gg.png')}" alt="" width="40" height="36"><span>{NAME}</span></a>
  <nav>{nav('', 'Home', 'home')}{nav('videos/', 'Videos', 'videos')}{nav('shorts/', 'Shorts', 'shorts')}{nav('about/', 'About', 'about')}</nav>
  <a class="btn sub small" href="{SUB_URL}" target="_blank" rel="noopener">Subscribe</a>
</header>
<main>
{body}
</main>
<footer>
  <img src="{u('assets/gg.png')}" alt="" width="32" height="29">
  <p>© {datetime.now(timezone.utc).year} {NAME} · <a href="{CHANNEL_URL}" target="_blank" rel="noopener">YouTube</a> · Fan-made channel, not affiliated with Rockstar Games or Take-Two.</p>
</footer>
<script src="{u('assets/app.js')}?v={BUILD_TIME[:13]}" defer></script>
</body>
</html>
"""


def card(v):
    if v["short"]:
        return f"""<a class="card short" href="{u(vpath(v))}">
  <div class="thumb"><img src="https://i.ytimg.com/vi/{v['id']}/oar2.jpg" onerror="this.onerror=null;this.src='{thumb_hq(v)}'" alt="" loading="lazy" width="270" height="480"></div>
  <h3>{esc(v['title'])}</h3>
</a>"""
    return f"""<a class="card" href="{u(vpath(v))}">
  <div class="thumb"><img src="{thumb_hq(v)}" alt="" loading="lazy" width="480" height="360"><span class="dur">{fmt_dur(v['duration'])}</span></div>
  <h3>{esc(v['title'])}</h3>
  <time datetime="{v['published']}">{fmt_date(v['published'])}</time>
</a>"""


def player(v, eager=False):
    cls = "player vertical" if v["short"] else "player"
    img = v["thumb"] if not v["short"] else f"https://i.ytimg.com/vi/{v['id']}/oar2.jpg"
    loading = "eager" if eager else "lazy"
    return f"""<div class="{cls}" data-id="{v['id']}">
  <img src="{esc(img)}" alt="{esc(v['title'])}" loading="{loading}" fetchpriority="{'high' if eager else 'auto'}">
  <button class="play" aria-label="Play {esc(v['title'])}"><svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.3.3 34 .3 34 .3s-21.3 0-26.5 1.4a8.5 8.5 0 0 0-6 6C.1 13 .1 24 .1 24s0 11 1.4 16.3a8.5 8.5 0 0 0 6 6C12.7 47.7 34 47.7 34 47.7s21.3 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.9 35 67.9 24 67.9 24s0-11-1.4-16.3z" fill="#FF2E88"/><path d="M45 24 27 14v20z" fill="#fff"/></svg></button>
</div>"""


def grid(vs, cls="grid"):
    return f'<div class="{cls}">' + "\n".join(card(v) for v in vs) + "</div>"


# ---------- pages ----------
def build_home():
    hero_bg = banner_url()
    style = f' style="--banner:url(\'{esc(hero_bg)}\')"' if hero_bg else ""
    latest = LONG[0] if LONG else (VIDEOS[0] if VIDEOS else None)
    parts = [f"""<section class="hero{' has-banner' if hero_bg else ''}"{style}>
  <div class="sun"></div><div class="gridfloor"></div>
  <div class="hero-in">
    <img class="logo" src="{u('assets/gg.png')}" alt="{NAME} logo" width="220" height="198">
    <h1>{NAME}</h1>
    <p class="tag">{esc(CONFIG['tagline'])}</p>
    <div class="cta">
      <a class="btn sub" href="{SUB_URL}" target="_blank" rel="noopener">Subscribe on YouTube</a>
      <a class="btn ghost" href="{u('videos/')}">All videos</a>
    </div>
  </div>
</section>"""]
    if latest:
        parts.append(f"""<section class="wrap latest">
  <h2 class="eyebrow">Latest video</h2>
  <div class="latest-row">
    {player(latest, eager=True)}
    <div class="latest-info">
      <h3><a href="{u(vpath(latest))}">{esc(latest['title'])}</a></h3>
      <time datetime="{latest['published']}">{fmt_date(latest['published'])}</time>
      <p>{esc(short_desc(latest, 260))}</p>
      <a class="btn ghost" href="{u(vpath(latest))}">Chapters &amp; details</a>
    </div>
  </div>
</section>""")
    more = [v for v in LONG if v is not latest][:6]
    if more:
        parts.append(f"""<section class="wrap"><div class="row-head"><h2>More videos</h2><a href="{u('videos/')}">See all →</a></div>{grid(more)}</section>""")
    if SHORTS:
        parts.append(f"""<section class="wrap"><div class="row-head"><h2>Shorts</h2><a href="{u('shorts/')}">See all →</a></div>{grid(SHORTS[:6], 'grid shorts')}</section>""")
    if not VIDEOS:
        parts.append('<section class="wrap"><p class="empty">First video coming soon.</p></section>')
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": absu(),
          "sameAs": [CHANNEL_URL]}
    write("", page("", NAME, CONFIG["tagline"], "\n".join(parts), active="home",
                   og_image=hero_bg or None,
                   extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>'))


def build_list(path, title, desc, vs, cls, key):
    body = f"""<section class="wrap"><h1 class="page-title">{title}</h1><p class="lede">{esc(desc)}</p>
{grid(vs, cls) if vs else '<p class="empty">Nothing here yet. Check back soon.</p>'}</section>"""
    write(path, page(path, title, desc, body, active=key))


def build_video(v):
    path = vpath(v)
    ch = chapters(v["description"])
    chap_html = ""
    if ch:
        items = "".join(f'<li><a href="#t={s}" class="ts" data-t="{s}"><span>{t}</span>{esc(name)}</a></li>'
                        for s, t, name in ch)
        chap_html = f'<details class="chapters" open><summary>Chapters</summary><ol>{items}</ol></details>'
    pool = SHORTS if v["short"] else LONG
    related = [x for x in pool if x["id"] != v["id"]][:6]
    rel_html = ""
    if related:
        rel_html = f'<section class="related"><h2>{"More Shorts" if v["short"] else "More videos"}</h2>{grid(related, "grid shorts" if v["short"] else "grid")}</section>'
    body = f"""<article class="wrap video{' is-short' if v['short'] else ''}">
  {player(v, eager=True)}
  <div class="meta">
    <h1>{esc(v['title'])}</h1>
    <p class="sub-line"><time datetime="{v['published']}">{fmt_date(v['published'])}</time> · {fmt_dur(v['duration'])}
      · <a href="https://www.youtube.com/watch?v={v['id']}" target="_blank" rel="noopener">Watch on YouTube</a></p>
    <a class="btn sub" href="{SUB_URL}" target="_blank" rel="noopener">Subscribe</a>
  </div>
  {chap_html}
  <div class="desc">{render_desc(v['description'])}</div>
  {rel_html}
</article>"""
    ld = {"@context": "https://schema.org", "@type": "VideoObject", "name": v["title"],
          "description": short_desc(v, 500), "thumbnailUrl": [v["thumb"]],
          "uploadDate": v["published"], "duration": iso_dur(v["duration"]),
          "embedUrl": f"https://www.youtube.com/embed/{v['id']}",
          "contentUrl": f"https://www.youtube.com/watch?v={v['id']}"}
    extra = (f'<meta property="og:video" content="https://www.youtube.com/embed/{v["id"]}">'
             f'<meta property="article:published_time" content="{v["published"]}">'
             f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    write(path, page(path, v["title"], short_desc(v), body, og_image=v["thumb"],
                     og_type="video.other", extra_head=extra,
                     active="shorts" if v["short"] else "videos"))


def build_about():
    paras = "".join(f"<p>{esc(p)}</p>" for p in CONFIG["about"])
    avatar = CHANNEL.get("avatar")
    av = f'<img class="avatar" src="{esc(avatar)}" alt="{NAME} channel avatar" width="160" height="160">' if avatar else ""
    body = f"""<section class="wrap about">
  <div class="about-head">{av}<div><h1 class="page-title">About {NAME}</h1>
  <p class="lede">{len(LONG)} videos · {len(SHORTS)} Shorts</p></div></div>
  {paras}
  <div class="cta"><a class="btn sub" href="{SUB_URL}" target="_blank" rel="noopener">Subscribe on YouTube</a>
  <a class="btn ghost" href="{CHANNEL_URL}" target="_blank" rel="noopener">Open the channel</a></div>
</section>"""
    write("about/", page("about/", f"About {NAME}", CONFIG["about"][0][:155], body, active="about"))


def build_404():
    body = f"""<section class="wrap notfound"><h1 class="page-title">Wrong turn</h1>
<p class="lede">That page doesn't exist. Maybe the video moved.</p>
<a class="btn sub" href="{u()}">Back to the home page</a></section>"""
    (OUT / "404.html").write_text(page("404.html", "Page not found", "Page not found", body), encoding="utf-8")


def build_seo_files():
    urls = ["", "videos/", "shorts/", "about/"] + [vpath(v) for v in VIDEOS]
    lastmod = {vpath(v): v["published"][:10] for v in VIDEOS}
    items = "".join(f"<url><loc>{absu(p)}</loc>" + (f"<lastmod>{lastmod[p]}</lastmod>" if p in lastmod else "") + "</url>"
                    for p in urls)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>',
        encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {absu('sitemap.xml')}\n", encoding="utf-8")
    domain = os.environ.get("CUSTOM_DOMAIN", "").strip()
    if domain:
        (OUT / "CNAME").write_text(domain + "\n", encoding="utf-8")


def write(path, content):
    target = OUT / path / "index.html" if not path.endswith(".html") else OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    build_home()
    build_list("videos/", "All videos", f"Every {NAME} deep dive, newest first.", LONG, "grid", "videos")
    build_list("shorts/", "Shorts", f"Quick {NAME} Shorts, newest first.", SHORTS, "grid shorts", "shorts")
    for v in VIDEOS:
        build_video(v)
    build_about()
    build_404()
    build_seo_files()
    print(f"Built {len(VIDEOS) + 5} pages into _site/ for {SITE_URL}")


if __name__ == "__main__":
    main()
