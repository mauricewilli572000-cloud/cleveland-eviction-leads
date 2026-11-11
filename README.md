# Cleveland (Cuyahoga County, OH) — Eviction Leads (tired landlords)

Built like `franklin-eviction-leads`.

- **Cases:** Cleveland Municipal Housing Court *civil docket* (scheduled hearings), read daily.
  The court's case portal is behind a CAPTCHA, so only the published docket is used. Every
  eviction case seen is kept, so history builds up even if the court skips a week.
- **Properties:** each landlord's name is matched against Cuyahoga County parcel owners in Cleveland.
  This is the landlord's whole Cleveland portfolio, not necessarily the unit being evicted.
- The Housing Authority, the City and land bank are left out.

Score: repeat filings, individual (not company) landlords, small portfolios (1–5 properties),
out-of-state owners; big managers lose points.

Outputs: `docs/index.html` · `docs/cleveland_evictions.json` (read by ohio-lead-stacker) ·
`data/ghl_cleveland_evictions.csv` (landlords with properties found).
