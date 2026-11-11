import json, re, io
from curl_cffi import requests as cr
S = cr.Session(impersonate="chrome")
def show(tag, obj): print(f"@@{tag}@@ " + json.dumps(obj, default=str)[:6000])
r = S.get("https://www.clevelandhousingcourt.org/accessible-civil-docket", timeout=60); t = r.text
rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
cells = [[re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)] for row in rows]
show("civil_docket", {"st": r.status_code, "rows": len(rows), "first": cells[:12], "text": re.sub(r"<script.*?</script>|<[^>]+>|\s+", " ", t)[2000:4500]})
r = S.get("https://www.clevelandhousingcourt.org/sites/default/files/Criminal%20Cases%20Filed%20Report.xlsx", timeout=60)
try:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True)
    ws = wb.worksheets[0]; rr = [[str(c) if c is not None else "" for c in row] for row in ws.iter_rows(values_only=True)]
    show("criminal_filed", {"st": r.status_code, "n": len(rr), "head": rr[:8]})
except Exception as e:
    show("criminal_filed_err", [r.status_code, str(e), r.content[:200].decode("latin-1")])
r = S.get("https://portal-ohcleveland.tylertech.cloud/CMCPORTAL/", timeout=60); t = r.text
show("tyler", {"st": r.status_code, "captcha": bool(re.search(r"recaptcha|captcha|hcaptcha", t, re.I)), "links": re.findall(r'href="([^"]+)"', t)[:30]})
r = S.get("https://portal-ohcleveland.tylertech.cloud/CMCPORTAL/Home/Dashboard/29", timeout=60); t = r.text
show("tyler_search", {"st": r.status_code, "captcha": bool(re.search(r"recaptcha|captcha|hcaptcha", t, re.I)), "snip": re.sub(r"<script.*?</script>|<[^>]+>|\s+", " ", t)[:800]})
