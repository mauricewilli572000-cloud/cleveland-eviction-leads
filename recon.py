import json, re, urllib.parse
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:5000])
def main_part(t):
    m = re.search(r'<main.*?</main>|id="main-content".*?<footer|<div[^>]+(?:content-area|main-content|page-content)[^>]*>.*?<footer', t, re.S | re.I)
    return m.group(0) if m else t
for tag, u in [("public_access", "https://clevelandmunicipalcourt.org/public-access"), ("hc_docket", "https://www.clevelandhousingcourt.org/docket")]:
    r = S.get(u, timeout=45); t = r.text; mp = main_part(t)
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>", "", mp, flags=re.S)
    links = [(re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()[:70], urllib.parse.urljoin(str(r.url), m.group(1))) for m in re.finditer(r'href="([^"#]+)"[^>]*>(.*?)</a>', body, re.S)]
    show(tag, {"st": r.status_code, "text": re.sub(r"<[^>]+>|\s+", " ", body)[:2500], "links": links[:50], "iframes": re.findall(r'<iframe[^>]+src="([^"]+)"', t)})
