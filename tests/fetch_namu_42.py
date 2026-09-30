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

def section_between(text, start_kw, end_kw, limit=2200):
    start = text.find(start_kw)
    if start == -1:
        return f"[{start_kw}] NOT FOUND"
    end = text.find(end_kw, start + len(start_kw))
    if end == -1:
        end = start + limit
    return text[start : min(end, start + limit)]

def links(html):
    return re.findall(r'href="(/w/[^"]+)"', html)

out = []
# 1) 이용자 관리 방침: 4.2.1 봇 사용 승인 본문
html = get("https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EC%9D%B4%EC%9A%A9%EC%9E%90%20%EA%B4%80%EB%A6%AC%20%EB%B0%A9%EC%B9%A8")
text = to_text(html)
out.append("=== 4.2.1 봇 사용 승인 (이용자 관리 방침) ===")
out.append(section_between(text, "4.2.1. 봇 사용 승인", "4.2.2.", 2000))

# 2) 기본방침 HTML에서 이용약관/robots 관련 링크 찾기
html2 = get("https://namu.wiki/w/%EB%82%98%EB%AC%B4%EC%9C%84%ED%82%A4:%EA%B8%B0%EB%B3%B8%EB%B0%A9%EC%B9%A8")
out.append("=== links on 기본방침 page (terms/약관 related) ===")
found = sorted({l for l in links(html2) if any(k in l for k in ("약관", "Terms", "terms", "policies", "이용"))})
out.append("\n".join(found) if found else "(no terms-related /w/ links found)")
out.append("=== all footer-ish links sample ===")
out.append("\n".join(sorted({l for l in links(html2)})[:40]))

pathlib.Path(OUT_DIR / "namu-policy-42.txt").write_text("\n".join(out), encoding="utf-8")
print(f"saved: {OUT_DIR / 'namu-policy-42.txt'}")
