# CV Search: a private CV database for L/S equity search

Upload your CVs (PDF, Word, zip of a folder), then search in plain English:

> **Healthcare analyst 3-5 years London buy-side**

The app reads every CV and pulls out:

| Detected automatically | How |
|---|---|
| **Years of experience** | Adds up the job date ranges ("Jan 2019 – Present", "03/2017 - 06/2020", "2016 – 2019"). Overlapping roles count once and education dates are ignored. Falls back to phrases like "6 years of experience". |
| **Sector** | Healthcare, TMT, Consumer, Industrials, Financials, Energy, Utilities, Materials, Real Estate, Business Services, Autos, Generalist. Uses synonyms, so *biotech*, *pharma* and *medtech* all count as Healthcare. |
| **Role** | Analyst, Associate, PM, Sector Head, CIO, Trader, Quant, Risk, Data Scientist |
| **Location** | London, NYC, Dubai, Abu Dhabi, Riyadh, Doha, etc., plus regions (UK / US / Middle East / Europe / Asia). The current location comes from the contact block. |
| **Firms & background** | ~200 named pod shops, hedge funds, GCC sovereigns, long-only managers, sell-side banks and consultancies. Gives you **buy-side** and **sell-side** filters. |
| **Strategy** | Long/Short Equity, Long Only, Event Driven, Macro, and more |
| **Qualifications** | CFA (charterholder or any level), MBA, PhD, MD, ACA/CPA, CAIA |
| **Contact details** | Name, email, phone, LinkedIn |

Anything else you type (e.g. *oncology*, *"medical devices"*, *ex-Millennium*) becomes a keyword that must appear in the CV.
Results are ranked by how strongly each CV matches, with the matching text highlighted.

## Features

- **Natural-language search.** The app shows how it read your search as removable chips, and you can adjust it with the filter panel.
- **Candidate page.** Shows the parsed profile, the full CV text with your keywords highlighted, and buttons to open or download the original file.
- **Notes and corrections.** Add call notes, comp or availability, and fix anything the parser got wrong (years, location, sectors). Your edits are kept separately and survive re-analysis.
- **Export shortlist to CSV** so you can send it or paste it into your CRM.
- **Duplicate detection.** Re-uploading the same file is harmless.
- **Flexible years.** Add ±1 year of "flex", and choose whether to include CVs whose experience couldn't be worked out.

## Privacy

Everything runs **on your own computer**. CVs are never sent to any outside service. The app only accepts connections
from your own machine (127.0.0.1). CVs and the database live in the `data/` folder, which is excluded from git.
Deleting a candidate removes their CV file too, which helps with GDPR requests.

## Windows: the easy way

1. Install **Python** from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** on the installer's first screen.
2. Download this project as a ZIP from GitHub, right-click the file and choose **Extract All**.
3. Double-click **`start.bat`**. The first run takes a minute or two to set up, then your browser opens on the app.
   Keep the black window open while you use the app. Closing it stops the app.
4. To load your CVs, drag your CV folder onto **`import_cvs.bat`**. You can also use the **Upload CVs** page in the app.

## Setup by hand (Mac, or Windows without the .bat files)

1. Install **Python 3.10 or newer** from https://www.python.org/downloads/ (on Windows, tick *"Add Python to PATH"*).
2. Download this project, open a terminal (Mac: *Terminal*; Windows: *Command Prompt*) in the project folder, and run:

   ```
   python -m venv .venv
   # Mac/Linux:
   source .venv/bin/activate
   # Windows:
   .venv\Scripts\activate

   pip install -r requirements.txt
   ```

3. *(Optional)* For old **.doc** / **.rtf** files, install the free [LibreOffice](https://www.libreoffice.org). PDF and .docx work without it.

## Loading your ~1,000 CVs

Point the importer at the folder that holds them. Sub-folders are included.

```
python import_cvs.py "/Users/you/Documents/CVs"
```

This takes about 20 seconds per 1,000 CVs. Afterwards it lists any files that need a look, for example scanned image-only
PDFs, which contain no text to read. You can also upload files or a .zip from the **Upload CVs** page at any time.

## Running the app

```
python run.py
```

Your browser opens at http://127.0.0.1:5000. Press Ctrl+C in the terminal to stop the app.

## Tailoring the keywords

All sector synonyms, firm names, locations and qualifications are in [`cvsearch/taxonomy.py`](cvsearch/taxonomy.py),
which is plain lists you can edit. Add a new fund or a sector synonym, then click **Re-analyse all CVs** on the Upload page, or run
`python import_cvs.py --reparse`.

## Known limits

- **Years of experience is an estimate** from the dates on the CV, and internships are included. Correct it on the candidate page when needed.
- **Scanned PDFs** (photos of paper) have no text and are flagged on upload. They would need OCR.
- Sector tagging needs **at least two mentions**, or one mention in a job-title line, so that a passing reference doesn't tag a CV.

## For developers

```
pip install pytest
python -m pytest
```

Code layout: `cvsearch/extract.py` (file → text), `parser.py` (text → profile), `query.py` (search sentence → filters),
`search.py` (filtering and ranking), `db.py` (SQLite + FTS5 full-text index), `app.py` (Flask web UI).
