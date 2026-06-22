"""
section_splitter.py — format detection and section splitting for Housing Ombudsman decisions.

Two document formats exist:
  'new'  — Nov 2025+ "Investigation" format, starts with "Decision\\nCase ID"
  'old'  — older "REPORT" format, contains REPORT heading near the top
"""
import re

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

# Normalised determination labels (match OUTCOME_PATTERNS in build_insights_db.py)
_DETERMINATION_NORMALISE = {
    'severe maladministration': 'Severe Maladministration',
    'no maladministration': 'No Maladministration',
    'maladministration': 'Maladministration',
    'service failure': 'Service Failure',
    'reasonable redress': 'Reasonable Redress',
    'outside jurisdiction': 'Outside Jurisdiction',
}


def detect_format(text: str) -> str:
    """Return 'new' for Investigation format (Nov 2025+) or 'old' for REPORT format."""
    if _NEW_FORMAT_MARKER.search(text[:200]):
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
