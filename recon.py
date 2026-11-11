import json, re, urllib.parse
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:4500])
KEY = re.compile(r"case|record|search|docket|public|access|eservice|clerk|eviction|housing", re.I)
def page(tag, u):
    try:
        r = S.get(u, timeout=45); t = r.text
    except Exception as e:
        show(tag, str(e)); return ""
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    links = [(re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()[:60], urllib.parse.urljoin(str(r.url), m.group(1))) for m in re.finditer(r'href="([^"#]+)"[^>]*>(.*?)</a>', t, re.S)]
    show(tag, {"st": r.status_code, "url": str(r.url), "captcha": bool(re.search(r"captcha|recaptcha|hcaptcha|turnstile|cf-chl", t, re.I)),
               "forms": re.findall(r"<form[^>]*>", t)[:5], "links": [l for l in links if KEY.search(l[0] + l[1])][:40],
               "text": re.sub(r"<[^>]+>|\s+", " ", body)[:700]})
    return t
page("cmc_home", "https://clevelandmunicipalcourt.org/")
page("cmc_records", "https://clevelandmunicipalcourt.org/clerk-of-courts/court-records")
page("housing", "https://clevelandmunicipalcourt.org/housing-court")
for u in ["https://eservices.clevelandmunicipalcourt.org/", "https://clevelandmunicipalcourt.org/public-access",
          "https://portal.clevelandmunicipalcourt.org/", "https://clevelandmunicipalcourt.org/clerk-of-courts/case-information"]:
    page(u, u)
