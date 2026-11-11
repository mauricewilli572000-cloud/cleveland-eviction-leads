"""Parse the Housing Court docket, group cases by landlord, find landlords' properties, score."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import logging
import re
import time

import config

log = logging.getLogger(__name__)

try:
    from curl_cffi import requests as _http
    S = _http.Session(impersonate="chrome")
except Exception:  # pragma: no cover
    import requests as _http
    S = _http.Session()


def get(url, **kw):
    last = None
    for attempt in range(4):
        try:
            r = S.get(url, timeout=90, **kw)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


# ----------------------------------------------------------------- docket
def _cell(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_docket(page: str) -> list[dict]:
    """Rows of the accessible civil docket -> eviction cases."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [_cell(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)]
        if len(cells) < 4 or not re.match(r"\d{4}-CV", cells[0]):
            continue
        num, style, htype, hdate = cells[:4]
        if not any(w in htype.upper() for w in config.EVICTION_HEARING_WORDS):
            continue
        plaintiff, _, defendant = style.partition(" vs ")
        out.append({"case_number": num, "plaintiff": clean_party(plaintiff), "defendant": clean_party(defendant),
                    "hearing_type": htype, "hearing_date": parse_date(hdate)})
    return out


def clean_party(p: str) -> str:
    p = re.sub(r"\bet\.? al\.?\s*$", "", p.strip(), flags=re.I).strip(" ,.")
    return re.sub(r"\s+", " ", p)


def parse_date(s: str) -> str:
    for fmt in ("%A, %B %d, %Y", "%B %d, %Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def landlord_key(name: str) -> str:
    n = re.sub(r"[^A-Z0-9 ]", " ", name.upper())
    n = re.sub(r"\b(LLC|L L C|INC|CORP|CORPORATION|CO|COMPANY|LTD|LP|LLP|THE)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def is_entity(name: str) -> bool:
    n = f" {name.upper()} "
    return any(w in n for w in config.ENTITY_WORDS)


def excluded(name: str) -> bool:
    n = name.upper()
    return any(w in n for w in config.EXCLUDE_PLAINTIFFS) or n.startswith("OCCUPANT")


# ----------------------------------------------------------------- portfolio
def owner_patterns(name: str) -> list[str]:
    """SQL LIKE patterns for the county owner field.

    Companies: 'MONTGOMERY STREET HOMES%'. People ('Barbara Welker'): the county writes
    'WELKER, BARBARA' or 'WELKER BARBARA', so match 'WELKER%BARBARA%'.
    """
    key = landlord_key(name)
    if not key:
        return []
    if is_entity(name):
        return [key.replace(" ", "%") + "%"]
    toks = key.split()
    if len(toks) < 2:
        return []
    first, last = toks[0], toks[-1]
    return [f"{last}%{first}%"]


def fetch_portfolio(name: str) -> list[dict]:
    props = {}
    for pat in owner_patterns(name):
        where = f"UPPER(deeded_owner) LIKE '{pat.replace(chr(39), chr(39) * 2)}' AND UPPER(par_city) = 'CLEVELAND'"
        params = {"where": where, "outFields": config.PARCEL_FIELDS, "returnGeometry": "false", "f": "json",
                  "resultRecordCount": config.MAX_PORTFOLIO}
        try:
            feats = get(config.PARCELS_QUERY, params=params).json().get("features", [])
        except Exception as e:  # noqa: BLE001
            log.warning("portfolio query failed for %s: %s", name, e)
            continue
        for f in feats:
            a = f.get("attributes", {})
            pin = str(a.get("parcelpin") or "")
            addr = re.sub(r"\s+", " ", str(a.get("par_addr_all") or "")).strip()
            if pin and addr and not addr.startswith("0 "):
                props[pin] = {
                    "parcel": pin, "address": addr, "owner": a.get("deeded_owner") or "",
                    "use": a.get("tax_luc_description") or "",
                    "mail_street": a.get("mail_addr_street") or "", "mail_city": a.get("mail_city") or "",
                    "mail_state": a.get("mail_state") or "", "mail_zip": str(a.get("mail_zip") or "")[:5],
                }
        time.sleep(config.REQUEST_DELAY)
    return list(props.values())


# ----------------------------------------------------------------- leads
def build_leads(cases: dict[str, dict], portfolios: dict[str, list[dict]], today: dt.date) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    names: dict[str, str] = {}
    for c in cases.values():
        if excluded(c["plaintiff"]):
            continue
        k = landlord_key(c["plaintiff"])
        if not k:
            continue
        groups.setdefault(k, []).append(c)
        names.setdefault(k, c["plaintiff"])
    y_ago = (today - dt.timedelta(days=365)).isoformat()
    q_ago = (today - dt.timedelta(days=90)).isoformat()
    leads = []
    for k, cs in groups.items():
        name = names[k]
        props = portfolios.get(k, [])
        dates = sorted(c.get("hearing_date") or c["first_seen"] for c in cs)
        n12 = sum(1 for d in dates if d >= y_ago)
        n90 = sum(1 for d in dates if d >= q_ago)
        mail = next((p for p in props if p["mail_street"]), {})
        out_state = bool(mail.get("mail_state")) and mail["mail_state"].upper() not in ("OH", "OHIO")
        entity = is_entity(name)
        large = any(w in name.upper() for w in config.LARGE_MANAGER_WORDS) or len(props) > 25

        score, signals = 0, []
        b = min(40, 10 * n12); score += b; signals.append(f"{n12} eviction filing(s) on the docket (+{b})")
        if n90 >= 2:
            score += 10; signals.append("2+ filings in 90 days (+10)")
        if not entity:
            score += 20; signals.append("individual landlord (+20)")
        if props and len(props) <= 5:
            score += 15; signals.append(f"small portfolio: {len(props)} Cleveland propert{'y' if len(props) == 1 else 'ies'} (+15)")
        if out_state:
            score += 10; signals.append(f"owner mails out of state ({mail['mail_state']}) (+10)")
        if large:
            score -= 30; signals.append("large manager / portfolio (-30)")
        if not props:
            signals.append("no Cleveland properties found under this name")
        score = max(0, min(100, score))
        tier = "HOT" if score >= 60 else "WARM" if score >= 35 else "COLD"
        leads.append({
            "lead_id": hashlib.sha1(k.encode()).hexdigest()[:12],
            "lead_type": "Eviction (tired landlord)",
            "source": "Cleveland Housing Court docket",
            "owner_name": name,
            "owner_type": "entity" if entity else "individual",
            "mailing_street": mail.get("mail_street", ""), "mailing_city": mail.get("mail_city", ""),
            "mailing_state": mail.get("mail_state", ""), "mailing_zip": mail.get("mail_zip", ""),
            "property_addresses": [p["address"] for p in props][:50],
            "parcels": [p["parcel"] for p in props][:50],
            "property_count": len(props),
            "filings_12m": n12, "filings_90d": n90,
            "first_filing": dates[0], "last_filing": dates[-1],
            "case_numbers": sorted(c["case_number"] for c in cs),
            "defendants": sorted({c["defendant"] for c in cs if c["defendant"]})[:20],
            "score": score, "tier": tier, "signals": signals,
        })
    leads.sort(key=lambda l: (-l["score"], -l["filings_12m"], l["owner_name"]))
    return leads
