"""Fetch the PUBLIC videos of the Getaway Grid channel with the YouTube Data API v3.

Needs one environment variable: YT_API_KEY (a read-only API key, stored as a
GitHub secret). It never uses OAuth tokens and never sees private videos.

Writes data/channel.json and data/videos.json. Only stdlib, no pip installs.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
API = "https://www.googleapis.com/youtube/v3/"
SHORT_MAX_SECONDS = 180  # YouTube allows Shorts up to 3 minutes


def api(endpoint, **params):
    key = os.environ.get("YT_API_KEY", "").strip()
    if not key:
        sys.exit("ERROR: the YT_API_KEY secret is missing. Add it under the repo's "
                 "Settings > Secrets and variables > Actions.")
    params["key"] = key
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # Print the API's reason, but never the URL (it contains the key).
        try:
            reason = json.load(e)["error"]["message"]
        except Exception:
            reason = str(e.code)
        sys.exit(f"ERROR: YouTube API call '{endpoint}' failed: {reason}")


def iso_duration_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    days, h, mins, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mins * 60 + s


def is_shorts_url(video_id):
    """YouTube serves /shorts/ID with 200 for Shorts and redirects (303) for normal videos."""
    req = urllib.request.Request(
        f"https://www.youtube.com/shorts/{video_id}", method="HEAD",
        headers={"User-Agent": "Mozilla/5.0 (site-builder)"})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=15) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and "/watch" in (e.headers.get("Location") or ""):
            return False
        return None  # consent page, rate limit...: unknown
    except Exception:
        return None


def best_thumb(thumbs):
    for k in ("maxres", "standard", "high", "medium", "default"):
        if k in thumbs:
            return thumbs[k]["url"]
    return ""


def main():
    cid = CONFIG["channel_id"]
    ch = api("channels", part="snippet,contentDetails,brandingSettings,statistics", id=cid)
    if not ch.get("items"):
        sys.exit(f"ERROR: channel {cid} not found")
    ch = ch["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while True:
        p = dict(part="contentDetails", playlistId=uploads, maxResults=50)
        if token:
            p["pageToken"] = token
        page = api("playlistItems", **p)
        ids += [it["contentDetails"]["videoId"] for it in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token:
            break

    videos = []
    for i in range(0, len(ids), 50):
        batch = api("videos", part="snippet,contentDetails,status,player",
                    id=",".join(ids[i:i + 50]), maxWidth=480)
        for v in batch.get("items", []):
            st, sn = v.get("status", {}), v["snippet"]
            # The rule: only PUBLIC videos, never private / unlisted / scheduled / upcoming.
            if st.get("privacyStatus") != "public":
                continue
            if st.get("uploadStatus") not in (None, "processed"):
                continue
            if sn.get("liveBroadcastContent") in ("upcoming", "live"):
                continue
            secs = iso_duration_seconds(v["contentDetails"].get("duration"))
            pl = v.get("player", {})
            w, h = int(pl.get("embedWidth") or 16), int(pl.get("embedHeight") or 9)
            vertical = h >= w  # Shorts are always vertical or square
            short = False
            if 0 < secs <= SHORT_MAX_SECONDS:
                # Two signals: the player shape from the API, and youtube.com/shorts/ID answering directly.
                short = vertical or is_shorts_url(v["id"]) is True
            videos.append({
                "id": v["id"],
                "title": sn["title"],
                "description": sn.get("description", ""),
                "published": sn["publishedAt"],
                "duration": secs,
                "thumb": best_thumb(sn.get("thumbnails", {})),
                "tags": sn.get("tags", [])[:15],
                "short": short,
                "vertical": vertical,
            })

    videos.sort(key=lambda x: x["published"], reverse=True)
    b = ch.get("brandingSettings", {})
    channel = {
        "id": cid,
        "title": ch["snippet"]["title"],
        "description": ch["snippet"].get("description", ""),
        "handle": ch["snippet"].get("customUrl", ""),
        "avatar": best_thumb(ch["snippet"].get("thumbnails", {})),
        "banner": b.get("image", {}).get("bannerExternalUrl", ""),
    }
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    (out / "channel.json").write_text(json.dumps(channel, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "videos.json").write_text(json.dumps(videos, indent=1, ensure_ascii=False), encoding="utf-8")
    longs = sum(not v["short"] for v in videos)
    print(f"OK: {len(videos)} public videos ({longs} long, {len(videos) - longs} Shorts)")


if __name__ == "__main__":
    main()
