# linkedin-articles

Turn conference artefacts — slide photos, PDFs, speaker decks — into LinkedIn-ready content using Claude.

Drop your files in, answer a few prompts, get back a long-form article, carousel post (with `.pptx`), infographic concept with DALL-E prompt, and/or a short punchy post. All copy-paste ready.

---

## Features

- **Multimodal extraction** — Claude Vision reads slide images and PDFs page-by-page, pulling out key points, quotes, data, frameworks, and technologies
- **Hot-take detection** — flags counterintuitive or contrarian claims that make the best hooks
- **Synthesis brief** — clusters insights across all artefacts into 3–5 themes with novelty scoring; you review and approve before generation
- **Format recommender** — picks the right format(s) based on your content (carousel for slide-heavy runs, article for dense conceptual content, etc.)
- **Topic deduplication** — tracks what you've already written about across runs so you don't repeat yourself
- **Four output formats**:
  - `article.md` — 600–900 word long-form LinkedIn article
  - `carousel.md` + `carousel.pptx` — 8–12 slide carousel with PPTX ready for design
  - `infographic.md` — visual concept spec + full DALL-E/ChatGPT image prompt + caption
  - `short_post.md` — punchy 150–250 word post with bullet takeaways
- **Image generation prompts** — consolidated in `image_prompts.md` for use with ChatGPT / DALL-E / Midjourney

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/YOUR_USERNAME/linkedin-articles.git
cd linkedin-articles
pip install -r requirements.txt

# 2. Install poppler (required for PDF→image conversion)
brew install poppler          # macOS
# sudo apt-get install poppler-utils  # Ubuntu/Debian

# 3. Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Create a manifest for your conference run
python main.py init
# Edit manifest.yaml with conference details

# 5. Drop artefacts into data/raw/ and run
python main.py run --input data/raw/ --manifest manifest.yaml
```

---

## Installation

### Requirements

- Python 3.11+
- `poppler` system library (for PDF processing)
- An [Anthropic API key](https://console.anthropic.com/)

### System dependencies

| OS | Command |
|---|---|
| macOS | `brew install poppler` |
| Ubuntu/Debian | `sudo apt-get install poppler-utils` |
| Windows | Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/) |

### Python dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Single file

```bash
python main.py run --input path/to/slides.pdf
```

### Batch (whole directory)

```bash
python main.py run --input data/raw/ --manifest manifest.yaml
```

### Force a specific format

```bash
python main.py run --input data/raw/ --format article
python main.py run --input data/raw/ --format carousel
python main.py run --input data/raw/ --format all
```

### Skip review gates (automation)

```bash
python main.py run --input data/raw/ --no-review
```

### Custom output directory

```bash
python main.py run --input data/raw/ --output-dir ~/Desktop/my-conference-content
```

### View covered topics

```bash
python main.py topics
```

---

## CLI Reference

```
Commands:
  run     Process artefacts and generate LinkedIn content
  init    Create a manifest.yaml template in the current directory
  topics  Show all previously covered topics

Options for `run`:
  -i, --input PATH         File or directory to process  [required]
  -m, --manifest PATH      manifest.yaml path (default: manifest.yaml)
  -f, --format CHOICE      article | carousel | infographic | short_post | all | auto
  -o, --output-dir PATH    Output directory
  --no-review              Skip human review gates
```

---

## Configuration

### manifest.yaml

Created by `python main.py init`. Key fields:

| Field | Purpose |
|---|---|
| `conference_name` | Used in generated content and file naming |
| `conference_date` | Included in byline and captions |
| `speakers` | Name/role/company list for attribution |
| `file_speakers` | Map specific filenames to their speaker |
| `max_pages_per_pdf` | Limit API calls on large decks (default: 30) |

See [docs/manifest-reference.md](docs/manifest-reference.md) for the full field reference.

### config/persona.md

Defines your LinkedIn voice — tone, style rules, banned phrases, audience, and topics you care about. Edit this to match how you actually write. See [docs/persona-guide.md](docs/persona-guide.md).

### config/hashtags.json

Curated hashtag tiers (tier1–tier3, conference, community). The generator picks the most relevant 8 per run. Edit to add or reorder tags.

---

## Output Structure

Each run creates a timestamped directory:

```
data/output/2025-05-15_data-ai-summit/
  article.md          ← paste directly into LinkedIn
  carousel.md         ← text version of all slides
  carousel.pptx       ← dark-themed deck, square format (10×10in)
  infographic.md      ← visual concept + image prompt + caption
  short_post.md       ← punchy post, ready to paste
  image_prompts.md    ← all DALL-E/ChatGPT prompts consolidated
  run_summary.json    ← metadata for this run
```

---

## Project Structure

```
linkedin-articles/
├── main.py                    # CLI entry point
├── pipeline/
│   ├── ingest.py              # file discovery + deduplication
│   ├── extract.py             # Claude Vision + pdfplumber extraction
│   ├── synthesize.py          # theme clustering + hot-take detection
│   ├── format_recommender.py  # rule-based + LLM format selection
│   ├── generate.py            # Jinja2 prompt rendering + Claude generation
│   └── export.py              # markdown + PPTX output
├── templates/
│   ├── article_prompt.j2
│   ├── carousel_prompt.j2
│   ├── infographic_prompt.j2
│   └── short_post_prompt.j2
├── config/
│   ├── persona.md             # your LinkedIn voice
│   ├── hashtags.json          # curated hashtag tiers
│   └── manifest_template.yaml
├── data/
│   ├── raw/                   # drop artefacts here
│   ├── processed/             # extracted JSON + hash log
│   └── output/                # generated content runs
├── docs/                      # extended documentation
└── topics_log.json            # cross-run topic deduplication log
```

---

## Docs

- [Getting Started](docs/getting-started.md)
- [Manifest Reference](docs/manifest-reference.md)
- [Output Formats](docs/output-formats.md)
- [Persona Guide](docs/persona-guide.md)
- [Advanced Usage](docs/advanced-usage.md)

---

## Model

Uses `claude-sonnet-4-6` for all extraction, synthesis, and generation steps. Approximately **3–8 API calls per artefact** depending on page count, plus synthesis and generation calls.

Rough cost estimate for a 20-slide conference deck:
- Extraction: ~20 Vision calls (~$0.05–$0.15)
- Synthesis + generation: 2–5 calls (~$0.02–$0.05)
- **Total: ~$0.10–$0.25 per run** (varies with content density)

---

## License

MIT
