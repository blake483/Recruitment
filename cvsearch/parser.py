"""Pull structured facts out of raw CV text.

Everything here is heuristic keyword matching - no external services, so CVs
never leave your machine. Results are "best effort" and can be corrected by
hand on each candidate's page.
"""

import datetime as dt
import re
from functools import lru_cache

from . import taxonomy

_WORD_EDGE_L = r"(?<![A-Za-z0-9])"
_WORD_EDGE_R = r"(?![A-Za-z0-9])"


@lru_cache(maxsize=None)
def _pattern(synonyms):
    alts = sorted(synonyms, key=len, reverse=True)  # longest first
    body = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in alts)
    return re.compile(_WORD_EDGE_L + "(?:" + body + ")" + _WORD_EDGE_R, re.IGNORECASE)


def pattern_for(synonyms):
    return _pattern(tuple(synonyms))


def count_tags(text, mapping):
    counts = {}
    for tag, synonyms in mapping.items():
        if isinstance(synonyms, tuple):  # LOCATIONS entries are (region, synonyms)
            synonyms = synonyms[1]
        n = len(pattern_for(synonyms).findall(text))
        if n:
            counts[tag] = n
    return counts


# --------------------------------------------------------------------------
# Experience dates
# --------------------------------------------------------------------------

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
             r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_DATE_RE = (rf"(?:{_MONTH_RE}\.?,?\s*(?:\d{{4}}|'\d{{2}})"   # Jan 2019, Sept. 2019, Mar '19
            r"|(?<!\d)\d{1,2}\s*[/.]\s*\d{4}(?!\d)"            # 03/2019, 3.2019
            r"|(?<!\d)(?:19|20)\d{2}(?!\d))")                  # 2019
_PRESENT_RE = r"(?:present|current|currently|now|today|date|ongoing)"
_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_RE})\s*(?:-|–|—|~|to|until|till|through)\s*(?P<end>{_DATE_RE}|{_PRESENT_RE})",
    re.IGNORECASE,
)

_EDU_HEADINGS = ("education", "academic", "qualifications", "university education")
_EXP_HEADINGS = ("experience", "professional experience", "work experience", "employment",
                 "career history", "career", "professional background", "work history",
                 "investment experience", "relevant experience")
_OTHER_HEADINGS = ("skills", "interests", "languages", "additional", "certifications",
                   "publications", "references", "personal", "activities", "achievements",
                   "extracurricular", "awards", "profile", "summary", "other")
_EDU_LINE = re.compile(
    r"(?<![A-Za-z])(?:university|universit[àäé]|college|school|institute of technology|"
    r"b\.?sc|m\.?sc|b\.?a\.?\s*\(hons|bachelor|master'?s|mba|ph\.?d|a-levels?|gcse|"
    r"high school|baccalaureate|degree)(?![A-Za-z])",
    re.IGNORECASE,
)


def _heading_kind(line):
    stripped = re.sub(r"[^a-z &]", "", line.lower()).strip()
    if not stripped or len(stripped) > 45 or len(stripped.split()) > 5:
        return None
    for kind, words in (("edu", _EDU_HEADINGS), ("exp", _EXP_HEADINGS), ("other", _OTHER_HEADINGS)):
        if any(stripped.startswith(w) or stripped.endswith(w) for w in words):
            return kind
    return None


def _parse_date(s, is_end, today):
    s = s.strip().lower()
    if re.fullmatch(_PRESENT_RE, s):
        return today.year, today.month
    m = re.match(rf"({_MONTH_RE})\.?,?\s*(\d{{4}}|'\d{{2}})", s)
    if m:
        year = m.group(2)
        year = 2000 + int(year[1:]) if year.startswith("'") else int(year)
        return year, _MONTHS[m.group(1)[:3]]
    m = re.match(r"(\d{1,2})\s*[/.]\s*(\d{4})", s)
    if m:
        month = int(m.group(1))
        return int(m.group(2)), month if 1 <= month <= 12 else 1
    m = re.match(r"(\d{4})", s)
    if m:
        # Year-only ranges: "2016 - 2019" reads as three years.
        return int(m.group(1)), 1
    return None


def experience_ranges(text, today=None):
    """Return [(start_month_index, end_month_index, line)] for work date ranges."""
    today = today or dt.date.today()
    ranges = []
    section = None
    for line in text.splitlines():
        kind = _heading_kind(line)
        if kind:
            section = kind
            continue
        if section == "edu" or _EDU_LINE.search(line):
            continue
        for m in _RANGE_RE.finditer(line):
            start = _parse_date(m.group("start"), False, today)
            end = _parse_date(m.group("end"), True, today)
            if not start or not end:
                continue
            s_idx = start[0] * 12 + start[1] - 1
            e_idx = end[0] * 12 + end[1] - 1
            if not (1970 <= start[0] <= today.year and 1970 <= end[0] <= today.year + 1):
                continue
            if e_idx < s_idx or e_idx - s_idx > 45 * 12:
                continue
            ranges.append((s_idx, min(e_idx, today.year * 12 + today.month - 1), line.strip()))
    return ranges


def total_years(ranges):
    """Sum of date ranges, with overlapping roles counted once."""
    if not ranges:
        return None
    spans = sorted((s, e) for s, e, _ in ranges)
    months = 0
    cur_s, cur_e = spans[0]
    for s, e in spans[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            months += cur_e - cur_s
            cur_s, cur_e = s, e
    months += cur_e - cur_s
    return round(months / 12, 1)


_STATED_YEARS = re.compile(
    r"(\d{1,2})\+?\s*(?:years|yrs)['’]?\s*(?:of\s+)?(?:[a-z/&-]+\s+){0,4}?experience",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Contact details
# --------------------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:\+|00)?\d[\d\s().-]{7,}\d")
_LINKEDIN = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.IGNORECASE)
_NOT_NAME = re.compile(
    r"curriculum|vitae|resume|résumé|^cv$|profile|summary|address|email|phone|mobile|"
    r"linkedin|confidential|experience|education",
    re.IGNORECASE,
)


def _guess_name(lines, fallback):
    for line in lines[:10]:
        candidate = re.sub(r"\s+", " ", line).strip(" ,|-•")
        candidate = re.split(r"\s[|•–-]\s", candidate)[0].strip()
        words = candidate.split()
        if not (2 <= len(words) <= 5) or len(candidate) > 50:
            continue
        if _NOT_NAME.search(candidate) or re.search(r"[\d@/:]", candidate):
            continue
        if not all(re.fullmatch(r"[A-Za-zÀ-ÿ'’.-]+", w) for w in words):
            continue
        if not all(w[0].isupper() for w in words if len(w) > 2):
            continue
        return candidate.title() if candidate.isupper() else candidate
    return fallback


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------

def _role_line(line):
    return bool(pattern_for(sum(taxonomy.ROLES.values(), [])).search(line))


def _clean_role(s):
    return re.sub(r"\s+", " ", s).strip(" |,-–—:()•\t")


def _location_of(line):
    for tag, (_, syns) in taxonomy.LOCATIONS.items():
        if pattern_for(syns).search(line):
            return tag
    return None


def parse_cv(text, filename="", today=None):
    today = today or dt.date.today()
    lines = [l for l in (ln.strip() for ln in text.splitlines()) if l]
    fallback_name = re.sub(r"[_-]+", " ", filename.rsplit(".", 1)[0]).strip().title() or "Unknown"

    # --- experience
    ranges = experience_ranges(text, today)
    years = total_years(ranges)
    years_source = "dates" if years is not None else None
    if years is None:
        stated = [int(m.group(1)) for m in _STATED_YEARS.finditer(text) if int(m.group(1)) < 45]
        if stated:
            years, years_source = float(max(stated)), "stated"
    career_start = None
    current_role = ""
    if ranges:
        career_start = min(s for s, _, _ in ranges) // 12
        latest = max(ranges, key=lambda r: (r[1], r[0]))
        current_role = _clean_role(_RANGE_RE.sub("", latest[2]))
        idx = next((i for i, l in enumerate(lines) if l == latest[2]), None)
        if idx is not None and not _role_line(current_role):
            # Firm and title are usually on adjacent lines; add whichever has the title.
            for j in (idx + 1, idx - 1):
                if 0 <= j < len(lines) and _role_line(lines[j]) and not _RANGE_RE.search(lines[j]):
                    extra = _clean_role(lines[j])
                    current_role = f"{current_role} — {extra}" if current_role else extra
                    break
        current_role = current_role[:160]

    # --- sectors: need repeated mentions, or a mention on a job-title line
    sector_counts = count_tags(text, taxonomy.SECTORS)
    title_sectors = set()
    for line in lines:
        if _role_line(line):
            title_sectors.update(count_tags(line, taxonomy.SECTORS))
    sector_tags = sorted(
        (t for t, n in sector_counts.items() if n >= taxonomy.SECTOR_MIN_MENTIONS or t in title_sectors),
        key=lambda t: -sector_counts[t],
    )

    roles = sorted(count_tags(text, taxonomy.ROLES))
    strategies = sorted(count_tags(text, taxonomy.STRATEGIES))
    firm_groups = sorted(count_tags(text, taxonomy.FIRMS))
    firms = {}  # lower-case -> spelling as it first appears on the CV
    for syns in taxonomy.FIRMS.values():
        for m in pattern_for(syns).finditer(text):
            key = re.sub(r"\s+", " ", m.group(0).lower())
            if key not in {"hedge fund", "equity research", "sell-side", "sell side"}:
                firms.setdefault(key, re.sub(r"\s+", " ", m.group(0)))
    firms = sorted(firms.values(), key=str.lower)

    # Ignore education lines, so "London Business School" doesn't make someone London-based.
    loc_counts = count_tags("\n".join(l for l in lines if not _EDU_LINE.search(l)), taxonomy.LOCATIONS)
    locations = sorted(loc_counts, key=lambda t: -loc_counts[t])
    primary_location = None
    for line in lines[:12]:  # contact block
        primary_location = _location_of(line)
        if primary_location:
            break
    if not primary_location and ranges:
        primary_location = _location_of(max(ranges, key=lambda r: r[1])[2])
    if not primary_location and locations:
        primary_location = locations[0]
    regions = sorted({taxonomy.LOCATIONS[l][0] for l in locations})

    quals = sorted(count_tags(text, taxonomy.QUALIFICATIONS))

    email = _EMAIL.search(text)
    phone = next((p.group(0).strip() for p in _PHONE.finditer("\n".join(lines[:25]))
                  if sum(c.isdigit() for c in p.group(0)) >= 9
                  and not _RANGE_RE.fullmatch(p.group(0).strip())), "")
    linkedin = _LINKEDIN.search(text)

    return {
        "name": _guess_name(lines, fallback_name),
        "email": email.group(0) if email else "",
        "phone": phone,
        "linkedin": linkedin.group(0) if linkedin else "",
        "years_experience": years,
        "years_source": years_source,
        "career_start": career_start,
        "current_role": current_role,
        "sector_counts": sector_counts,
        "sectors": sector_tags,
        "roles": roles,
        "strategies": strategies,
        "firm_groups": firm_groups,
        "firms": firms,
        "locations": locations,
        "primary_location": primary_location,
        "regions": regions,
        "qualifications": quals,
        "buy_side": bool(set(firm_groups) & taxonomy.BUY_SIDE_GROUPS),
        "sell_side": bool(set(firm_groups) & taxonomy.SELL_SIDE_GROUPS),
    }
