"""Keyword dictionaries for Long/Short equity hedge fund recruiting.

Every tag maps to a list of synonyms. Matching is case-insensitive and on
word boundaries, so "Tech" will not match "Technical" unless listed.
Edit these lists freely, then run `python import_cvs.py --reparse` to
re-tag every CV already in the database.
"""

SECTORS = {
    "Healthcare": [
        "healthcare", "health care", "biotech", "biotechnology", "pharma",
        "pharmaceutical", "pharmaceuticals", "medtech", "med tech",
        "medical devices", "medical technology", "life sciences",
        "managed care", "diagnostics", "hospitals", "healthcare services",
        "specialty pharma", "biopharma", "life science tools",
    ],
    "TMT": [
        "tmt", "technology", "tech", "software", "semiconductors",
        "semiconductor", "semis", "internet", "media", "telecom",
        "telecoms", "telecommunications", "hardware", "it services",
        "saas", "cybersecurity", "ai infrastructure",
    ],
    "Consumer": [
        "consumer", "retail", "retailers", "consumer staples",
        "consumer discretionary", "staples", "restaurants", "leisure",
        "luxury", "apparel", "food & beverage", "food and beverage",
        "beverages", "e-commerce", "ecommerce", "travel", "hotels",
        "gaming", "household products",
    ],
    "Industrials": [
        "industrials", "industrial", "aerospace", "defense", "defence",
        "capital goods", "transports", "transportation", "machinery",
        "building products", "construction", "airlines", "logistics",
        "multi-industry", "electrical equipment",
    ],
    "Financials": [
        "financials", "banks", "banking sector", "insurance", "insurers",
        "fintech", "asset managers", "specialty finance", "exchanges",
        "payments", "diversified financials",
    ],
    "Energy": [
        "energy", "oil & gas", "oil and gas", "e&p", "oilfield services",
        "refiners", "midstream", "energy transition", "renewables",
        "clean energy", "clean tech", "cleantech",
    ],
    "Utilities": ["utilities", "power & utilities", "power generation", "regulated utilities"],
    "Materials": [
        "materials", "basic materials", "chemicals", "metals & mining",
        "metals and mining", "mining", "steel", "paper & packaging",
        "packaging", "commodities",
    ],
    "Real Estate": ["real estate", "reits", "reit", "property sector", "listed property"],
    "Business Services": ["business services", "services sector", "staffing", "outsourcing"],
    "Autos": ["autos", "automotive", "auto parts", "autos & mobility", "electric vehicles"],
    "Generalist": ["generalist", "multi-sector", "multi sector", "sector agnostic"],
}

ROLES = {
    "Analyst": [
        "analyst", "research analyst", "investment analyst", "equity analyst",
        "senior analyst", "equity research analyst", "sector analyst",
    ],
    "Associate": ["associate", "research associate", "investment associate"],
    "Portfolio Manager": [
        "portfolio manager", "pm", "sub-pm", "sub pm", "co-pm",
        "co-portfolio manager", "lead portfolio manager",
    ],
    "Sector Head": ["sector head", "head of research", "head of equities", "sector lead"],
    "CIO": ["cio", "chief investment officer"],
    "Trader": ["trader", "execution trader", "equity trader"],
    "Quant": ["quant", "quantitative analyst", "quantitative researcher"],
    "Risk": ["risk manager", "risk analyst", "risk management"],
    "Data Scientist": ["data scientist", "data science", "alternative data", "alt data"],
}

STRATEGIES = {
    "Long/Short Equity": [
        "long/short", "long short", "long-short", "l/s", "equity long/short",
        "long/short equity", "long short equity", "market neutral",
        "fundamental equity", "equity hedge fund",
    ],
    "Long Only": ["long only", "long-only"],
    "Event Driven": ["event driven", "event-driven", "merger arbitrage", "special situations"],
    "Macro": ["global macro", "macro"],
    "Credit": ["credit analyst", "credit fund", "distressed debt", "high yield"],
    "Quantitative": ["systematic", "quantitative equity", "stat arb", "statistical arbitrage"],
}

# Firms are grouped so a search for "buy-side" or "sell-side" works too.
FIRMS = {
    "Multi-Manager / Pod": [
        "millennium", "citadel", "point72", "point 72", "balyasny", "exodus point",
        "exoduspoint", "schonfeld", "verition", "eisler", "hudson bay",
        "jain global", "walleye", "marshall wace", "centiva", "capstone investment",
        "sculptor", "man group", "man glg", "glg", "bluecrest", "squarepoint",
        "qube", "holocene", "integrated core strategies", "surveyor capital",
        "citadel global equities",
    ],
    "Hedge Fund": [
        "hedge fund", "egerton", "lansdowne", "tiger global", "coatue",
        "lone pine", "maverick capital", "viking global", "d1 capital", "third point",
        "pershing square", "jericho capital", "tci", "the children's investment fund",
        "two sigma", "aqr", "samlyn", "suvretta", "ra capital", "deerfield management",
        "perceptive advisors", "casdin", "ghost tree", "polar capital", "cheyne",
        "odey", "brook asset", "pelham capital", "sand grove", "kite lake",
        "whale rock", "light street", "atreides", "durable capital",
        "eminence capital", "glenview capital", "hound partners", "steadfast capital", "alkeon",
        "tybourne", "boussard", "sona asset management", "helikon",
        "bridgewater", "arrowstreet", "rokos", "brevan howard", "caxton",
        "tudor investment", "elliott management", "davidson kempner",
        "anchorage capital", "king street capital", "farallon", "baupost",
        "marathon asset management", "blackstone alternative",
    ],
    "Sovereign / GCC Institution": [
        "adia", "abu dhabi investment authority", "mubadala", "pif",
        "public investment fund", "qia", "qatar investment authority",
        "kuwait investment authority", "adq", "lunate", "alpha dhabi",
        "international holding company", "oman investment authority",
        "saudi aramco", "jadwa", "hassana", "al rajhi capital", "sico",
        "emirates nbd asset management", "investcorp", "gulf capital",
    ],
    "Long-Only Asset Manager": [
        "fidelity", "wellington", "capital group", "t. rowe price", "t rowe price",
        "blackrock", "schroders", "baillie gifford", "invesco", "jpmam",
        "j.p. morgan asset management", "jpmorgan asset management",
        "janus henderson", "m&g", "aberdeen standard", "abrdn", "legal & general",
        "lgim", "ninety one", "artisan partners", "pimco", "vanguard",
        "state street", "amundi", "pictet", "lombard odier", "columbia threadneedle",
        "federated hermes", "jupiter", "liontrust", "ruffer",
    ],
    "Sell-Side": [
        "goldman sachs", "morgan stanley", "jp morgan", "j.p. morgan", "jpmorgan",
        "bank of america", "bofa", "merrill lynch", "citi", "citigroup",
        "citibank", "barclays", "ubs", "credit suisse", "deutsche bank",
        "jefferies", "bernstein", "alliancebernstein", "evercore", "evercore isi",
        "cowen", "td cowen", "leerink", "svb leerink", "piper sandler",
        "stifel", "berenberg", "exane", "bnp paribas", "hsbc", "nomura",
        "macquarie", "redburn", "rothschild & co redburn", "numis", "peel hunt",
        "wolfe research", "raymond james", "rbc", "rbc capital markets",
        "guggenheim", "mizuho", "bmo", "wells fargo", "oppenheimer",
        "needham & company", "robert w. baird", "william blair", "truist", "kepler cheuvreux",
        "societe generale", "société générale", "equity research", "sell-side",
        "sell side", "efg hermes", "arqaam", "hsbc saudi",
        "snb capital", "emirates nbd capital",
    ],
    "Consulting / Industry": [
        "mckinsey", "bain & company", "boston consulting group", "bcg",
        "l.e.k.", "lek consulting", "oliver wyman", "deloitte", "pwc",
        "kpmg", "ernst & young", "ey-parthenon", "accenture",
    ],
}

LOCATIONS = {
    # location tag -> (region, synonyms)
    "London": ("UK", ["london", "mayfair", "st james's", "canary wharf"]),
    "Edinburgh": ("UK", ["edinburgh"]),
    "New York": ("US", ["new york", "nyc", "new york city", "manhattan", "ny, ny", "new york, ny"]),
    "Stamford / Greenwich": ("US", ["stamford", "greenwich"]),
    "Boston": ("US", ["boston"]),
    "San Francisco": ("US", ["san francisco", "menlo park", "palo alto"]),
    "Chicago": ("US", ["chicago"]),
    "Miami": ("US", ["miami", "west palm beach", "palm beach"]),
    "Dubai": ("Middle East", ["dubai", "difc"]),
    "Abu Dhabi": ("Middle East", ["abu dhabi", "adgm"]),
    "Riyadh": ("Middle East", ["riyadh", "saudi arabia", "ksa"]),
    "Doha": ("Middle East", ["doha", "qatar"]),
    "Kuwait": ("Middle East", ["kuwait"]),
    "Bahrain": ("Middle East", ["bahrain", "manama"]),
    "Hong Kong": ("Asia", ["hong kong"]),
    "Singapore": ("Asia", ["singapore"]),
    "Paris": ("Europe", ["paris"]),
    "Geneva": ("Europe", ["geneva"]),
    "Zurich": ("Europe", ["zurich", "zürich"]),
    "Frankfurt": ("Europe", ["frankfurt"]),
    "Stockholm": ("Europe", ["stockholm"]),
}

REGIONS = {
    "UK": ["uk", "united kingdom", "england", "britain"],
    "US": ["us", "usa", "united states", "america"],
    "Middle East": ["middle east", "gcc", "mena", "gulf", "uae", "united arab emirates"],
    "Europe": ["europe", "continental europe"],
    "Asia": ["asia", "apac"],
}

QUALIFICATIONS = {
    "CFA Charterholder": ["cfa charterholder", "cfa charter holder", "cfa®"],
    "CFA (any level)": ["cfa", "cfa level i", "cfa level ii", "cfa level iii", "cfa level 1", "cfa level 2", "cfa level 3"],
    "MBA": ["mba", "master of business administration"],
    "PhD": ["phd", "ph.d", "ph.d.", "dphil", "doctorate"],
    "MD": ["m.d.", "doctor of medicine", "mbbs", "medical doctor", "physician"],
    "ACA / CPA": ["aca", "acca", "cpa", "chartered accountant", "icaew"],
    "CAIA": ["caia"],
}

# Tags that are too ambiguous to trust from a single mention in the body.
# (e.g. "tech" or "media" crop up in every CV; "power" in "PowerPoint" won't
# match thanks to word boundaries, but "power" as a verb still might.)
SECTOR_MIN_MENTIONS = 2

# Which firm groups count as buy-side / sell-side for the quick filters.
BUY_SIDE_GROUPS = {"Multi-Manager / Pod", "Hedge Fund", "Sovereign / GCC Institution", "Long-Only Asset Manager"}
SELL_SIDE_GROUPS = {"Sell-Side"}
