# Persona Guide

`config/persona.md` is the most important configuration file. It defines your LinkedIn voice — and every piece of generated content is shaped by it. The default is a solid starting point, but the output improves significantly once it matches how you actually write.

---

## What the persona file contains

| Section | Purpose |
|---|---|
| Who I am | Your role, background, and credibility markers |
| My perspective | Your worldview and what makes you different from generic AI commentators |
| Writing style | Rules for tone, sentence structure, and what to avoid |
| Tone calibration | Analogies that help the model understand the register |
| Topics I care about | Your subject matter focus — shapes what gets emphasised in synthesis |
| My audience | Who you're writing for — affects vocabulary and assumed knowledge level |

---

## How to customise it

### 1. Add your genuine opinions

Replace the default perspective with real things you believe about the industry:

```markdown
## My perspective
- I believe RAG is being used as a crutch to avoid fixing poor data quality
- Agent frameworks have too much abstraction for most production use cases
- The "AI engineer" title is mostly data engineering with a rebrand
```

The more specific and opinionated, the better. The model uses this to generate takes that actually sound like you.

### 2. Capture your style rules

Add specific patterns from your past posts that work well:

```markdown
## Writing style
- I start LinkedIn posts with a one-line statement, never a question
- I use em dashes a lot — they feel like an aside in a conversation
- I never use bullet points with more than 5 words per bullet
- I attribute claims specifically: "X said Y at Z conference" not "industry experts say"
```

### 3. Add banned phrases

The default includes common LinkedIn clichés. Add your personal pet peeves:

```markdown
## Banned phrases
- "excited to share"
- "at the end of the day"
- "paradigm shift"
- "the future is now"
- "low-hanging fruit"
- any phrase you'd roll your eyes at reading
```

### 4. Describe your audience precisely

Generic "data professionals" produces generic content. Be specific:

```markdown
## My audience
Senior data engineers and ML platform leads at companies with 100+ person data orgs,
who are evaluating whether to build or buy agentic tooling. They're sceptical of hype
but genuinely trying to figure out what's real. They don't need AI explained to them.
```

---

## Testing your persona

After editing, run a quick test with a single slide image:

```bash
python main.py run --input path/to/one_slide.png --format short_post
```

Read the output. Does it sound like you? If not, adjust the persona and try again. The short post format gives the fastest feedback loop.

---

## What NOT to put in persona.md

- Conference-specific context (that goes in `manifest.yaml`)
- Technical instructions to the model (the prompt templates handle that)
- Formatting requirements like "use markdown headers" (LinkedIn doesn't render them)
