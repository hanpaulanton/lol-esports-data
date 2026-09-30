import urllib.request
import re
import pathlib

UA = "LoLEsportsFanDataPolicyReview/0.1 (unofficial fan project; personal non-commercial; policy review only)"
OUT_DIR = pathlib.Path(r"C:\Users\sw486\Downloads\projectesprtsclndr\lol-esports-data\phase18nw-test")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        pathlib.Path(OUT_DIR / "http-requests.txt").open("a", encoding="utf-8").write(f"{url} -> {r.status}\n")
        return r.read().decode("utf-8", errors="replace")

html = get("https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EA%B8%B0%EB%B3%B8%EB%B0%A9%EC%B9%A8")
# find any anchor whose text/href mentions 약관/Terms
anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.S)
hits = []
for href, label in anchors:
    label_text = re.sub(r"<[^>]+>", " ", label)
    label_text = re.sub(r"\s+", " ", label_text).strip()
    if any(k in href for k in ("약관", "terms", "Terms", "TOS", "tos")) or any(
        k in label_text for k in ("약관", "Terms")
    ):
        hits.append((href, label_text))
out = ["=== anchors mentioning terms ==="]
for href, label in hits:
    out.append(f"href={href}  label={label!r}")
if not hits:
    out.append("(no anchors with terms found in the served HTML)")
pathlib.Path(OUT_DIR / "namu-terms-links.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
