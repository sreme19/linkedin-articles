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
- **Editorial memory** — learns from your final edited posts, not only the first AI draft
- **Private post QA** — checks drafts for privacy risks, repeated topic clusters, and style regressions
- **Safe public examples** — can use a curated source-linked set of public business examples (Apple, Microsoft, LEGO, etc.) without leaking private meeting context
- **Output formats**:
  - `article.md` — 600–900 word long-form LinkedIn article
  - `carousel.md` + `carousel.pptx` — 8–12 slide carousel with PPTX ready for design
  - `infographic.md` — visual concept spec + full DALL-E/ChatGPT image prompt + caption
  - `short_post.md` — punchy 150–250 word post with bullet takeaways
  - `non_ai_post.md` — privacy-safe professional reflection from meeting notes, without company or personal details
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
python main.py run --input data/private/meeting-notes --privacy-mode --format non_ai_post
python main.py run --input data/raw/ --format all
```

### Private meeting notes

For private notes, put `.txt`, `.md`, `.docx`, or text-readable `.pdf` files under `data/private/` or `data/meeting_notes/` and run with `--privacy-mode`:

```bash
python main.py run --input data/private/ --privacy-mode --format non_ai_post
```

Privacy mode refuses to process in-repo files unless git is already ignoring them, anonymizes extracted text before synthesis, writes output to ignored `data/private_output/`, and skips tracked topic/post logs.

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

### Editorial memory and post QA

The app has a small "rules engine" for learning your editorial preferences.
This is especially useful for private meeting notes where you may edit the AI draft
before posting. The important idea is:

1. The app generates a draft.
2. You edit it into the final version you actually like.
3. You record that final version.
4. Future runs use that final version as a style and topic signal.

Record the user-edited final version after you publish or approve a draft:

```bash
python main.py record-final \
  --file data/private_output/YYYY-MM-DD_topic/non_ai_post.md \
  --mode management_reflection \
  --topic "Company phase alignment" \
  --notes "What changed and why the final worked"
```

This writes to `data/final_posts_log.json`. Treat that file as public-safe:
only record final posts that you would be comfortable committing to git.

Check a draft for privacy risks, repeated topic clusters, and style issues:

```bash
python main.py check-post \
  --file data/private_output/YYYY-MM-DD_topic/non_ai_post.md \
  --privacy-mode \
  --mode management_reflection
```

The most common modes are:

| Mode | Use it when |
|---|---|
| `management_reflection` | Turning private work notes into a broad leadership or management post |
| `career_transition` | Writing about role changes, transitions, or professional evolution |
| `leadership_lesson` | Writing a general operating lesson for leaders or managers |
| `ai_data_practitioner` | Writing about data, analytics, AI, agents, or technical implementation |
| `public_example_analysis` | Starting from a public business example rather than private notes |

Where the rules live:

| File | What it does |
|---|---|
| `config/editorial_learnings.json` | Stores writing rules learned from final approved posts |
| `config/topic_clusters.json` | Groups similar ideas so the app can warn about repeats |
| `data/final_posts_log.json` | Stores final user-approved posts that future runs learn from |
| `data/public_examples.json` | Stores 100 safe public business examples with source URLs |
| `pipeline/editorial.py` | Runs the rules: mode detection, repeat checks, example selection, and QA |

For a deeper walkthrough, read [Editorial Memory](docs/editorial-memory.md).

---

## CLI Reference

```
Commands:
  run           Process artefacts and generate LinkedIn content
  init          Create a manifest.yaml template in the current directory
  topics        Show all previously covered topics
  check-post    Check one draft for privacy, style, and topic-cluster issues
  record-final  Save a user-approved final post so future runs learn from it

Options for `run`:
  -i, --input PATH         File or directory to process  [required]
  -m, --manifest PATH      manifest.yaml path (default: manifest.yaml)
  -f, --format CHOICE      article | carousel | infographic | short_post | hot_take | reaction_post | story_post | non_ai_post | all | auto
  -o, --output-dir PATH    Output directory
  --no-review              Skip human review gates
  --privacy-mode           Enforce ignored inputs, anonymized synthesis, and ignored private output
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
│   ├── editorial.py           # editorial memory, repeat checks, public examples
│   └── export.py              # markdown + PPTX output
├── templates/
│   ├── article_prompt.j2
│   ├── carousel_prompt.j2
│   ├── infographic_prompt.j2
│   └── short_post_prompt.j2
├── config/
│   ├── persona.md             # your LinkedIn voice
│   ├── hashtags.json          # curated hashtag tiers
│   ├── editorial_learnings.json # final-post style rules
│   ├── topic_clusters.json    # semantic-ish repeat detection clusters
│   └── manifest_template.yaml
├── data/
│   ├── raw/                   # drop public artefacts here
│   ├── private/               # ignored private source notes
│   ├── meeting_notes/         # ignored private meeting notes
│   ├── processed/             # extracted JSON + hash log
│   ├── output/                # generated public content runs
│   ├── private_output/        # ignored privacy-mode output
│   ├── final_posts_log.json   # public-safe final posts used for learning
│   └── public_examples.json   # source-linked public business examples
├── docs/                      # extended documentation
└── topics_log.json            # cross-run topic deduplication log
```

---

## Docs

- [Getting Started](docs/getting-started.md)
- [Manifest Reference](docs/manifest-reference.md)
- [Output Formats](docs/output-formats.md)
- [Persona Guide](docs/persona-guide.md)
- [Editorial Memory](docs/editorial-memory.md)
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
