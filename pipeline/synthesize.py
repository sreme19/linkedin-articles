import json
from typing import Dict, List

import anthropic
from rich.console import Console

console = Console()

_SYNTHESIS_PROMPT = """\
You are synthesising conference insights for a LinkedIn thought leader in the data and agentic AI space.

CONFERENCE: {conference_name} ({conference_date})
SPEAKERS: {speakers}

EXTRACTED ARTEFACTS ({count} items):
{artefacts}

TOPICS ALREADY COVERED BY THIS AUTHOR (flag if we are retreading ground):
{covered_topics}

YOUR TASK:
Analyse ALL the artefacts above and return ONLY valid JSON — no other text, no markdown fences.

1. Identify the 3–5 strongest, most actionable themes across all content
2. For each theme: rate novelty as high (surprising/new), medium (evolving known idea), or low (widely discussed)
3. Identify HOT TAKES: specific claims that are counterintuitive, challenge industry consensus, or would surprise a senior data practitioner. Be specific about WHY each is surprising.
4. Pull the 3 best quotes and 3 best data points from all artefacts
5. Write one compelling LinkedIn hook line (the sentence that stops the scroll)
6. Recommend one primary content format: article, carousel, infographic, or short_post — with a 5-word reason

JSON format:
{{
  "conference_summary": "2–3 sentence overview of dominant themes at the conference",
  "themes": [
    {{
      "title": "Theme name (3–5 words)",
      "insight": "Core insight in 1–2 sentences",
      "evidence": ["supporting point 1", "supporting point 2"],
      "sources": ["speaker / artefact reference"],
      "novelty": "high|medium|low",
      "previously_covered": false
    }}
  ],
  "hot_takes": [
    {{
      "claim": "The specific counterintuitive claim (exact words where possible)",
      "source": "Who said it / which artefact",
      "why_surprising": "Why this challenges conventional thinking (1 sentence)"
    }}
  ],
  "best_hook": "One sentence that would make a data practitioner stop scrolling",
  "top_quotes": ["quote text — Speaker Name, Company"],
  "top_data_points": ["statistic/number with full context and source"],
  "recommended_format": "article|carousel|infographic|short_post — reason in 5 words"
}}\
"""


def synthesize(artifacts: List[Dict], manifest: Dict, topics_log: Dict) -> Dict:
    client = anthropic.Anthropic()

    covered = [t["topic"] for t in topics_log.get("topics", [])]

    speakers = manifest.get("speakers", [])
    if speakers:
        speaker_str = ", ".join(
            f"{s.get('name', '')} ({s.get('role', '')}, {s.get('company', '')})"
            for s in speakers
        )
    else:
        speaker_str = manifest.get("speaker", "Various")

    # Summarise each artefact — keep only the richest fields to avoid context bloat
    summaries = []
    for i, art in enumerate(artifacts):
        summaries.append(
            {
                "id": i + 1,
                "source": _path_stem(art.get("source_file", "")),
                "title": art.get("title", ""),
                "key_points": art.get("key_points", [])[:6],
                "data_points": art.get("data_points", [])[:4],
                "quotes": art.get("quotes", [])[:3],
                "frameworks": art.get("frameworks", [])[:3],
                "hot_takes": art.get("hot_takes", []),
            }
        )

    prompt = _SYNTHESIS_PROMPT.format(
        conference_name=manifest.get("conference_name", "Unknown"),
        conference_date=manifest.get("conference_date", ""),
        speakers=speaker_str,
        count=len(artifacts),
        artefacts=json.dumps(summaries, indent=2),
        covered_topics=json.dumps(covered[:20]) if covered else "[]",
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            # Attach previously-covered matches for use downstream
            result["_covered_topics"] = [
                t
                for t in topics_log.get("topics", [])
                if any(
                    theme.get("title", "").lower() in t["topic"].lower()
                    for theme in result.get("themes", [])
                )
            ]
            return result
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Warning: could not parse synthesis JSON: {e}[/yellow]")

    return {
        "conference_summary": text[:300],
        "themes": [],
        "hot_takes": [],
        "best_hook": "",
        "top_quotes": [],
        "top_data_points": [],
        "recommended_format": "article",
        "_covered_topics": [],
    }


def _path_stem(filepath: str) -> str:
    from pathlib import Path as _Path
    return _Path(filepath).name if filepath else ""
