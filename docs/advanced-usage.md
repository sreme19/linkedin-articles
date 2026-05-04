# Advanced Usage

---

## Processing a single file

You don't need a full conference batch. Single-file mode works identically:

```bash
python main.py run --input path/to/single_slide.jpg --format short_post
```

No manifest required — it falls back to defaults.

---

## Skipping deduplication

By default, files are hashed and skip re-processing. To re-process everything:

```bash
rm data/processed/seen_hashes.json
python main.py run --input data/raw/
```

---

## Generating all four formats at once

```bash
python main.py run --input data/raw/ --format all
```

This takes longer and costs more but gives you maximum optionality. Useful when you're unsure which format will perform best with a given piece of content.

---

## Controlling API costs

**Reduce pages per PDF:**
```yaml
# manifest.yaml
max_pages_per_pdf: 10
```

**Process only image files (skip PDFs entirely):**
```bash
# Move only your JPG/PNG files to raw/ for this run
python main.py run --input data/raw/
```

**Use `--no-review` for faster iteration:**
```bash
python main.py run --input data/raw/ --format short_post --no-review
```

---

## Custom output directory

```bash
python main.py run --input data/raw/ --output-dir ~/Desktop/summit-2025-content
```

Useful for organising output outside the project directory, or for sharing output with a team.

---

## Viewing and managing covered topics

See all topics logged across runs:
```bash
python main.py topics
```

Reset the topics log (start fresh):
```bash
echo '{"topics": []}' > topics_log.json
```

---

## Re-using extracted data

Extracted artefact JSON is saved to `data/processed/` after each run. If extraction succeeded but synthesis/generation failed, you can inspect the extracted data:

```bash
cat data/processed/2025-05-15_data-ai-summit_extracted.json | python -m json.tool
```

This is useful for debugging or for manually crafting content when the generated output misses the mark.

---

## Editing the prompt templates

All four content format prompts live in `templates/`. They're [Jinja2](https://jinja.palletsprojects.com/) templates rendered with the synthesis data before being sent to Claude.

To change the article length:
```
# templates/article_prompt.j2
- Length: 600–900 words
# change to:
- Length: 400–600 words
```

To add a new instruction:
```
# Add to the ARTICLE REQUIREMENTS section
- Always mention the conference name in the first paragraph
- End every article with a book recommendation
```

---

## Adding a new output format

1. Create `templates/my_format_prompt.j2`
2. Add `"my_format"` to the choices in `main.py` (`--format` option)
3. Add a handler in `pipeline/export.py` (`_export_my_format`)
4. Add the description to `FORMAT_DESCRIPTIONS` in `pipeline/format_recommender.py`

The `generate_content` function in `pipeline/generate.py` will automatically pick up the new template by name.
