# Manifest Reference

`manifest.yaml` provides per-run context that improves attribution accuracy, speaker quotes, and overall content quality. Run `python main.py init` to generate a template.

---

## Full schema

```yaml
# Required
conference_name: "Data + AI Summit 2025"
conference_date: "2025-05-15"

# Recommended
location: "San Francisco, CA"
conference_url: "https://example.com"

# Default speaker label for unattributed slides
speaker: "Various Speakers"

# Named speaker list for attribution
speakers:
  - name: "Jane Smith"
    role: "Head of AI"
    company: "Databricks"
  - name: "John Doe"
    role: "Principal Engineer"
    company: "dbt Labs"

# Per-file speaker overrides (key = exact filename)
file_speakers:
  "smith_keynote.pdf": "Jane Smith, Head of AI @ Databricks"
  "doe_workshop.png": "John Doe, Principal Engineer @ dbt Labs"

# Max pages extracted per PDF (default: 30)
# Reduce to cut costs on very large decks
max_pages_per_pdf: 30

# Optional notes — fed to synthesis for additional context
notes: |
  Focus tracks: agentic AI, data mesh, streaming pipelines.
  Dominant theme: closing the gap between AI demos and production deployments.
```

---

## Field notes

### `conference_name`
Used in the slug for the output directory, in generated article bylines, and in the topics log. Keep it consistent across runs from the same event.

### `file_speakers`
The most impactful field for output quality. When you know which speaker presented which slides, map them here. The extraction prompt includes the speaker name, which dramatically improves quote attribution and framing.

### `max_pages_per_pdf`
Each page is one Claude Vision API call. A 100-page deck = 100 calls. Set this to `20–30` for conference slides (most of the value is in the first N slides anyway).

### `notes`
Free-form context that gets passed to the synthesis step. Useful for capturing the conference's dominant theme, your personal focus areas for this run, or any background that would help Claude understand the content.

---

## Minimal manifest

If you're in a hurry, the only required field is `conference_name`. Everything else improves quality.

```yaml
conference_name: "My Conference"
```
