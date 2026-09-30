"""Filter and rank candidates against a set of search criteria."""

from . import taxonomy
from .db import sector_synonyms

LIST_FIELDS = ("sectors", "roles", "locations", "regions", "strategies", "firm_groups", "qualifications", "keywords")


def empty_criteria():
    return {
        "sectors": [], "roles": [], "locations": [], "regions": [], "strategies": [],
        "firm_groups": [], "qualifications": [], "keywords": [],
        "min_years": None, "max_years": None, "buy_side": False, "sell_side": False,
        "include_unknown_years": False, "years_flex": 0.0,
    }


def is_empty(c):
    return not any(c[f] for f in LIST_FIELDS) and c["min_years"] is None and c["max_years"] is None \
        and not c["buy_side"] and not c["sell_side"]


def run_search(store, criteria):
    """Return (results, info). Each result is a candidate dict with score/snippet added."""
    c = criteria
    hits = store.keyword_hits(c["keywords"])
    info = {"hidden_unknown_years": 0}
    lo = None if c["min_years"] is None else c["min_years"] - c["years_flex"]
    hi = None if c["max_years"] is None else c["max_years"] + c["years_flex"]

    results = []
    for cand in store.all():
        if hits is not None and cand["id"] not in hits:
            continue
        if c["sectors"] and not set(c["sectors"]) & set(cand.get("sectors", [])):
            continue
        if c["roles"] and not set(c["roles"]) & set(cand.get("roles", [])):
            continue
        if c["firm_groups"] and not set(c["firm_groups"]) & set(cand.get("firm_groups", [])):
            continue
        if c["qualifications"] and not set(c["qualifications"]) <= set(cand.get("qualifications", [])):
            continue
        if c["buy_side"] and not cand.get("buy_side"):
            continue
        if c["sell_side"] and not cand.get("sell_side"):
            continue
        if c["locations"] or c["regions"]:
            cand_locs = set(cand.get("locations", []))
            if cand.get("primary_location"):
                cand_locs.add(cand["primary_location"])
            cand_regions = {taxonomy.LOCATIONS[l][0] for l in cand_locs if l in taxonomy.LOCATIONS}
            if not (cand_locs & set(c["locations"]) or cand_regions & set(c["regions"])):
                continue

        years = cand.get("years_experience")
        years = float(years) if years not in (None, "") else None
        if lo is not None or hi is not None:
            if years is None:
                if not c["include_unknown_years"]:
                    info["hidden_unknown_years"] += 1
                    continue
            elif (lo is not None and years < lo) or (hi is not None and years > hi):
                continue

        score = 0.0
        counts = cand.get("sector_counts", {})
        for s in c["sectors"]:
            score += 2 * min(counts.get(s, 0), 10)
            if cand.get("sectors") and cand["sectors"][0] == s:
                score += 6  # it's their main sector
        if hits is not None:
            score += 3 * hits[cand["id"]][0]
        primary = cand.get("primary_location")
        if primary and (primary in c["locations"] or taxonomy.LOCATIONS.get(primary, ("",))[0] in c["regions"]):
            score += 5
        score += 3 * len(set(c["strategies"]) & set(cand.get("strategies", [])))
        if "Long/Short Equity" in cand.get("strategies", []):
            score += 2  # always nudge L/S experience up
        if years is not None and lo is not None and hi is not None:
            score += 3  # inside the requested window (unknowns sink below)

        cand["score"] = round(score, 1)
        if hits is not None:
            cand["snippet"] = hits[cand["id"]][1]
        elif c["sectors"]:
            cand["snippet"] = store.context_snippet(cand["id"], sector_synonyms(c["sectors"]))
        else:
            cand["snippet"] = ""
        results.append(cand)

    if not is_empty(c):
        results.sort(key=lambda r: -r["score"])
    return results, info
