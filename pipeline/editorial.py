import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

FINAL_POSTS_LOG = DATA_DIR / "final_posts_log.json"
EDITORIAL_LEARNINGS = CONFIG_DIR / "editorial_learnings.json"
TOPIC_CLUSTERS = CONFIG_DIR / "topic_clusters.json"
PUBLIC_EXAMPLES = DATA_DIR / "public_examples.json"


PRIVATE_RISK_PATTERNS = [
    (re.compile(r"\b8\s+years\b|\beight\s+years\b", re.IGNORECASE), "exact tenure"),
    (re.compile(r"\bmy company\b|\bmy employer\b", re.IGNORECASE), "private employer hint"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "email address"),
    (re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE), "URL"),
    (re.compile(r"\b[A-Z]{2,}-\d{2,}\b"), "internal ticket or ID"),
]

STYLE_PATTERNS = [
    (re.compile(r"\bexcited to share\b", re.IGNORECASE), "generic LinkedIn opener"),
    (re.compile(r"\bhumbled\b", re.IGNORECASE), "generic humility phrase"),
    (re.compile(r"\bgame-changer\b", re.IGNORECASE), "cliche"),
    (re.compile(r"\bparadigm shift\b", re.IGNORECASE), "cliche"),
    (re.compile(r"\bin today's fast-paced world\b", re.IGNORECASE), "cliche"),
]


def _read_json(path: Path, default: Dict) -> Dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def load_editorial_learnings() -> Dict:
    return _read_json(EDITORIAL_LEARNINGS, {"global_rules": [], "mode_rules": {}, "approved_examples": []})


def load_topic_clusters() -> Dict:
    return _read_json(TOPIC_CLUSTERS, {"clusters": []})


def load_final_posts() -> Dict:
    return _read_json(FINAL_POSTS_LOG, {"final_posts": []})


def load_public_examples() -> List[Dict]:
    data = _read_json(PUBLIC_EXAMPLES, {"examples": []})
    return data.get("examples", [])


def infer_post_mode(synthesis: Dict, manifest: Dict, requested: Optional[str] = None) -> str:
    if requested:
        return requested
    text = _synthesis_text(synthesis)
    if manifest.get("privacy_mode"):
        if _contains_any(text, ["career", "role", "transition", "stepping down", "leave"]):
            if _contains_any(text, ["building", "scaling", "optim", "simplifying", "phase", "exploration"]):
                return "management_reflection"
            return "career_transition"
        if _contains_any(text, ["leadership", "manager", "management", "operational", "organization", "organisation"]):
            return "management_reflection"
    if _contains_any(text, ["ai", "agent", "llm", "data", "analytics", "pipeline"]):
        return "ai_data_practitioner"
    return "leadership_lesson"


def detect_topic_clusters(text: str) -> List[Dict]:
    lowered = text.lower()
    matches = []
    for cluster in load_topic_clusters().get("clusters", []):
        keywords = cluster.get("keywords", [])
        hits = [kw for kw in keywords if kw.lower() in lowered]
        if hits:
            matches.append({
                "id": cluster.get("id", ""),
                "label": cluster.get("label", ""),
                "hits": hits[:5],
            })
    return matches


def recent_final_clusters(limit: int = 12) -> List[str]:
    posts = load_final_posts().get("final_posts", [])
    clusters: List[str] = []
    for post in reversed(posts[-limit:]):
        cluster = post.get("topic_cluster")
        if cluster and cluster not in clusters:
            clusters.append(cluster)
    return clusters


def repeat_warnings(synthesis: Dict, final_limit: int = 12) -> List[str]:
    text = _synthesis_text(synthesis)
    current = {c["id"] for c in detect_topic_clusters(text)}
    recent = set(recent_final_clusters(final_limit))
    warnings = []
    for cluster in sorted(current & recent):
        warnings.append(f"Potential repeat: current synthesis overlaps recent final-post cluster `{cluster}`.")
    return warnings


def select_public_examples(synthesis: Dict, mode: str, limit: int = 3) -> List[Dict]:
    if mode not in {"management_reflection", "leadership_lesson", "public_example_analysis"}:
        return []
    text = _synthesis_text(synthesis)
    clusters = {c["id"] for c in detect_topic_clusters(text)}
    examples = load_public_examples()
    scored = []
    for example in examples:
        tags = set(example.get("tags", []))
        score = len(clusters & tags)
        if mode in tags:
            score += 2
        if any(word in text.lower() for word in [str(t).replace("_", " ") for t in tags]):
            score += 1
        if score:
            scored.append((score, example))
    if not scored:
        scored = [(1, ex) for ex in examples if "management_reflection" in ex.get("tags", [])]
    return [ex for _, ex in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def build_editorial_context(synthesis: Dict, manifest: Dict, requested_mode: Optional[str] = None) -> Dict:
    mode = infer_post_mode(synthesis, manifest, requested_mode)
    learnings = load_editorial_learnings()
    synthesis_clusters = detect_topic_clusters(_synthesis_text(synthesis))
    return {
        "post_mode": mode,
        "global_rules": learnings.get("global_rules", []),
        "mode_rules": learnings.get("mode_rules", {}).get(mode, []),
        "approved_examples": learnings.get("approved_examples", [])[-3:],
        "topic_clusters": synthesis_clusters,
        "recent_final_clusters": recent_final_clusters(),
        "repeat_warnings": repeat_warnings(synthesis),
        "public_examples": select_public_examples(synthesis, mode),
    }


def enrich_synthesis(synthesis: Dict, manifest: Dict, requested_mode: Optional[str] = None) -> Dict:
    enriched = dict(synthesis)
    enriched["_editorial"] = build_editorial_context(synthesis, manifest, requested_mode)
    return enriched


def validate_post_text(text: str, privacy_mode: bool = False, mode: str = "") -> Dict:
    issues = []
    for pattern, label in STYLE_PATTERNS:
        if pattern.search(text):
            issues.append({"severity": "warning", "type": "style", "message": f"Avoid {label}."})
    if privacy_mode:
        for pattern, label in PRIVATE_RISK_PATTERNS:
            if pattern.search(text):
                issues.append({"severity": "error", "type": "privacy", "message": f"Private post includes {label}."})
    if mode == "management_reflection":
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if len(first_line.split()) < 5:
            issues.append({"severity": "warning", "type": "style", "message": "Management post should open with a strong headline or hook."})
        if not re.search(r"\b(building|scaling|tightening|simplifying|optimizing|optimising|reinvention|exploration|operational)\b", text, re.IGNORECASE):
            issues.append({"severity": "warning", "type": "content", "message": "Management reflection may be missing company-phase language."})
    clusters = detect_topic_clusters(text)
    return {
        "ok": not any(issue["severity"] == "error" for issue in issues),
        "issues": issues,
        "topic_clusters": clusters,
        "word_count": len(re.findall(r"\b\w+\b", text)),
    }


def record_final_post(
    post_text: str,
    source_generated_file: str = "",
    mode: str = "",
    topic: str = "",
    notes: str = "",
) -> Dict:
    clusters = detect_topic_clusters(post_text)
    topic_cluster = clusters[0]["id"] if clusters else ""
    log = load_final_posts()
    entry = {
        "id": f"{date.today().isoformat()}-{uuid.uuid4().hex[:6]}",
        "date": date.today().isoformat(),
        "mode": mode or "unknown",
        "topic": topic,
        "topic_cluster": topic_cluster,
        "topic_clusters": clusters,
        "source_generated_file": source_generated_file,
        "post_text": post_text,
        "notes": notes,
        "checks": validate_post_text(post_text, privacy_mode=True, mode=mode),
    }
    log.setdefault("final_posts", []).append(entry)
    FINAL_POSTS_LOG.write_text(json.dumps(log, indent=2))
    return entry


def _synthesis_text(synthesis: Dict) -> str:
    parts = [
        synthesis.get("conference_summary", ""),
        synthesis.get("best_hook", ""),
        " ".join(t.get("title", "") + " " + t.get("insight", "") for t in synthesis.get("themes", [])),
        " ".join(h.get("claim", "") + " " + h.get("why_surprising", "") for h in synthesis.get("hot_takes", [])),
        " ".join(synthesis.get("top_data_points", [])),
    ]
    return "\n".join(parts)


def _contains_any(text: str, needles: List[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)
