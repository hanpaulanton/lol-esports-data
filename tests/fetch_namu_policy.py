import urllib.request
import re
import sys

UA = "LoLEsportsFanDataPolicyReview/0.1 (unofficial fan project; personal non-commercial; policy review only)"
OUT = r"C:\Users\sw486\Downloads\projectesprtsclndr\lol-esports-data\phase18nw-test\policy-extract.txt"
REQUEST_COUNT_FILE = r"C:\Users\sw486\Downloads\projectesprtsclndr\lol-esports-data\phase18nw-test\http-requests.txt"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return r.read().decode("utf-8", errors="replace")

def to_text(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)

def count_request(url, status):
    with open(REQUEST_COUNT_FILE, "a", encoding="utf-8") as handle:
        handle.write(f"{url} -> {status}\n")

def show(url, keywords, max_per_keyword=3, out=None):
    html = get(url)
    count_request(url, 200)
    text = to_text(html)
    lines = [f"== {url} STATUS=200 TEXTLEN={len(text)}"]
    for kw in keywords:
        matches = list(re.finditer(re.escape(kw), text, flags=re.IGNORECASE))
        if not matches:
            lines.append(f"--- [{kw}] NOT FOUND")
            continue
        lines.append(f"--- [{kw}] {len(matches)} occurrence(s); first {min(max_per_keyword, len(matches))}:")
        for m in matches[:max_per_keyword]:
            start = max(0, m.start() - 150)
            snippet = text[start : m.start() + 400]
            lines.append(f"    ...{snippet}...")
    (out or sys.stdout).write("\n".join(lines) + "\n\n")

if __name__ == "__main__":
    import pathlib
    out_dir = pathlib.Path(REQUEST_COUNT_FILE).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "policy-extract.txt"
    with open(out_path, "w", encoding="utf-8") as out:
        show(
            "https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EA%B8%B0%EB%B3%B8%EB%B0%A9%EC%B9%A8",
            ["봇", "API", "크롤", "자동화", "스크래핑", "비정상적인 방법", "접근", "CC BY-NC-SA"],
            out=out,
        )
        show(
            "https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EC%9D%B4%EC%9A%A9%EC%9E%90%20%EA%B4%80%EB%A6%AC%20%EB%B0%A9%EC%B9%A8",
            ["봇", "API", "무단", "크롤", "차단", "자동"],
            out=out,
        )
        show(
            "https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EB%B4%87%20%EB%AA%A9%EB%A1%9D",
            ["봇", "승인", "API"],
            out=out,
        )
    print(f"saved: {out_path}")
