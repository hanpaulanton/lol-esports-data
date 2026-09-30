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

html = get("https://namu.wiki/Search?q=%EC%9D%B4%EC%9A%A9%EC%95%BD%EA%B4%80")
text = re.sub(r"<[^>]+>", " ", html)
text = re.sub(r"\s+", " ", text)
print("STATUS=200 TEXTLEN=", len(text))
print(text[:1200])
paths = sorted(set(re.findall(r'href="(/w/[^"]{0,90})"', html)))
print("\n/w/ links on result page:")
for p in paths[:20]:
    print("  ", p)
