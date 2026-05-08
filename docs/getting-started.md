# Getting Started

This guide walks you through your first run end-to-end.

---

## 1. Prerequisites

- Python 3.11+
- `poppler` for PDF-to-image conversion
- Anthropic API key ([get one here](https://console.anthropic.com/))

Install poppler:
```bash
brew install poppler        # macOS
sudo apt-get install poppler-utils  # Ubuntu/Debian
```

---

## 2. Install

```bash
git clone https://github.com/YOUR_USERNAME/linkedin-articles.git
cd linkedin-articles
pip install -r requirements.txt
```

---

## 3. Configure API key

```bash
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 4. Create a manifest

```bash
python main.py init
```

Edit the generated `manifest.yaml`:

```yaml
conference_name: "Data + AI Summit 2025"
conference_date: "2025-05-15"
location: "San Francisco, CA"
speaker: "Various Speakers"
speakers:
  - name: "Jane Smith"
    role: "Head of AI"
    company: "Databricks"
```

The more detail you provide here, the better the attribution in generated content.

---

## 5. Add your artefacts

Drop your files into `data/raw/`:

```
data/raw/
  keynote_slides.pdf
  panel_discussion.pdf
  photo_slide_01.jpg
  photo_slide_02.jpg
```

Supported formats: **PDF, PNG, JPG, JPEG, WEBP, TXT, MD, DOCX**

---

## 6. Run

```bash
python main.py run --input data/raw/ --manifest manifest.yaml
```

The pipeline will:
1. Scan and deduplicate files
2. Extract content from each (Claude Vision for images, pdfplumber + Vision for PDFs)
3. Synthesise themes and detect hot takes
4. **Show you a synthesis brief and ask for confirmation** (type `y` to continue)
5. Recommend content formats based on what was found
6. **Ask you to confirm or change the format selection**
7. Generate content
8. Export to `data/output/YYYY-MM-DD_conference-name/`

---

## 7. Use the output

Open `data/output/YYYY-MM-DD_conference-name/`:

| File | What to do with it |
|---|---|
| `article.md` | Paste directly into LinkedIn's article editor |
| `short_post.md` | Paste directly into LinkedIn post composer |
| `carousel.md` | Text reference for each slide |
| `carousel.pptx` | Open in PowerPoint or Google Slides, adjust visuals, export as PDF for LinkedIn |
| `infographic.md` | Read the image prompt → paste into ChatGPT or DALL-E → paste caption |
| `image_prompts.md` | All image prompts in one place |

---

## 8. Customise your persona

Before your second run, edit `config/persona.md` to match your actual writing style. The default is a reasonable starting point but the output improves significantly once it reflects how you actually write.

See [Persona Guide](persona-guide.md) for details.

---

## Private Meeting Notes

For confidential meeting notes, use privacy mode and keep files under an ignored folder:

```bash
mkdir -p data/private/meeting-notes
python main.py run --input data/private/meeting-notes --privacy-mode --format non_ai_post
```

Privacy mode:

- refuses to process in-repo files that are tracked or not ignored by git
- anonymizes extracted notes before synthesis
- writes output to ignored `data/private_output/` by default
- skips tracked topic and post logs
- generates `non_ai_post.md` without company names, personal names, client names, project names, URLs, emails, or identifying details

### Private notes workflow for beginners

Use this workflow when you have meeting notes, planning notes, or personal work
reflections that should not reveal your company or colleagues.

1. Put the private files in `data/private/meeting-notes/`.
2. Run the app with `--privacy-mode`.
3. Open the generated `non_ai_post.md`.
4. Edit it into the version you would actually post.
5. Run `check-post` to catch privacy and style mistakes.
6. If the final post is public-safe, record it with `record-final` so the app learns.

Example:

```bash
python main.py run \
  --input data/private/meeting-notes \
  --privacy-mode \
  --format non_ai_post
```

Check the generated post:

```bash
python main.py check-post \
  --file data/private_output/YYYY-MM-DD_work-notes/non_ai_post.md \
  --privacy-mode \
  --mode management_reflection
```

If the check says `"ok": true`, and you are happy with the final post, record it:

```bash
python main.py record-final \
  --file data/private_output/YYYY-MM-DD_work-notes/non_ai_post.md \
  --mode management_reflection \
  --topic "Company phase alignment" \
  --notes "Final version used broader leadership framing and avoided exact tenure."
```

Important: `record-final` writes to `data/final_posts_log.json`, which is tracked
by git. Only record posts that are already safe to publish publicly.

### What "mode" means

A mode tells the app what kind of post you are writing. It changes the style
checks and the examples the app prefers.

| Mode | Plain-English meaning |
|---|---|
| `management_reflection` | A leadership or management lesson from private work notes |
| `career_transition` | A post about changing roles, stepping back, or career evolution |
| `leadership_lesson` | A general lesson for managers and operators |
| `ai_data_practitioner` | A technical post about data, AI, analytics, or agents |
| `public_example_analysis` | A post built around a public company example |

If you are unsure, use `management_reflection` for private management notes.

### Why the app records final posts

The first AI draft is often not the best version. You may improve the hook,
remove identifying details, add a public example, or adjust the tone. The final
edited post is the strongest signal of your actual taste.

When you run `record-final`, the app stores:

- the final text
- the post mode
- the topic
- the detected topic cluster
- the QA check result
- your note about why the final worked

Future runs use this memory to avoid repeating the same topic and to steer
toward the style you approved.
