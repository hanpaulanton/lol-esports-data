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

# 1) search for the T1 team document name
search_html = get("https://namu.wiki/Search?q=" + urllib.request.quote("T1 프로게임단"))
paths = re.findall(r'href="(/w/[^"]{0,90})"', search_html)
print("search result paths (first 12):")
for p in paths[:12]:
    print("  ", p)

# 2) fetch the first plausible team document
target = next((p for p in paths if "T1" in urllib.request.unquote(p)), None)
if target:
    full = "https://namu.wiki" + target
    print("\nfetching:", full)
    html = get(full)
    text = to_text(html)
    print("DOC TEXTLEN=", len(text))
    keywords = [
        "전 팀명", "옛 팀명", "이전 팀명", "창단", "별칭", "약칭",
        "스폰서", "LCK", "챔피언스", "월드", "MSI", "우승", "로스터",
        "전적", "경기", "스코어", "BO",
    ]
    findings = {}
    for kw in keywords:
        m = re.search(re.escape(kw), text, flags=re.IGNORECASE)
        if m:
            start = max(0, m.start() - 80)
            findings[kw] = text[start : m.start() + 220]
        else:
            findings[kw] = "NOT FOUND"
    (pathlib.Path(OUT_DIR) / "namu-team-doc-t1.txt").write_text(
        "document: " + full + "\n\n" +
        "\n\n".join(f"[{k}]\n{v}" for k, v in findings.items()) + "\n\n" +
        "=== first 2500 chars ===\n" + text[:2500],
        encoding="utf-8",
    )
    print(f"saved: {OUT_DIR / 'namu-team-doc-t1.txt'}")
else:
    print("no team document found in search results")
