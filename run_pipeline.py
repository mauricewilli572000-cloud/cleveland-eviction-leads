#!/usr/bin/env python3
"""Cleveland eviction leads: docket -> landlords -> their Cleveland properties -> scored leads."""
from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import re
import shutil
import sys

import config
import evictions as E

log = logging.getLogger("cleveland_evictions")


def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def split_name(name: str) -> tuple[str, str, str]:
    if E.is_entity(name):
        return "", "", name
    parts = name.split()
    return (" ".join(parts[:-1]), parts[-1], "") if len(parts) > 1 else ("", name, "")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    today = dt.date.today()
    cases = load(config.CASES_JSON, {})

    page = E.get(config.DOCKET_URL).text
    found = E.parse_docket(page)
    m = re.search(r"Period:\s*(.+?)\s+Entries", E._cell(page))
    period = m.group(1).strip() if m else ""
    new = 0
    for c in found:
        old = cases.get(c["case_number"])
        if old is None:
            c["first_seen"] = today.isoformat()
            cases[c["case_number"]] = c
            new += 1
        else:
            old.update({k: v for k, v in c.items() if v})
    log.info("Docket (%s): %d eviction hearings, %d new cases; %d cases stored", period or "?", len(found), new,
             len(cases))

    cache = load(config.PORTFOLIO_CACHE, {})
    stale = (today - dt.timedelta(days=config.PORTFOLIO_REFRESH_DAYS)).isoformat()
    landlords = {}
    for c in cases.values():
        if not E.excluded(c["plaintiff"]):
            landlords.setdefault(E.landlord_key(c["plaintiff"]), c["plaintiff"])
    queried = 0
    for k, name in landlords.items():
        hit = cache.get(k)
        if hit is None or hit.get("checked", "") < stale or hit.get("v") != E.MATCH_VERSION:
            cache[k] = {"checked": today.isoformat(), "v": E.MATCH_VERSION, "properties": E.fetch_portfolio(name)}
            queried += 1
    log.info("Landlords: %d (%d portfolios looked up this run)", len(landlords), queried)

    portfolios = {k: v["properties"] for k, v in cache.items()}
    leads = E.build_leads(cases, portfolios, today)
    meta = {"updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), "docket_period": period,
            "cases": len(cases), "landlords": len(leads), "with_properties": sum(1 for l in leads if l["property_count"]),
            "hot": sum(1 for l in leads if l["tier"] == "HOT")}

    config.DATA_DIR.mkdir(exist_ok=True)
    config.DOCS_DIR.mkdir(exist_ok=True)
    config.CASES_JSON.write_text(json.dumps(cases, indent=0), encoding="utf-8")
    config.PORTFOLIO_CACHE.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")
    config.DASHBOARD_JSON.write_text(json.dumps({"meta": meta, "records": leads}, separators=(",", ":")), encoding="utf-8")
    with open(config.GHL_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["First Name", "Last Name", "Company Name", "Mailing Address", "City", "State", "Postal Code",
                    "Lead Type", "Score", "Tier", "Eviction Filings (12 mo)", "Last Filing", "Cleveland Properties",
                    "Property Addresses", "Case Numbers", "Signals", "Tags"])
        for l in leads:
            if not l["property_count"]:
                continue
            first, last, company = split_name(l["owner_name"])
            w.writerow([first, last, company, l["mailing_street"], l["mailing_city"], l["mailing_state"],
                        l["mailing_zip"], l["lead_type"], l["score"], l["tier"], l["filings_12m"], l["last_filing"],
                        l["property_count"], " | ".join(l["property_addresses"][:10]), "; ".join(l["case_numbers"]),
                        "; ".join(l["signals"]), f"cleveland-evictions,{l['tier'].lower()},{l['owner_type']}"])
    shutil.copyfile(config.GHL_CSV, config.DOCS_CSV)
    log.info("Saved %d landlord leads (%d with properties, %d hot)", len(leads), meta["with_properties"], meta["hot"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
