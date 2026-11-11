import datetime as dt

import evictions as E

PAGE = """<table><tr><th>Case Number</th><th>Case Style</th><th>Hearing Type</th><th>Hearing Date</th><th>Hearing Time</th></tr>
<tr><th>2026-CVG-012976</th><td>Barbara Welker vs Frank Visconti et al.</td><td>Housing Eviction</td><td>Friday, October 16, 2026</td><td>9:00 AM</td></tr>
<tr><th>2026-CVG-017107</th><td>ME Real Estate Cleveland LLC vs Sarata Kande</td><td>Housing Eviction</td><td>Friday, October 16, 2026</td><td>9:00 AM</td></tr>
<tr><th>2026-CVG-017200</th><td>Cuyahoga Metropolitan Housing Authority vs A B</td><td>Housing Eviction</td><td>Monday, October 19, 2026</td><td>9:00 AM</td></tr>
<tr><th>2026-CVH-000001</th><td>X vs Y</td><td>Rent Deposit</td><td>Monday, October 19, 2026</td><td>9:00 AM</td></tr></table>"""


def test_parse_docket():
    cases = E.parse_docket(PAGE)
    assert [c["case_number"] for c in cases] == ["2026-CVG-012976", "2026-CVG-017107", "2026-CVG-017200"]
    assert cases[0]["plaintiff"] == "Barbara Welker" and cases[0]["defendant"] == "Frank Visconti"
    assert cases[0]["hearing_date"] == "2026-10-16"


def test_owner_patterns():
    assert E.owner_patterns("Barbara Welker") == ["WELKER%BARBARA%"]
    assert E.owner_patterns("Montgomery Street Homes LLC") == ["MONTGOMERY STREET HOMES%"]


def test_owner_matches():
    assert E.owner_matches("James Taylor", "TAYLOR, JAMES A. JR.")
    assert not E.owner_matches("James Taylor", "TAYLOR, JAMESON S.")
    assert E.owner_matches("Montgomery Street Homes LLC", "MONTGOMERY STREET HOMES, LLC")
    assert not E.owner_matches("East Properties LLC", "EAST 55TH PROPERTIES, LLC.")


def test_build_leads_excludes_cmha_and_scores_small_individual():
    cases = {c["case_number"]: {**c, "first_seen": "2026-10-16"} for c in E.parse_docket(PAGE)}
    props = {E.landlord_key("Barbara Welker"): [{"parcel": "1", "address": "1 MAIN ST, CLEVELAND, OH, 44102",
              "owner": "WELKER, BARBARA", "use": "", "mail_street": "9 ELM", "mail_city": "MIAMI",
              "mail_state": "FL", "mail_zip": "33101"}]}
    leads = E.build_leads(cases, props, dt.date(2026, 11, 10))
    names = [l["owner_name"] for l in leads]
    assert "Cuyahoga Metropolitan Housing Authority" not in names
    top = leads[0]
    assert top["owner_name"] == "Barbara Welker" and top["tier"] in ("HOT", "WARM") and top["property_count"] == 1
