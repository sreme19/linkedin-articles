# Editorial Memory

This guide explains the editorial rules engine in beginner-friendly terms.

The goal is simple: the app should learn from the posts you actually approve,
not only from the AI drafts it creates.

---

## The Problem It Solves

Without editorial memory, the app can make these mistakes:

- repeat the same idea in different words
- mention private details like exact tenure
- generate a post that sounds too much like a private resignation note
- miss the tone you created in your final edited version
- avoid useful public examples even when they would make the post stronger

Editorial memory adds a lightweight feedback loop.

---

## The Feedback Loop

1. Run the app and generate a draft.
2. Edit the draft manually.
3. Check the edited draft with `check-post`.
4. Record the final version with `record-final`.
5. Future generations use that final version as guidance.

In other words:

```text
Generated draft -> Your edited final -> Recorded learning -> Better future drafts
```

---

## Commands

### Check a draft

Use this before posting or recording a final version:

```bash
python main.py check-post \
  --file data/private_output/YYYY-MM-DD_work-notes/non_ai_post.md \
  --privacy-mode \
  --mode management_reflection
```

What it checks:

- banned private details, such as exact tenure
- generic LinkedIn cliches
- repeated topic clusters
- whether the post matches the selected mode

If the command prints `"ok": true`, the draft passed the hard checks.

If it prints `"ok": false`, read the `issues` list and edit the draft.

### Record a final post

Use this after you have edited the draft into the final version:

```bash
python main.py record-final \
  --file data/private_output/YYYY-MM-DD_work-notes/non_ai_post.md \
  --mode management_reflection \
  --topic "Company phase alignment" \
  --notes "Used broad leadership framing, avoided exact tenure, and added a public example."
```

This saves the final post in `data/final_posts_log.json`.

Only record posts that are public-safe. This file is tracked by git, so do not
store confidential notes, company names, colleague names, or internal details in it.

---

## Post Modes

A post mode is a label that tells the app what style of post you want.

| Mode | Use this for |
|---|---|
| `management_reflection` | Leadership and management lessons from private notes |
| `career_transition` | Role changes, stepping back, transitions, career evolution |
| `leadership_lesson` | General lessons for leaders, operators, and managers |
| `ai_data_practitioner` | Data, analytics, AI, LLMs, agents, and implementation posts |
| `public_example_analysis` | Posts mainly built around a public company example |

For private management notes, start with:

```bash
--mode management_reflection
```

---

## Topic Clusters

A topic cluster is a group of related ideas. The app uses clusters to detect
repetition even when the wording changes.

Example:

```text
"handover", "succession", "redundancy", and "single point of failure"
```

These all belong to the `succession_redundancy` cluster.

If you recently posted about that cluster, the app can warn before generating
another similar post.

The cluster rules live here:

```text
config/topic_clusters.json
```

You can add more clusters later. Each cluster has:

- an `id`: a machine-friendly name
- a `label`: a human-friendly name
- `keywords`: words or phrases that signal the topic

---

## Editorial Learnings

Editorial learnings are the rules the app should remember about your taste.

They live here:

```text
config/editorial_learnings.json
```

Examples of rules:

- avoid exact private tenure details
- prefer a strong headline for management posts
- use company phase language when relevant
- use safe public examples when they strengthen the lesson
- do not repeat the same conceptual territory with new wording

This file also stores a short summary of why your approved example posts worked.

---

## Public Examples

The app can use public business examples to make a management post stronger.

Examples include:

- Steve Jobs refocusing Apple
- Satya Nadella shifting Microsoft toward cloud
- LEGO simplifying after over-expansion
- Netflix moving from DVD rentals to streaming

The dataset lives here:

```text
data/public_examples.json
```

Each example has:

- `title`
- `company`
- `years`
- `phase`
- `lesson`
- `tags`
- `source_url`
- `source_name`

The generation prompt tells the model to use at most one public example and not
imply that the public company is connected to your private notes.

---

## Files Added By This Feature

| File | Purpose |
|---|---|
| `pipeline/editorial.py` | The Python code for editorial memory and checks |
| `config/editorial_learnings.json` | Style rules and approved-post learnings |
| `config/topic_clusters.json` | Repeat-detection clusters |
| `data/final_posts_log.json` | Final approved posts that future runs learn from |
| `data/public_examples.json` | 100 safe, source-linked public examples |

---

## Common Beginner Questions

### Do I need to edit JSON files by hand?

Usually, no. Use `record-final` to add final posts. You only need to edit
`config/editorial_learnings.json` or `config/topic_clusters.json` if you want
to change the rules directly.

### What if `check-post` finds a problem?

Open the post file, edit the text, save it, and run `check-post` again.

### Can I record private notes with `record-final`?

No. Record only the final public-safe LinkedIn post. Do not record raw notes,
names, internal project details, or confidential context.

### Does this replace human editing?

No. It makes the next draft better, but you should still read and edit every
post before publishing.

### Does public example support scrape live data every time?

No. The app uses `data/public_examples.json`, a curated dataset of public,
source-linked examples. This keeps generation faster, more stable, and less
likely to pull in unsafe or unrelated examples.
