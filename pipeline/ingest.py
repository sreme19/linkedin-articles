import hashlib
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".docx"}
_DATE_RE = re.compile(r"(20\d{6}|19\d{6})")


def load_manifest(manifest_path: str) -> Dict:
    path = Path(manifest_path)
    if not path.exists():
        return {"conference_name": "Unknown Conference"}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def collect_files(input_path: str) -> List[Path]:
    p = Path(input_path)
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [p]
        console.print(f"[yellow]Unsupported file type: {p.suffix}[/yellow]")
        return []
    if p.is_dir():
        files = sorted(
            f for f in p.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        return files
    console.print(f"[red]{input_path} is not a file or directory.[/red]")
    return []


def group_by_event(files: List[Path]) -> Dict[str, List[Path]]:
    """Group files by 8-digit date found in filename. Returns dict sorted most-recent first."""
    groups: Dict[str, List[Path]] = {}
    undated: List[Path] = []
    for f in files:
        m = _DATE_RE.search(f.stem)
        if m:
            groups.setdefault(m.group(1), []).append(f)
        else:
            undated.append(f)
    if undated:
        groups["undated"] = undated
    return dict(sorted(groups.items(), key=lambda x: x[0], reverse=True))


def select_event(groups: Dict[str, List[Path]], no_review: bool = False) -> List[Path]:
    """Return files for the chosen event group. Auto-selects most recent when no_review=True."""
    if len(groups) <= 1:
        return [f for files in groups.values() for f in files]

    if no_review:
        for key, files in groups.items():
            if key != "undated":
                console.print(f"[dim]Auto-selected event: {key} ({len(files)} files)[/dim]")
                return files
        return list(groups.values())[0]

    table = Table(title="Detected Events", show_lines=True)
    table.add_column("#", style="bold", width=4)
    table.add_column("Date", style="cyan")
    table.add_column("Files", justify="right")

    keys = list(groups.keys())
    for i, key in enumerate(keys, 1):
        table.add_row(str(i), key, str(len(groups[key])))

    console.print(table)
    console.print("[dim]0 = use all files[/dim]")

    choice = click.prompt("Select event number", type=int, default=1)
    if choice == 0:
        return [f for files in groups.values() for f in files]
    if 1 <= choice <= len(keys):
        return groups[keys[choice - 1]]
    console.print("[yellow]Invalid choice — using most recent.[/yellow]")
    return list(groups.values())[0]


def sample_files(files: List[Path], n: int) -> List[Path]:
    if n <= 0 or n >= len(files):
        return files
    sampled = random.sample(files, n)
    console.print(f"[dim]Sampled {n} of {len(files)} files[/dim]")
    return sorted(sampled)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_seen_hashes(processed_dir: Path) -> Tuple[Dict, Path]:
    """Load existing hash log. Does NOT write anything."""
    processed_dir.mkdir(parents=True, exist_ok=True)
    hashes_file = processed_dir / "seen_hashes.json"
    seen: Dict[str, str] = {}
    if hashes_file.exists():
        with open(hashes_file) as f:
            seen = json.load(f)
    return seen, hashes_file


def filter_new_files(files: List[Path], seen: Dict) -> List[Tuple[Path, str]]:
    """Return (path, hash) for files not yet successfully processed."""
    result = []
    for f in files:
        h = _hash_file(f)
        if h in seen:
            console.print(f"  [dim]Skip (already processed): {f.name}[/dim]")
        else:
            result.append((f, h))
    return result


def mark_processed(file_hash: str, path: Path, hashes_file: Path, seen: Dict) -> None:
    """Write a single file's hash to disk immediately after successful extraction."""
    seen[file_hash] = str(path)
    with open(hashes_file, "w") as f:
        json.dump(seen, f, indent=2)
