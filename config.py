"""Cleveland (Cuyahoga County, OH) eviction leads - tired landlords.

Cases:  Cleveland Municipal Housing Court civil docket (scheduled hearings, HTML)
        https://www.clevelandhousingcourt.org/accessible-civil-docket
        The court's case portal is behind a CAPTCHA, so only the published docket is used.
        Every eviction case seen is kept, so history builds up run by run.
Owners: Cuyahoga County Open Data Parcels (owner, site and mailing address)
"""
from pathlib import Path

DOCKET_URL = "https://www.clevelandhousingcourt.org/accessible-civil-docket"
EVICTION_HEARING_WORDS = ["EVICTION", "FORCIBLE", "FED"]
PARCELS_QUERY = "https://gis.cuyahogacounty.gov/server/rest/services/Open_Data_Parcels/MapServer/0/query"
PARCEL_FIELDS = "parcelpin,deeded_owner,par_addr_all,par_city,par_zip,mail_name,mail_addr_street,mail_city,mail_state,mail_zip,tax_luc_description"
MAX_PORTFOLIO = 200          # parcels kept per landlord
PORTFOLIO_REFRESH_DAYS = 30  # re-query a landlord's properties this often
REQUEST_DELAY = 0.3

# Plaintiffs that are never motivated sellers.
EXCLUDE_PLAINTIFFS = ["CUYAHOGA METROPOLITAN HOUSING", "CMHA", "HOUSING AUTHORITY", "CITY OF CLEVELAND",
                      "COUNTY OF CUYAHOGA", "LAND REUTILIZATION", "LAND BANK"]
ENTITY_WORDS = ["LLC", "L.L.C", "INC", "CORP", "COMPANY", " CO ", "LTD", " LP", "LLP", "TRUST", "PROPERTIES",
                "HOLDINGS", "INVESTMENTS", "MANAGEMENT", "REALTY", "HOMES", "APARTMENTS", "ASSOCIATES", "GROUP",
                "PARTNERS", "ENTERPRISES", "VENTURES", "CAPITAL", "RENTALS", "HOUSING", "CHURCH", "BANK", "FUND"]
LARGE_MANAGER_WORDS = ["MANAGEMENT", "APARTMENTS", "COMMUNITIES", "RESIDENTIAL", "MILLENNIA", "K&D", "NRP"]

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
CASES_JSON = DATA_DIR / "cases.json"
PORTFOLIO_CACHE = DATA_DIR / "portfolio_cache.json"
DASHBOARD_JSON = DOCS_DIR / "cleveland_evictions.json"
GHL_CSV = DATA_DIR / "ghl_cleveland_evictions.csv"
DOCS_CSV = DOCS_DIR / "ghl_cleveland_evictions.csv"
