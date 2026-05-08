import re
import subprocess
from pathlib import Path
from typing import Dict, List


_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_PERSON_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")
_INTERNAL_ID_RE = re.compile(r"\b(?:[A-Z]{2,}-\d{2,}|[A-Z0-9]{6,}-[A-Z0-9-]{3,})\b")
_ORG_CONTEXT_RE = re.compile(
    r"\b(company|organisation|organization|org|client|customer|vendor|partner|"
    r"employer|account|tenant|brand|team|department|business unit|project|program)"
    r"\s*[:=-]\s*[^\n,;]+",
    re.IGNORECASE,
)
_AFFILIATION_RE = re.compile(
    r"\b(from|at|with|for|inside|within)\s+([A-Z][A-Za-z0-9&.'-]{2,}"
    r"(?:\s+[A-Z][A-Za-z0-9&.'-]{2,}){0,3})\b"
)

_COMPANY_HINTS = (
    "Inc", "Ltd", "LLC", "Corp", "Corporation", "Company", "Technologies",
    "Systems", "Solutions", "Labs", "Bank", "Capital", "Enterprises",
)
_COMPANY_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,3}\s+"
    rf"(?:{'|'.join(_COMPANY_HINTS)})\b"
)

_SAFE_TITLE_WORDS = {
    "AI", "API", "AWS", "CEO", "CTO", "CFO", "HR", "IT", "ML", "OKR", "SRE",
    "LinkedIn", "GitHub", "Python", "Java", "Kubernetes", "Monday", "Tuesday",
    "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}


def assert_private_path(path: str, repo_root: Path) -> None:
    """Fail if an in-repo private input could be committed by accident."""
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = repo_root / target
    target = target.resolve()
    repo_root = repo_root.resolve()

    try:
        target.relative_to(repo_root)
    except ValueError:
        return

    paths = [target]
    if target.is_dir():
        paths = [p for p in target.rglob("*") if p.is_file()]
        if not paths:
            paths = [target]

    unsafe: List[str] = []
    for item in paths:
        if item.name == ".gitkeep":
            continue
        rel = item.relative_to(repo_root)
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(rel)],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(rel)],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode == 0 or ignored.returncode != 0:
            unsafe.append(str(rel))

    if unsafe:
        preview = "\n".join(f"  - {p}" for p in unsafe[:8])
        more = "\n  ..." if len(unsafe) > 8 else ""
        raise ValueError(
            "Privacy mode refused to process files that are tracked or not ignored by git:\n"
            f"{preview}{more}\n\n"
            "Move meeting notes under data/private/ or data/meeting_notes/, or add a local ignore rule."
        )


def anonymize_text(text: str, strict: bool = False) -> str:
    text = _EMAIL_RE.sub("[email redacted]", text)
    text = _URL_RE.sub("[url redacted]", text)
    text = _PHONE_RE.sub("[phone redacted]", text)
    text = _INTERNAL_ID_RE.sub("[internal id redacted]", text)
    text = _ORG_CONTEXT_RE.sub(r"\1: [detail redacted]", text)
    text = _COMPANY_RE.sub("my organization", text)
    text = _AFFILIATION_RE.sub(r"\1 [named entity redacted]", text)

    def replace_person(match: re.Match) -> str:
        value = match.group(0)
        if any(part in _SAFE_TITLE_WORDS for part in value.split()):
            return value
        return "a colleague"

    text = _PERSON_RE.sub(replace_person, text)
    if strict:
        text = redact_titlecase_entities(text)
    return text


def redact_titlecase_entities(text: str) -> str:
    """Aggressively remove remaining name-like entities before private LLM calls."""
    def replace(match: re.Match) -> str:
        value = match.group(0)
        if any(part in _SAFE_TITLE_WORDS for part in value.split()):
            return value
        return "[named entity redacted]"

    return _PERSON_RE.sub(replace, text)


def anonymize_artifacts(artifacts: List[Dict]) -> List[Dict]:
    sanitized: List[Dict] = []
    for artifact in artifacts:
        clean = {}
        for key, value in artifact.items():
            if key == "source_file":
                clean[key] = Path(value).name if value else ""
            elif isinstance(value, str):
                clean[key] = anonymize_text(value)
            elif isinstance(value, list):
                clean[key] = [
                    anonymize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                clean[key] = value
        sanitized.append(clean)
    return sanitized


def private_manifest(manifest: Dict) -> Dict:
    return {
        **manifest,
        "privacy_mode": True,
        "conference_name": "work notes",
        "conference_date": "",
        "speaker": "Private notes",
        "speakers": [],
        "notes": (
            "Write from the perspective of someone with long-term leadership experience. "
            "Do not name the organization, colleagues, customers, teams, projects, internal tools, "
            "or any personally identifying details."
        ),
    }
