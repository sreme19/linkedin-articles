# Output Formats

Each format is designed for a different use case and posting cadence.

---

## article.md — Long-form LinkedIn Article

**When to use:** Deep conferences with multiple speakers and dense content. Best for thought leadership positioning.

**Length:** 600–900 words

**Structure:**
1. Hook — bold claim or surprising statistic (2–3 sentences)
2. Context — what conference, what was the dominant conversation
3. Insights — 3–5 numbered, each evidence-backed
4. Your take — opinionated synthesis paragraph
5. CTA — a question that practitioners want to answer

**How to post:**
- Open LinkedIn → Write article
- Paste content directly
- Add a header image (use the infographic image prompt for one that matches)

---

## carousel.md + carousel.pptx — Slide Carousel

**When to use:** Visual, slide-heavy conferences. High engagement format on LinkedIn.

**Slide count:** 8–12

**Slide types:**
- `title` — hook headline + conference name
- `content` — numbered, headline + 3 bullets max
- `stat` — single large number + context + source
- `quote` — speaker quote + attribution
- `cta` — follow prompt + engagement question

**The PPTX:**
- Square format (10×10 inches = LinkedIn optimal)
- Dark theme (`#0D1117` background, `#0077B5` LinkedIn blue accents)
- Open in PowerPoint or Google Slides to add images from `image_prompts.md`
- Export as PDF, then upload as a document post to LinkedIn (not as slides — LinkedIn's native carousel is document-based)

**How to post:**
1. Open `carousel.pptx` in PowerPoint / Google Slides
2. Add visuals from image prompts (paste generated images into each slide)
3. Export as PDF
4. LinkedIn → Start a post → Add document → Upload PDF
5. Paste `caption` from `carousel.md` as your post text

---

## infographic.md — Single-Image Infographic

**When to use:** When there's a clear framework, taxonomy, or comparison to visualise. Best with strong data points.

**Contains:**
- Visual concept description (what type of graphic + layout)
- Content structure (what goes where)
- Full DALL-E/ChatGPT image prompt (~150–200 words)
- LinkedIn caption (150–200 words)

**How to generate the image:**
1. Open ChatGPT or DALL-E
2. Paste the image prompt from `image_prompts.md`
3. Download the generated image
4. LinkedIn → Start a post → Add image → Upload
5. Paste the caption

**Tip:** If the generated image isn't quite right, add `"regenerate with slight variations"` or adjust the prompt. The prompt is designed for dark-themed, professional vector-style graphics.

---

## short_post.md — Short Punchy Post

**When to use:** High-frequency posting. Works best when there's a strong hot take to lead with. Lowest effort, highest posting cadence.

**Length:** 150–250 words

**Structure:**
- Line 1: Bold opening statement (often a hot take)
- 3–5 bullet takeaways
- Closing question

**How to post:**
- LinkedIn → Start a post → Paste directly
- No image needed (though adding the infographic image can increase reach)

---

## image_prompts.md — Consolidated Image Prompts

All DALL-E/ChatGPT prompts in one file:
- One per carousel slide that needs a visual
- One for the infographic
- Style guidelines baked in (dark theme, professional, no text in image)

**Tip for best results:**
- Use ChatGPT (GPT-4o) or DALL-E 3 for the cleanest output
- Add `"1080x1080 pixels, square format"` if the tool doesn't default to square
- For carousel slides, generate each image separately and insert into the PPTX
