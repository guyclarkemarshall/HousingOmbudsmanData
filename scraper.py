#!/usr/bin/env python3
"""
UK Housing Ombudsman Decision Scraper
Scrapes housing dispute decisions and stores them in a local SQLite database.
"""

import os
import re
import sys
import time
import sqlite3
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Config
DB_NAME = "ombudsman_decisions.db"
URLS_FILE = "urls.txt"
BASE_URL = "https://www.housing-ombudsman.org.uk/decisions/"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
DELAY = 1.5

def init_db(db_path=DB_NAME):
    """Initializes the SQLite database and creates the decisions table if it doesn't exist."""
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            decision_date TEXT,
            landlord TEXT,
            full_text TEXT
        )
    """)
    conn.commit()
    conn.close()

def is_decision_url(url, base_url):
    """Checks if a URL is a decision page and returns the normalized absolute URL, or None."""
    abs_url = urljoin(base_url, url)
    # Strip query parameters and hash fragments
    abs_url = abs_url.split('?')[0].split('#')[0]
    
    # Must start with decisions base URL
    if not abs_url.startswith("https://www.housing-ombudsman.org.uk/decisions/"):
        return None
        
    path_suffix = abs_url[len("https://www.housing-ombudsman.org.uk/decisions/"):].strip('/')
    if not path_suffix:
        return None
        
    # Ignore page/ pagination and rss feeds
    if re.match(r'^page/\d+', path_suffix) or path_suffix == 'feed':
        return None
        
    return abs_url

def harvest_urls(start_page=1, end_page=10, urls_file=URLS_FILE):
    """Phase 1: URL Harvesting (Index Scraping)."""
    print(f"Starting Phase 1: Harvesting URLs from page {start_page} to {end_page}...")
    
    # Load existing URLs to avoid duplicate writing and to keep memory of what was already harvested
    existing_urls = set()
    if os.path.exists(urls_file):
        with open(urls_file, "r", encoding="utf-8") as f:
            for line in f:
                url_str = line.strip()
                if url_str:
                    existing_urls.add(url_str)
        print(f"Loaded {len(existing_urls)} existing URLs from {urls_file}")
        
    discovered_urls = []
    
    for page in range(start_page, end_page + 1):
        if page == 1:
            target_url = BASE_URL
        else:
            target_url = f"{BASE_URL}page/{page}/"
            
        print(f"Fetching archive page {page}/{end_page}: {target_url}")
        
        try:
            r = requests.get(target_url, headers=DEFAULT_HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            # Wait a bit before trying next page
            time.sleep(DELAY)
            continue
            
        soup = BeautifulSoup(r.text, 'html.parser')
        page_links_count = 0
        new_urls_on_page = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            decision_url = is_decision_url(href, target_url)
            if decision_url and decision_url not in existing_urls:
                existing_urls.add(decision_url)
                discovered_urls.append(decision_url)
                new_urls_on_page.append(decision_url)
                page_links_count += 1
                
        print(f"Discovered {page_links_count} NEW decision links on page {page}.")
        
        # Incremental save to file
        if new_urls_on_page:
            with open(urls_file, "a", encoding="utf-8") as f:
                for url in new_urls_on_page:
                    f.write(url + "\n")
            print(f"  Appended {len(new_urls_on_page)} new URLs to {urls_file}")
            
        # Respect rate limit
        time.sleep(DELAY)
        
    print(f"Harvesting phase segment completed. Total unique URLs currently loaded: {len(existing_urls)}")
    return discovered_urls

def clean_date_str(date_str):
    """Formats raw date strings by inserting spaces between day and month if merged (e.g. 26May -> 26 May)."""
    if not date_str:
        return None
    # "26May 2026" -> "26 May 2026"
    date_str = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', date_str)
    # "May2026" -> "May 2026"
    date_str = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', date_str)
    return ' '.join(date_str.split())

def extract_decision_data(url):
    """Fetches a detailed decision page and extracts Title, Date, Landlord, and Full Text."""
    print(f"Extracting detail content from: {url}")
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
    r.raise_for_status()
    
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Title extraction (usually in H1 inside main or header)
    title = None
    main = soup.find('main')
    if main:
        h1 = main.find('h1')
        if h1:
            title = h1.get_text(strip=True)
            
    if not title:
        # Fallbacks
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        else:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Strip branding suffix
                title = title.split('|')[0].strip()
                
    # Metadata extraction (Date, Landlord)
    landlord = None
    date_str = None
    
    # Locate the specific metadata table (the one containing 'Case ID')
    metadata_table = None
    for table in soup.find_all('table'):
        has_case_id = False
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True).lower() for td in tr.find_all(['td', 'th'])]
            if cells and 'case id' in cells[0]:
                has_case_id = True
                break
        if has_case_id:
            metadata_table = table
            break
            
    if metadata_table:
        for tr in metadata_table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if len(cells) == 2:
                key = cells[0].lower().strip()
                val = cells[1].strip()
                if 'landlord type' in key:
                    continue
                elif 'landlord' in key:
                    landlord = val
                elif 'date' in key:
                    date_str = clean_date_str(val)
                    
    # Fallback to paragraph-based metadata parsing if table extraction failed or is incomplete
    if not landlord or not date_str:
        paragraphs = [p.get_text().strip() for p in soup.find_all('p')]
        paragraphs = [p for p in paragraphs if p]
        for idx, text in enumerate(paragraphs):
            if text.upper() == 'REPORT':
                if idx + 1 < len(paragraphs) and 'COMPLAINT' in paragraphs[idx + 1].upper():
                    if not landlord and idx + 2 < len(paragraphs):
                        landlord = paragraphs[idx + 2]
                    if not date_str and idx + 3 < len(paragraphs):
                        date_str = clean_date_str(paragraphs[idx + 3])
                    break
                    
    # Full Text extraction: target main container or the specific column wrapper
    # We find the table, get its parent div that represents the main content column.
    content_div = None
    if main:
        table = main.find('table')
        if table:
            curr = table.parent
            while curr and curr.name != 'main':
                # Identify grid/column container classes
                if curr.name == 'div' and any(cls in curr.get('class', []) for cls in ['column', 'columns', 'medium-9', 'large-8']):
                    content_div = curr
                    break
                curr = curr.parent
                
        if not content_div:
            content_div = main
    else:
        content_div = soup
        
    full_text = content_div.get_text(separator='\n', strip=True)
    
    return {
        "url": url,
        "title": title or "Unknown Title",
        "decision_date": date_str,
        "landlord": landlord or "Unknown Landlord",
        "full_text": full_text
    }

def extract_content(urls_file=URLS_FILE, db_path=DB_NAME):
    """Phase 2: Content Extraction (Detail Scraping)."""
    if not os.path.exists(urls_file):
        print(f"Error: URLs file {urls_file} not found. Run harvesting first.")
        return
        
    with open(urls_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
        
    print(f"Starting Phase 2: Extracting data from {len(urls)} URLs...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    success_count = 0
    fail_count = 0
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Processing decision URL...")
        try:
            # Check if URL already processed
            cursor.execute("SELECT id FROM decisions WHERE url = ?", (url,))
            if cursor.fetchone():
                print(f"  URL already exists in database, skipping: {url}")
                continue
                
            # Extract data
            data = extract_decision_data(url)
            
            # Store in DB
            cursor.execute("""
                INSERT OR IGNORE INTO decisions (url, title, decision_date, landlord, full_text)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data["url"],
                data["title"],
                data["decision_date"],
                data["landlord"],
                data["full_text"]
            ))
            conn.commit()
            
            success_count += 1
            print(f"  Saved: '{data['title']}' | Landlord: '{data['landlord']}' | Date: '{data['decision_date']}'")
            
        except Exception as e:
            fail_count += 1
            print(f"  Error processing URL {url}: {e}", file=sys.stderr)
            
        # Respect rate limit
        time.sleep(DELAY)
        
    conn.close()
    print(f"\nPhase 2 extraction completed. Successes: {success_count}, Failures: {fail_count}")

def main():
    parser = argparse.ArgumentParser(description="Housing Ombudsman Decision Scraper")
    parser.add_argument("--harvest", action="store_true", help="Run Phase 1: Harvest decision URLs from index")
    parser.add_argument("--extract", action="store_true", help="Run Phase 2: Extract decision content from harvested URLs")
    parser.add_argument("--start-page", type=int, default=None, help="Start page for URL harvesting")
    parser.add_argument("--end-page", type=int, default=None, help="End page for URL harvesting")
    parser.add_argument("--pages", type=int, default=None, help="Number of index pages to harvest (default: 10, from page 1)")
    parser.add_argument("--db", type=str, default=DB_NAME, help="SQLite database filename")
    parser.add_argument("--urls-file", type=str, default=URLS_FILE, help="Text file to save/read URLs")
    
    args = parser.parse_args()
    
    # Resolve page ranges with backward compatibility for --pages
    start_page = args.start_page if args.start_page is not None else 1
    if args.end_page is not None:
        end_page = args.end_page
    elif args.pages is not None:
        end_page = args.pages
    else:
        end_page = 10
        
    # If no flags are provided, run both phases in sequence
    run_all = not (args.harvest or args.extract)
    
    init_db(args.db)
    
    if args.harvest or run_all:
        harvest_urls(start_page=start_page, end_page=end_page, urls_file=args.urls_file)
        
    if args.extract or run_all:
        extract_content(urls_file=args.urls_file, db_path=args.db)

if __name__ == "__main__":
    main()
