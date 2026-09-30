import urllib.request
import re
import pathlib

UA = "LoLEsportsFanDataPolicyReview/0.1 (unofficial fan project; personal non-commercial; policy review only)"
OUT_DIR = pathlib.Path(r"C:\Users\sw486\Downloads\projectesprtsclndr\lol-esports-data\phase18nw-test")
REQ_LOG = OUT_DIR / "http-requests.txt"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        pathlib.Path(REQ_LOG).open("a", encoding="utf-8").write(f"{url} -> {r.status}\n")
        return r.read().decode("utf-8", errors="replace")

def to_text(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)

out_lines = []

# 1) find footer links (terms/privacy) on the basic policy page
html = get("https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EA%B8%B0%EB%B3%B8%EB%B0%A9%EC%B9%A8")
anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.S)
footer_hits = []
for href, label in anchors:
    label_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", label)).strip()
    if any(k in (href + label_text) for k in ("Terminos", "uso", "privacidad", "Privacidad")):
        footer_hits.append((href, label_text))
out_lines.append("=== footer policy links ===")
for href, label in footer_hits:
    out_lines.append(f"href={href}  label={label!r}")

# 2) fetch the terms page if a concrete URL was found
terms_url = next((href for href, _ in footer_hits if href.startswith("http") or href.startswith("/")), None)
if terms_url:
    if terms_url.startswith("/"):
        terms_url = "https://namu.wiki" + terms_url
    out_lines.append(f"=== fetching {terms_url} ===")
    try:
        thtml = get(terms_url)
        ttext = to_text(thtml)
        out_lines.append(f"STATUS=200 TEXTLEN={len(ttext)}")
        idx = ttext.find("Términos", 2000)  # skip nav
        if idx == -1:
            idx = 0
        out_lines.append(ttext[idx : idx + 1800])
        keywords = ["자동", "크롤", "스크래핑", "API", "수집", "data mining", " scraping"]
        for kw in keywords:
            m = re.search(re.escape(kw), ttext, flags=re.IGNORECASE)
            if m:
                start = max(0, m.start() - 150)
                out_lines.append(f"--- [{kw}] ...{ttext[start:m.start()+300]}...")
            else:
                out_lines.append(f"--- [{kw}] NOT FOUND")
    except Exception as exc:  # noqa: BLE001
        out_lines.append(f"TERMS FETCH FAILED: {exc}")
else:
    out_lines.append("no footer terms link found")

pathlib.Path(OUT_DIR / "namu-terms.txt").write_text("\n".join(out_lines), encoding="utf-8")
print(f"saved: {OUT_DIR / 'namu-terms.txt'}")
