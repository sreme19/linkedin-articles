import hashlib
import json
from pathlib import Path
from typing import Dict, List

import yaml
from rich.console import Console

console = Console()

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def load_manifest(manifest_path: str) -> Dict:
    path = Path(manifest_path)
    if not path.exists():
        console.print(
            f"[yellow]No manifest found at {manifest_path}. "
            "Run 'python main.py init' to create one.[/yellow]"
        )
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


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def deduplicate(files: List[Path], processed_dir: Path) -> List[Path]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    hashes_file = processed_dir / "seen_hashes.json"

    seen: Dict[str, str] = {}
    if hashes_file.exists():
        with open(hashes_file) as f:
            seen = json.load(f)

    new_files = []
    for f in files:
        h = _hash_file(f)
        if h in seen:
            console.print(f"  [dim]Skip (already processed): {f.name}[/dim]")
        else:
            seen[h] = str(f)
            new_files.append(f)

    with open(hashes_file, "w") as f:
        json.dump(seen, f, indent=2)

    return new_files
