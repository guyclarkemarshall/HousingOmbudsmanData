# UK Housing Ombudsman Disputes Dataset

A robust and complete dataset of housing dispute decisions scraped from the UK Housing Ombudsman's public index, stored in a local SQLite database.

## Dataset Overview

The dataset contains **16,611** extracted housing dispute decisions covering cases processed from 2019 up to mid-2026.

- **SQLite Database Package**: `ombudsman_decisions.zip` (compressed to 87 MB from the original 342.5 MB SQLite `.db` file).
- **URLs List**: `urls.txt` contains the complete set of 16,612 harvested decision detail URLs.

---

## Licensing & Attribution

This dataset is distributed under the **Creative Commons Attribution 4.0 International (CC-BY-4.0)** license. See the [LICENSE](file:///c:/Users/guycl/OmbudsmanScraper/LICENSE) file for details.

### Source Acknowledgment
- **Source**: All raw decision reports are sourced directly from the [UK Housing Ombudsman website](https://www.housing-ombudsman.org.uk/decisions/).
- **Original License**: Original materials published by the UK Housing Ombudsman are subject to Crown Copyright and published under the **Open Government Licence v3.0 (OGL-3.0)**.
- **Attribution Statement**: Contains public sector information licensed under the Open Government Licence v3.0. Sourced from the UK Housing Ombudsman.

If you use or redistribute this dataset, you must attribute the work by retaining the notice above and citing this repository.

---

## Database Schema

The SQLite database contains a single table named `decisions` with the following structure:

| Column Name | SQLite Type | Description |
|---|---|---|
| `id` | `INTEGER` | Primary Key (auto-incremented) |
| `url` | `TEXT` | Unique URL of the decision page |
| `title` | `TEXT` | Title of the decision (typically includes landlord and case ID) |
| `decision_date` | `TEXT` | Extracted decision date (formatted as e.g., `26 May 2026` or `None` if placeholder) |
| `landlord` | `TEXT` | Extracted Landlord name |
| `full_text` | `TEXT` | Complete body text of the decision report |

---

## How to Use the Data

### 1. Extract the Database
Since the SQLite database exceeds GitHub's file limit, it is stored as a compressed zip archive. Extract it before querying:

*On Windows (PowerShell):*
```powershell
Expand-Archive -Path ombudsman_decisions.zip -DestinationPath .
```

*On Linux/macOS:*
```bash
unzip ombudsman_decisions.zip
```

### 2. Querying the Database (Python Sample)
You can easily load and query the dataset in Python:

```python
import sqlite3

# Connect to the extracted database
conn = sqlite3.connect("ombudsman_decisions.db")
cursor = conn.cursor()

# Query a sample record
cursor.execute("""
    SELECT id, title, landlord, decision_date, length(full_text) 
    FROM decisions 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"ID: {row[0]} | Title: {row[1]} | Landlord: {row[2]} | Date: {row[3]} | Length: {row[4]} chars")

conn.close()
```

---

## Running the Scraper

The repository includes the scraping utility [scraper.py](file:///c:/Users/guycl/OmbudsmanScraper/scraper.py). If you want to update the database or re-scrape decisions, you can use the script directly.

### Prerequisites
Install the required packages:
```bash
pip install requests beautifulsoup4
```

### Script Arguments
- `--harvest`: Run Phase 1 to harvest decision URLs from index.
- `--extract`: Run Phase 2 to extract decision content from harvested URLs.
- `--start-page`: Start page for URL harvesting.
- `--end-page`: End page for URL harvesting.
- `--db`: SQLite database filename (default: `ombudsman_decisions.db`).
- `--urls-file`: Text file to save/read URLs (default: `urls.txt`).

### Examples
*Harvest the first 5 archive pages:*
```bash
python scraper.py --harvest --start-page 1 --end-page 5
```

*Extract content for all URLs currently listed in `urls.txt`:*
```bash
python scraper.py --extract
```
