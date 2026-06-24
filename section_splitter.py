"""
section_splitter.py — format detection, section splitting, and shared extraction
utilities for Housing Ombudsman decisions.

Two document formats exist:
  'new'  — Nov 2025+ "Investigation" format, starts with "Decision\\nCase ID"
  'old'  — older "REPORT" format, contains REPORT heading near the top
"""
import hashlib
import re

# ---------------------------------------------------------------------------
# Shared canonical constants
# ---------------------------------------------------------------------------

# Valid finding outcomes and their normalized casings.
# This is the single source of truth — all other modules import this dict.
NORMALIZED_OUTCOMES = {
    'no maladministration': 'No Maladministration',
    'service failure': 'Service Failure',
    'maladministration': 'Maladministration',
    'severe maladministration': 'Severe Maladministration',
    'reasonable redress': 'Reasonable Redress',
    'outside jurisdiction': 'Outside Jurisdiction',
    'choose an item.': 'Choose an item.',
}

# New-format docs (Nov 2025+) start with this metadata block
_NEW_FORMAT_MARKER = re.compile(r'^Decision\s*\nCase ID', re.MULTILINE)

OLD_SECTION_RE = re.compile(
    r'^('
    r'Background(?: and summary of events)?'
    r'|Summary of events'
    r'|The complaint'
    r'|Policies and Procedures'
    r'|Assessment and findings?'
    r'|Scope(?: of(?: the)? investigation)?'
    r'|Complaint handling'
    r'|Determination(?:\s*\((?:decision|jurisdictional decision)\))?'
    r'|Orders?(?: and recommendations?)?'
    r'|Recommendations?'
    r'|Conclusion'
    r'|Investigation'
    r')\s*$',
    re.MULTILINE | re.IGNORECASE
)

NEW_SECTION_RE = re.compile(
    r'^('
    r'Background'
    r'|What the complaint is about'
    r'|Our decision\s*\(determination\)'
    r'|Summary of reasons'
    r'|Putting things right'
    r'|Our investigation'
    r'|What we found(?: and why)?'
    r'|Orders?(?: and recommendations?)?'
    r'|Recommendations?'
    r'|Complaint'
    r'|Finding'
    r')\s*$',
    re.MULTILINE | re.IGNORECASE
)

# New-format Complaint/Finding pair extraction
_FINDING_PAIR_RE = re.compile(
    r'\nComplaint\n(.*?)\nFinding\n'
    r'(No maladministration|Service failure|Maladministration|'
    r'Severe maladministration|Reasonable redress|Outside jurisdiction)\n'
    r'(.*?)(?=\nComplaint\n|\nOrders?\n|\nPutting things right\n|$)',
    re.DOTALL | re.IGNORECASE
)

# Normalised determination labels — derived from the canonical NORMALIZED_OUTCOMES
_DETERMINATION_NORMALISE = {k: v for k, v in NORMALIZED_OUTCOMES.items() if k != 'choose an item.'}


def detect_format(text: str) -> str:
    """Return 'new' for Investigation format (Nov 2025+) or 'old' for REPORT format."""
    if _NEW_FORMAT_MARKER.search(text[:500]):
        return 'new'
    return 'old'


def split_sections(text: str) -> dict:
    """
    Split a Housing Ombudsman decision into named sections.
    Returns dict of {section_name: section_text}.
    Handles both old REPORT format and new Investigation format.
    Repeating Complaint/Finding headings (new format) are indexed: complaint_1, finding_1, etc.
    """
    fmt = detect_format(text)
    section_re = NEW_SECTION_RE if fmt == 'new' else OLD_SECTION_RE

    matches = list(section_re.finditer(text))
    if not matches:
        return {'full_doc': text}

    sections = {}

    # Capture preamble (metadata header before first heading)
    if matches[0].start() > 0:
        sections['preamble'] = text[:matches[0].start()].strip()

    counters = {}
    for i, m in enumerate(matches):
        raw_name = m.group(1).strip().lower()
        # Normalise spacing variants to a canonical key
        name = re.sub(r'\s+', '_', raw_name)
        name = re.sub(r'[^a-z0-9_]', '', name)

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Index repeated headings (complaint_1, complaint_2, finding_1 ...)
        if name in counters:
            counters[name] += 1
            key = f"{name}_{counters[name]}"
        else:
            counters[name] = 1
            key = f"{name}_1" if name in ('complaint', 'finding') else name

        sections[key] = content

    return sections


def extract_complaint_finding_pairs(text: str) -> list:
    """
    For new-format docs: extract structured (complaint, outcome, analysis) tuples
    from Complaint/Finding heading pairs inside the Our investigation section.
    Returns list of dicts with keys: complaint, outcome, analysis.
    outcome is normalised to match OUTCOME_PATTERNS labels in build_insights_db.py.
    Returns empty list for old-format docs.
    """
    if detect_format(text) == 'old':
        return []

    results = []
    for m in _FINDING_PAIR_RE.finditer(text):
        raw_outcome = m.group(2).strip().lower()
        outcome = _DETERMINATION_NORMALISE.get(raw_outcome, m.group(2).strip())
        results.append({
            'complaint': m.group(1).strip(),
            'outcome': outcome,
            'analysis': m.group(3).strip(),
        })
    return results


# ---------------------------------------------------------------------------
# Shared utility functions (canonical implementations — imported by both
# build_insights_db.py and build_complaints_db.py)
# ---------------------------------------------------------------------------

def parse_case_id(title: str, url: str) -> str:
    """Extracts a unique case ID from the title or URL.

    Tries title first (e.g. "Housing Trust (202347433)"), then URL
    (e.g. ends with landlord-name-caseid/), then falls back to a
    pseudo-id based on the URL hash.
    """
    # Try looking in title (usually e.g. "Housing Trust (202347433)")
    match = re.search(r'\((\d{7,9})\)', title)
    if match:
        return match.group(1)

    # Fallback to URL (usually ends with landlord-name-caseid/)
    match = re.search(r'-(\d{7,9})/?$', url)
    if match:
        return match.group(1)

    # Generates a pseudo-id if none found
    return "pseudo_" + hashlib.md5(url.encode()).hexdigest()[:8]


def extract_pairs(text: str) -> list:
    """Parses text line-by-line to extract complaint and finding pairs.

    Looks for lines matching the pattern:
      Complaint
      <description lines...>
      Finding
      <outcome>
    Returns list of (complaint_description, normalized_outcome) tuples.
    """
    if not text:
        return []

    text = text.replace('\r\n', '\n')
    lines = text.split('\n')

    pairs = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        if line.lower() == 'complaint':
            complaint_lines = []
            j = i + 1
            found_finding = False

            while j < n:
                next_line = lines[j].strip()
                if next_line.lower() == 'complaint':
                    # Hit another Complaint header without finding a Finding block first
                    break
                if next_line.lower() == 'finding':
                    found_finding = True
                    break
                complaint_lines.append(next_line)
                j += 1

            if found_finding and j + 1 < n:
                outcome = lines[j+1].strip()
                outcome_clean = outcome.rstrip('.').strip()
                outcome_lower = outcome_clean.lower()
                if outcome_lower in NORMALIZED_OUTCOMES:
                    complaint_desc = " ".join(" ".join(complaint_lines).split()).strip()
                    normalized_outcome = NORMALIZED_OUTCOMES[outcome_lower]
                    pairs.append((complaint_desc, normalized_outcome))
                    i = j + 2
                    continue
        i += 1

    return pairs


# ---------------------------------------------------------------------------
# Landlord Identity & Stock Size Canonical Mappings
# ---------------------------------------------------------------------------

import datetime

# Mappings to collapse landlord name variants to their canonical keys
LANDLORD_CANONICAL_MAPPINGS = {
    "lambeth": "london borough of lambeth",
    "l&q": "london & quadrant housing trust (l&q)",
    "london & quadrant": "london & quadrant housing trust (l&q)",
    "london and quadrant": "london & quadrant housing trust (l&q)",
    "peabody": "peabody trust",
    "clarion": "clarion housing association",
    "birmingham": "birmingham city council",
    "sovereign": "sovereign network group",
    "accent": "accent group",
    "aster": "aster group",
    "bromford": "bromford housing association",
    "connexus": "connexus housing",
    "curo": "curo places",
    "east midlands": "east midlands housing group",
    "emh group": "east midlands housing group",
    "forhousing": "forhousing",
    "greensquareaccord": "greensquareaccord",
    "abri": "abri group",
    "lewisham": "london borough of lewisham",
    "haringey": "haringey london borough council",
    "southern housing": "southern housing",
    "southwark": "southwark council",
    "notting hill genesis": "notting hill genesis (nhg)",
    "nhg": "notting hill genesis (nhg)",
    "sanctuary": "sanctuary housing association",
    "guinness": "the guinness partnership",
    "riverside": "the riverside group",
    "a2dominion": "a2dominion housing group",
    "a2 dominion": "a2dominion housing group",
    "hammersmith": "london borough of hammersmith and fulham",
    "havering": "london borough of havering council",
    "hyde housing": "hyde housing association",
    "incommunities": "incommunities",
    "islington": "london borough of islington",
    "jigsaw": "jigsaw homes group limited",
    "kirklees": "kirklees council",
    "barking and dagenham": "london borough of barking and dagenham",
    "brent": "london borough of brent",
    "croydon": "london borough of croydon",
    "ealing": "london borough of ealing",
    "enfield": "london borough of enfield",
    "hackney": "london borough of hackney",
    "hillingdon": "london borough of hillingdon",
    "hounslow": "london borough of hounslow",
    "newham": "london borough of newham",
    "milton keynes": "milton keynes city council",
    "moat homes": "moat homes limited",
    "newcastle": "newcastle city council",
    "north tyneside": "north tyneside council",
    "norwich": "norwich city council",
    "onward": "onward group",
    "orbit": "orbit group",
    "paradigm": "paradigm housing group",
    "home group": "home group",
    "places for people": "places for people homes",
    "sparrow": "sparrow shared ownership",
    "housing for women": "housing for women",
    "soho": "soho housing association"
}

# Canonical cased names for display and database storage
LANDLORD_DISPLAY_NAMES = {
    "london borough of lambeth": "London Borough of Lambeth",
    "london & quadrant housing trust (l&q)": "London & Quadrant Housing Trust (L&Q)",
    "peabody trust": "Peabody Trust",
    "clarion housing association": "Clarion Housing Association",
    "birmingham city council": "Birmingham City Council",
    "sovereign network group": "Sovereign Network Group",
    "accent group": "Accent Group",
    "aster group": "Aster Group",
    "bromford housing association": "Bromford Housing Association",
    "connexus housing": "Connexus Housing",
    "curo places": "Curo Places",
    "east midlands housing group": "East Midlands Housing Group",
    "forhousing": "ForHousing",
    "greensquareaccord": "GreenSquareAccord",
    "abri group": "Abri Group",
    "london borough of lewisham": "London Borough of Lewisham",
    "haringey london borough council": "Haringey London Borough Council",
    "southern housing": "Southern Housing",
    "southwark council": "Southwark Council",
    "notting hill genesis (nhg)": "Notting Hill Genesis (NHG)",
    "sanctuary housing association": "Sanctuary Housing Association",
    "the guinness partnership": "The Guinness Partnership",
    "the riverside group": "The Riverside Group",
    "a2dominion housing group": "A2Dominion Housing Group",
    "london borough of hammersmith and fulham": "London Borough of Hammersmith and Fulham",
    "london borough of havering council": "London Borough of Havering Council",
    "hyde housing association": "Hyde Housing Association",
    "incommunities": "Incommunities",
    "london borough of islington": "London Borough of Islington",
    "jigsaw homes group limited": "Jigsaw Homes Group Limited",
    "kirklees council": "Kirklees Council",
    "london borough of barking and dagenham": "London Borough of Barking and Dagenham",
    "london borough of brent": "London Borough of Brent",
    "london borough of croydon": "London Borough of Croydon",
    "london borough of ealing": "London Borough of Ealing",
    "london borough of enfield": "London Borough of Enfield",
    "london borough of hackney": "London Borough of Hackney",
    "london borough of hillingdon": "London Borough of Hillingdon",
    "london borough of hounslow": "London Borough of Hounslow",
    "london borough of newham": "London Borough of Newham",
    "milton keynes city council": "Milton Keynes City Council",
    "moat homes limited": "Moat Homes Limited",
    "newcastle city council": "Newcastle City Council",
    "north tyneside council": "North Tyneside Council",
    "norwich city council": "Norwich City Council",
    "onward group": "Onward Group",
    "orbit group": "Orbit Group",
    "paradigm housing group": "Paradigm Housing Group",
    "home group": "Home Group",
    "places for people homes": "Places for People Homes",
    "sparrow shared ownership": "Sparrow Shared Ownership",
    "housing for women": "Housing For Women",
    "soho housing association": "Soho Housing Association"
}

# RSH stock sizes (number of homes owned/managed) for normalisation checks
LANDLORD_STOCK_SIZES = {
    "Clarion Housing Association": 125000,
    "London & Quadrant Housing Trust (L&Q)": 110500,
    "Peabody Trust": 109000,
    "Metropolitan Thames Valley (MTV)": 57000,
    "Hyde Housing Association": 120000,
    "The Riverside Group": 75000,
    "Sanctuary Housing Association": 120000,
    "The Guinness Partnership": 70000,
    "Birmingham City Council": 60000,
    "London Borough of Lambeth": 33000,
    "Southwark Council": 55000,
    "Sovereign Network Group": 84000,
    "Bromford Housing Association": 46000,
    "Orbit Group": 47000,
    "Places for People Homes": 74000,
    "Home Group": 55000,
    "A2Dominion Housing Group": 39000,
    "London Borough of Hackney": 30000,
    "London Borough of Lewisham": 19000,
    "Haringey London Borough Council": 15000,
    "London Borough of Islington": 25000,
    "London Borough of Brent": 12000,
    "London Borough of Barking and Dagenham": 20000,
    "London Borough of Croydon": 16000,
    "London Borough of Ealing": 17000,
    "London Borough of Enfield": 11000,
    "London Borough of Hillingdon": 10000,
    "London Borough of Hounslow": 16000,
    "London Borough of Newham": 16000,
    "Milton Keynes City Council": 12000,
    "Moat Homes Limited": 20000,
    "Newcastle City Council": 25000,
    "North Tyneside Council": 15000,
    "Norwich City Council": 15000,
    "Onward Group": 35000,
    "Paradigm Housing Group": 15000,
    "Accent Group": 20000,
    "Aster Group": 32000,
    "Connexus Housing": 10000,
    "Curo Places": 13000,
    "East Midlands Housing Group": 21000,
    "ForHousing": 24000,
    "GreenSquareAccord": 25000,
    "Abri Group": 40000,
    "Southern Housing": 78000,
    "Notting Hill Genesis (NHG)": 66000,
    "London Borough of Hammersmith and Fulham": 17000,
    "London Borough of Havering Council": 10000,
    "Incommunities": 22000,
    "Jigsaw Homes Group Limited": 35000,
    "Kirklees Council": 22000,
}

def canonical_landlord_name(name):
    if not name:
        return "Unknown Landlord"
    name_lower = name.lower()
    
    # 1. Match canonical mappings with word boundary checks
    for k, v in LANDLORD_CANONICAL_MAPPINGS.items():
        pattern = r'(?<!\w)' + re.escape(k) + r'(?!\w)'
        if re.search(pattern, name_lower):
            return LANDLORD_DISPLAY_NAMES.get(v, v)
            
    # 2. General cleanup for other names
    clean = name
    clean = re.sub(
        r'\b(housing association|housing group|housing trust|group|limited|ltd|council|borough council|city council|district council|london borough of|london borough council|london borough|trust|homes)\b',
        '', clean, flags=re.I
    )
    clean = re.sub(r'[\(\)\-\,\.\']', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.title()

def clean_date_to_iso(date_str):
    if not date_str:
        return None, 0
        
    s_lower = date_str.strip().lower()
    
    # Check if amended/reissued/updated
    amended = 0
    if any(x in s_lower for x in ('amended', 're-issued', 'reissued', 'updated', 'review')):
        amended = 1
        
    # Collapse split digits, e.g. "202 4" -> "2024"
    s_clean = date_str
    s_clean = re.sub(r'(\d)\s+(?=\d)', r'\1', s_clean)
    
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    # Match standard "DD Month YYYY" pattern
    m = re.search(r'(\d+)\s+([a-zA-Z]+)\s+(\d{4})', s_clean)
    if m:
        day_str = m.group(1)
        if len(day_str) > 2:
            day_str = day_str[:2]
        day = int(day_str)
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month = months.get(month_name)
        if month:
            try:
                dt = datetime.date(year, month, day)
                return dt.strftime("%Y-%m-%d"), amended
            except ValueError:
                pass
                
    # Match DD/MM/YYYY pattern
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', s_clean)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year = int(m.group(3))
        try:
            dt = datetime.date(year, month, day)
            return dt.strftime("%Y-%m-%d"), amended
        except ValueError:
            pass
            
    return None, amended

