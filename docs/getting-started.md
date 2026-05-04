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

Supported formats: **PDF, PNG, JPG, JPEG, WEBP**

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
