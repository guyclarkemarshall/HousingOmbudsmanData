# Accessibility Patterns

This project serves the UK social housing sector. We are committed to making our datasets, documentation, and tooling accessible to all professionals and researchers, including those using assistive technology.

## Data & Documentation Accessibility
1. **Semantic Markdown**: All documentation files (`README.md`, guides, glossaries) use standard Markdown header hierarchies to support screen readers and outline navigation.
2. **Text Heuristics Over Image Formats**: Database results are delivered as text formats (SQLite database, CSV files), allowing screen readers, text-to-speech engines, and custom analytics packages to read the data easily.
3. **High Contrast Diagrams**: Mermaid flowcharts and database schema diagrams are designed with clear text labels and contrast-friendly stylings.

## CLI Tooling Accessibility
All Python-based command-line interface tools (e.g. `uv run scrape`, `uv run build-insights`):
- Avoid complex nested interactive prompts where simple command arguments can suffice.
- Output clean text messages that screen reader logs can capture.
- Minimize blinking or rapid screen refreshes.

## Future Web Application Standard
Should a frontend dashboard or web catalog be built on top of this dataset, it must strictly comply with **WCAG 2.2 AA** guidelines:
- Complete keyboard navigability.
- Meaningful labels and aria-attributes on form elements.
- Strict color contrast ratio (> 4.5:1 for regular text).
- Automated integration of `axe-core` checks in the pull request pipeline.
