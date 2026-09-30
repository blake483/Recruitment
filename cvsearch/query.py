"""Interpret a plain-English search like "Healthcare analyst 3-5 years London".

The output is a set of structured filters plus leftover keywords, which the
search page shows back to you so you can see (and tweak) what was understood.
"""

import re

from . import taxonomy
from .parser import pattern_for

_NUM = r"(\d{1,2}(?:\.\d)?)"
_YRS = r"\s*(?:\+\s*)?(?:years?|yrs?|yoe|y)\b(?:\s+of)?(?:\s+(?:work|industry|relevant|investment))?(?:\s+experience)?"

_YEAR_PATTERNS = [
    (re.compile(rf"{_NUM}\s*(?:-|–|—|to)\s*{_NUM}{_YRS}", re.I), "range"),
    (re.compile(rf"(?:at\s+least|minimum(?:\s+of)?|min\.?|over|more\s+than|>=?)\s*{_NUM}{_YRS}", re.I), "min"),
    (re.compile(rf"{_NUM}\s*\+{_YRS}", re.I), "min"),
    (re.compile(rf"{_NUM}{_YRS}\s*(?:plus|or\s+more|\+)", re.I), "min"),
    (re.compile(rf"(?:up\s+to|at\s+most|max(?:imum)?\.?|less\s+than|under|<=?)\s*{_NUM}{_YRS}", re.I), "max"),
    (re.compile(rf"{_NUM}{_YRS}", re.I), "about"),
]

_FLAGS = {
    "buy_side": re.compile(r"\bbuy[- ]?side\b", re.I),
    "sell_side": re.compile(r"\bsell[- ]?side\b", re.I),
}

_FIRM_GROUP_ALIASES = {
    "Multi-Manager / Pod": ["multi-manager", "multi manager", "multimanager", "pod shop", "pod", "platform"],
    "Sovereign / GCC Institution": ["sovereign wealth", "swf", "sovereign"],
    "Long-Only Asset Manager": ["asset manager", "long only fund"],
    "Consulting / Industry": ["consulting", "consultant", "industry background"],
}

_STOPWORDS = set("""
a an and or the with without in on at of for from to by who whom that which is are be has have having
experience experienced exp years year yrs yr plus level role roles search searching looking look need needs
want wants someone somebody candidate candidates cv cvs resume resumes profile profiles based located
hedge fund funds equity equities long short l s fundamental good strong great top tier ideally preferably
background please find show me all any some currently current previously within around approx approximately
""".split())


def _consume(q, pattern):
    """Remove every match of pattern from q; return (new_q, list_of_matches)."""
    found = [m.group(0) for m in pattern.finditer(q)]
    return pattern.sub(" ", q), found


def parse_query(q):
    q = q or ""
    result = {
        "sectors": [], "roles": [], "locations": [], "regions": [], "strategies": [],
        "firm_groups": [], "qualifications": [], "min_years": None, "max_years": None,
        "buy_side": False, "sell_side": False, "keywords": [],
    }

    # Quoted phrases are always kept as literal keywords.
    for phrase in re.findall(r'"([^"]+)"', q):
        result["keywords"].append(phrase.strip())
    q = re.sub(r'"[^"]*"', " ", q)

    for flag, pattern in _FLAGS.items():
        q, found = _consume(q, pattern)
        result[flag] = bool(found)

    for pattern, kind in _YEAR_PATTERNS:
        m = pattern.search(q)
        if not m:
            continue
        a = float(m.group(1))
        if kind == "range":
            b = float(m.group(2))
            result["min_years"], result["max_years"] = min(a, b), max(a, b)
        elif kind == "min":
            result["min_years"] = a
        elif kind == "max":
            result["max_years"] = a
        else:  # "5 years" -> roughly 4 to 6
            result["min_years"], result["max_years"] = max(a - 1, 0), a + 1
        q = q[:m.start()] + " " + q[m.end():]
        break

    # Qualifications before roles, so "CFA charterholder" is not split up.
    for key, mapping in (
        ("qualifications", taxonomy.QUALIFICATIONS),
        ("strategies", taxonomy.STRATEGIES),
        ("roles", taxonomy.ROLES),
        ("sectors", taxonomy.SECTORS),
        ("firm_groups", _FIRM_GROUP_ALIASES),
    ):
        for tag, synonyms in mapping.items():
            q, found = _consume(q, pattern_for(synonyms))
            if found and tag not in result[key]:
                result[key].append(tag)
    if "CFA Charterholder" in result["qualifications"] and "CFA (any level)" in result["qualifications"]:
        result["qualifications"].remove("CFA (any level)")

    for tag, (_, synonyms) in taxonomy.LOCATIONS.items():
        q, found = _consume(q, pattern_for(synonyms))
        if found:
            result["locations"].append(tag)
    for region, synonyms in taxonomy.REGIONS.items():
        # "us" is only a region when written in capitals.
        syns = [s for s in synonyms if s != "us"]
        q, found = _consume(q, pattern_for(syns))
        if region == "US":
            q, caps = _consume(q, re.compile(r"\bUS\b"))
            found += caps
        if found:
            result["regions"].append(region)

    # Named firms (e.g. "ex-Millennium") are searched as literal keywords.
    for synonyms in taxonomy.FIRMS.values():
        for m in pattern_for(synonyms).finditer(q):
            result["keywords"].append(m.group(0))
        q = pattern_for(synonyms).sub(" ", q)

    for token in re.findall(r"[A-Za-z0-9&][A-Za-z0-9&.+#'-]*", q):
        token = token.strip(".'-")
        if token and token.lower() not in _STOPWORDS and not re.fullmatch(r"ex|\d+", token.lower()):
            result["keywords"].append(token)
    return result
