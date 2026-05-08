import json
from pathlib import Path
from typing import Dict, List

import anthropic
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _pick_hashtags(hashtags_data: Dict, n: int = 8) -> str:
    pool = (
        hashtags_data.get("tier1", [])[:3]
        + hashtags_data.get("tier2", [])[:3]
        + hashtags_data.get("tier3", [])[:2]
        + hashtags_data.get("conference", [])[:1]
    )
    seen: set = set()
    result = []
    for tag in pool:
        if tag not in seen and len(result) < n:
            seen.add(tag)
            result.append(tag)
    return " ".join(result)


def generate_content(
    format_name: str,
    synthesis: Dict,
    manifest: Dict,
    persona: str,
    hashtags: Dict,
) -> Dict:
    client = anthropic.Anthropic()

    privacy_mode = bool(manifest.get("privacy_mode"))
    context = {
        "persona": persona,
        "conference_name": manifest.get("conference_name", "the conference"),
        "conference_date": manifest.get("conference_date", ""),
        "privacy_mode": privacy_mode,
        "professional_context": manifest.get("professional_context", "long-term leadership experience"),
        "privacy_rules": manifest.get("privacy_rules", []),
        "conference_summary": synthesis.get("conference_summary", ""),
        "themes": synthesis.get("themes", []),
        "hot_takes": synthesis.get("hot_takes", []),
        "top_quotes": synthesis.get("top_quotes", []),
        "top_data_points": synthesis.get("top_data_points", []),
        "top_technologies": synthesis.get("top_technologies", []),
        "covered_topics": [t["topic"] for t in synthesis.get("_covered_topics", [])],
        "best_hook": synthesis.get("best_hook", ""),
        "hashtags": _pick_hashtags(hashtags),
        "editorial": synthesis.get("_editorial", {}),
    }

    template = _env.get_template(f"{format_name}_prompt.j2")
    prompt = template.render(**context)

    SHORT_FORMATS = {"short_post", "hot_take", "reaction_post", "story_post", "non_ai_post"}
    system_msg = "You are a LinkedIn content writer. Follow all instructions precisely."
    if privacy_mode:
        system_msg += (
            " Privacy is mandatory: do not reveal or infer company names, personal names, "
            "client names, project names, internal tools, emails, URLs, or identifying details."
        )
    if format_name == "carousel":
        system_msg = (
            "You are a LinkedIn content writer. "
            "Return ONLY valid JSON — no markdown fences, no preamble, no trailing text."
        )
    elif format_name in SHORT_FORMATS:
        system_msg = (
            "You are a LinkedIn content writer. Follow all instructions precisely. "
            "Be ruthlessly concise — cut any sentence that doesn't earn its place."
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_msg,
        messages=[{"role": "user", "content": prompt}],
    )

    content_text = response.content[0].text

    result: Dict = {
        "format": format_name,
        "content": content_text,
        "conference": manifest.get("conference_name", ""),
    }

    if format_name == "carousel":
        try:
            start = content_text.find("{")
            end = content_text.rfind("}") + 1
            if start >= 0 and end > start:
                result["slides_data"] = json.loads(content_text[start:end])
            else:
                result["slides_data"] = None
        except json.JSONDecodeError:
            result["slides_data"] = None

    return result
