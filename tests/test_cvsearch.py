import datetime as dt

import pytest

from cvsearch.app import create_app
from cvsearch.db import Store
from cvsearch.parser import experience_ranges, parse_cv, total_years
from cvsearch.query import parse_query
from cvsearch.search import empty_criteria, run_search

TODAY = dt.date(2026, 9, 30)

HEALTHCARE_LONDON = """JANE SMITH
London, UK | jane.smith@email.com | +44 7700 900123 | linkedin.com/in/janesmith

PROFESSIONAL EXPERIENCE
Millennium Management, London                                   Jan 2023 – Present
Healthcare Analyst, Long/Short Equity pod
- Coverage of European pharma and medtech; generated long and short ideas in biotech.

Morgan Stanley, London                                           Sep 2021 – Dec 2022
Equity Research Associate, European Healthcare
- Covered pharmaceuticals and medical devices.

EDUCATION
University of Oxford, MSc Biochemistry                            2017 – 2021
CFA Level II candidate
"""

TMT_NYC = """John Doe
New York, NY | john@doe.com

EXPERIENCE
Citadel - Global Equities, New York        06/2014 - Present
Senior Analyst, TMT - software and semiconductors, long/short
Goldman Sachs, New York                    07/2012 - 05/2014
Investment Banking Analyst, Technology group

EDUCATION
Wharton, MBA 2010 - 2012
CFA Charterholder
"""

HEALTHCARE_DUBAI_JUNIOR = """Ahmed Al Mansoori
Dubai, UAE | ahmed@example.ae

Work Experience
ADIA, Abu Dhabi — Investment Analyst, Healthcare Equities       2025 – Present
Deloitte — Consultant, healthcare practice                        2024 – 2025
"""

NO_DATES = """Sarah Lee
Consumer analyst with 6 years of buy-side experience at Lansdowne Partners covering retail and luxury. London.
"""


def test_years_merge_overlaps_and_skip_education():
    ranges = experience_ranges(HEALTHCARE_LONDON, TODAY)
    assert len(ranges) == 2  # Oxford 2017-2021 is excluded
    assert total_years(ranges) == pytest.approx(5.0, abs=0.1)  # Sep 2021 -> Sep 2026


def test_parse_healthcare_cv():
    p = parse_cv(HEALTHCARE_LONDON, "jane.pdf", TODAY)
    assert p["name"] == "Jane Smith"
    assert p["email"] == "jane.smith@email.com"
    assert p["sectors"][0] == "Healthcare"
    assert p["primary_location"] == "London"
    assert p["buy_side"] and p["sell_side"]
    assert "Long/Short Equity" in p["strategies"]
    assert "Millennium" in p["firms"]
    assert p["career_start"] == 2021
    assert "Millennium" in p["current_role"]
    assert "CFA (any level)" in p["qualifications"]


def test_parse_tmt_cv():
    p = parse_cv(TMT_NYC, "john.docx", TODAY)
    assert p["name"] == "John Doe"
    assert p["sectors"][0] == "TMT"
    assert p["primary_location"] == "New York"
    assert p["years_experience"] == pytest.approx(14.2, abs=0.1)  # Jul 2012 -> Sep 2026
    assert "CFA Charterholder" in p["qualifications"]
    assert "MBA" in p["qualifications"]


def test_stated_years_fallback():
    p = parse_cv(NO_DATES, "sarah.txt", TODAY)
    assert p["years_experience"] == 6 and p["years_source"] == "stated"
    assert "Consumer" in p["sectors"]


@pytest.mark.parametrize("q, expected", [
    ("Healthcare analyst with 3-5 years experience",
     {"sectors": ["Healthcare"], "roles": ["Analyst"], "min_years": 3, "max_years": 5, "keywords": []}),
    ("biotech PM 10+ years NYC", {"sectors": ["Healthcare"], "roles": ["Portfolio Manager"],
                                   "min_years": 10, "max_years": None, "locations": ["New York"]}),
    ("TMT associate up to 3 yrs Middle East buy-side",
     {"sectors": ["TMT"], "roles": ["Associate"], "max_years": 3, "regions": ["Middle East"], "buy_side": True}),
    ('consumer analyst ex-Millennium "e-commerce" London',
     {"sectors": ["Consumer"], "locations": ["London"], "keywords": ["e-commerce", "Millennium"]}),
    ("healthcare analyst oncology CFA charterholder",
     {"keywords": ["oncology"], "qualifications": ["CFA Charterholder"]}),
    ("analyst 5 years", {"min_years": 4, "max_years": 6}),
    ("Healthcare analyst 3-5 years buy-side", {"min_years": 3, "max_years": 5, "buy_side": True}),
])
def test_parse_query(q, expected):
    got = parse_query(q)
    for k, v in expected.items():
        assert got[k] == v, (k, got)


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "data"))
    for name, text in [("jane.txt", HEALTHCARE_LONDON), ("john.txt", TMT_NYC),
                       ("ahmed.txt", HEALTHCARE_DUBAI_JUNIOR), ("sarah.txt", NO_DATES)]:
        path = tmp_path / name
        path.write_text(text)
        assert s.add_file(str(path))[0] == "added"
    return s


def search(store, q):
    c = empty_criteria()
    c.update({k: v for k, v in parse_query(q).items() if k in c})
    return [r["name"] for r in run_search(store, c)[0]]


def test_search_end_to_end(store, tmp_path):
    assert search(store, "Healthcare analyst 3-5 years") == ["Jane Smith"]
    assert search(store, "healthcare analyst up to 3 years Middle East") == ["Ahmed Al Mansoori"]
    assert set(search(store, "healthcare")) == {"Jane Smith", "Ahmed Al Mansoori"}
    assert search(store, "TMT 10+ years CFA charterholder") == ["John Doe"]
    assert search(store, "semiconductors") == ["John Doe"]
    assert search(store, "sell-side London") == ["Jane Smith"]
    # duplicates are detected
    (tmp_path / "copy.txt").write_text(TMT_NYC)
    assert store.add_file(str(tmp_path / "copy.txt"))[0] == "duplicate"


def test_web_app(tmp_path):
    app = create_app(str(tmp_path / "data"))
    client = app.test_client()
    assert b"No CVs yet" in client.get("/").data

    (tmp_path / "jane.txt").write_text(HEALTHCARE_LONDON)
    with open(tmp_path / "jane.txt", "rb") as f:
        r = client.post("/upload", data={"files": [(f, "jane.txt")]}, content_type="multipart/form-data")
    assert b"<strong>1</strong> added" in r.data

    r = client.get("/?q=healthcare+analyst+3-5+years")
    assert r.status_code == 302
    r = client.get(r.headers["Location"])
    assert b"Jane Smith" in r.data and b"Sector: Healthcare" in r.data

    r = client.post("/candidate/1", data={"notes": "Strong on biotech", "years_experience": "6", "sectors": ["Healthcare"]})
    assert r.status_code == 302
    assert app.store.get(1)["years_experience"] == 6
    assert "Jane Smith" in client.get("/export.csv?sector=Healthcare").data.decode()
    assert client.get("/candidate/1/file").status_code == 200
    client.post("/candidate/1/delete")
    assert app.store.stats()["total"] == 0
