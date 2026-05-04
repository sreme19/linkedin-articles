import json
import os
import sys
from datetime import date
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

console = Console()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
TOPICS_LOG = BASE_DIR / "topics_log.json"


@click.group()
def cli():
    """LinkedIn article generator — turn conference artefacts into ready-to-post content."""
    pass


@cli.command()
@click.option(
    "--input", "-i", "input_path", required=True,
    help="Path to a single file or a directory of artefacts (PDF, PNG, JPG, WEBP).",
)
@click.option(
    "--manifest", "-m", default="manifest.yaml",
    help="Path to manifest.yaml (default: manifest.yaml in current dir).",
)
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(
        ["article", "carousel", "infographic", "short_post", "all", "auto"],
        case_sensitive=False,
    ),
    default="auto",
    help="Content format to generate (default: auto-recommended).",
)
@click.option(
    "--output-dir", "-o", default=None,
    help="Output directory (default: data/output/YYYY-MM-DD_conference-name).",
)
@click.option(
    "--no-review", is_flag=True, default=False,
    help="Skip human review gates — useful for automation.",
)
def run(input_path, manifest, fmt, output_dir, no_review):
    """Process conference artefacts and generate LinkedIn content."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error: ANTHROPIC_API_KEY not set. "
            "Add it to .env or export it as an environment variable.[/red]"
        )
        sys.exit(1)

    from pipeline.ingest import collect_files, deduplicate, load_manifest
    from pipeline.extract import extract_artifact
    from pipeline.synthesize import synthesize
    from pipeline.format_recommender import recommend_and_confirm
    from pipeline.generate import generate_content
    from pipeline.export import export_run

    # ── 1. Ingest ─────────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 1 / 6 — Ingesting artefacts[/bold blue]"))

    manifest_data = load_manifest(manifest)
    conference = manifest_data.get("conference_name", "Unknown Conference")

    files = collect_files(input_path)
    if not files:
        console.print(f"[red]No supported files found at: {input_path}[/red]")
        sys.exit(1)

    console.print(f"Found [green]{len(files)}[/green] file(s) in {input_path}")

    processed_dir = DATA_DIR / "processed"
    new_files = deduplicate(files, processed_dir)

    if not new_files:
        console.print("[yellow]All files already processed. Delete data/processed/seen_hashes.json to re-process.[/yellow]")
        sys.exit(0)

    console.print(f"[green]{len(new_files)}[/green] new file(s) to process")

    # ── 2. Extract ────────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 2 / 6 — Extracting content[/bold blue]"))

    artifacts = []
    image_count = 0
    file_speakers = manifest_data.get("file_speakers", {})

    for f in new_files:
        ctx = manifest_data.copy()
        if f.name in file_speakers:
            ctx["speaker"] = file_speakers[f.name]

        artifact = extract_artifact(f, ctx)
        if artifact:
            artifacts.append(artifact)
            if artifact.get("source_type") == "image":
                image_count += 1
            elif artifact.get("source_type") == "pdf":
                image_count += artifact.get("page_count", 0)

    if not artifacts:
        console.print("[red]No content could be extracted from the provided files.[/red]")
        sys.exit(1)

    # Persist extracted content
    slug = conference.replace(" ", "-")[:30]
    extracted_path = processed_dir / f"{date.today().isoformat()}_{slug}_extracted.json"
    extracted_path.write_text(json.dumps(artifacts, indent=2))
    console.print(
        f"Extracted [green]{len(artifacts)}[/green] artefact(s) → "
        f"[dim]{extracted_path}[/dim]"
    )

    # ── 3. Synthesise ─────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 3 / 6 — Synthesising insights[/bold blue]"))

    topics_log = (
        json.loads(TOPICS_LOG.read_text()) if TOPICS_LOG.exists() else {"topics": []}
    )
    synthesis = synthesize(artifacts, manifest_data, topics_log)

    console.print(
        Panel(_format_synthesis(synthesis), title="[bold green]Synthesis Brief[/bold green]")
    )

    if not no_review:
        if not click.confirm(
            "\nDoes this synthesis look right? Continue to content generation?",
            default=True,
        ):
            console.print(
                f"[yellow]Aborted. Extracted data saved at {extracted_path}[/yellow]"
            )
            sys.exit(0)

    # ── 4. Recommend format ───────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 4 / 6 — Format recommendation[/bold blue]"))

    if fmt == "auto":
        formats = recommend_and_confirm(synthesis, image_count, no_review)
    elif fmt == "all":
        formats = ["article", "carousel", "infographic", "short_post"]
    else:
        formats = [fmt]

    console.print(f"Generating: [cyan]{', '.join(formats)}[/cyan]")

    # ── 5. Generate ───────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 5 / 6 — Generating content[/bold blue]"))

    persona = (CONFIG_DIR / "persona.md").read_text()
    hashtags = json.loads((CONFIG_DIR / "hashtags.json").read_text())

    generated = {}
    for fmt_name in formats:
        console.print(f"  Generating [cyan]{fmt_name}[/cyan]...")
        generated[fmt_name] = generate_content(
            fmt_name, synthesis, manifest_data, persona, hashtags
        )

    # ── 6. Export ─────────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 6 / 6 — Exporting[/bold blue]"))

    if output_dir is None:
        out_slug = conference.lower().replace(" ", "-")[:30]
        output_dir = str(DATA_DIR / "output" / f"{date.today().isoformat()}_{out_slug}")

    export_run(generated, synthesis, manifest_data, Path(output_dir))
    _update_topics_log(topics_log, synthesis, manifest_data, output_dir)

    console.print(
        f"\n[bold green]Done![/bold green]  "
        f"Output → [cyan]{output_dir}[/cyan]"
    )


@cli.command()
def init():
    """Create a manifest.yaml in the current directory from the built-in template."""
    template_path = CONFIG_DIR / "manifest_template.yaml"
    out = Path("manifest.yaml")
    if out.exists():
        if not click.confirm("manifest.yaml already exists. Overwrite?", default=False):
            console.print("Aborted.")
            return
    out.write_text(template_path.read_text())
    console.print(
        "[green]Created manifest.yaml[/green] — edit it with your conference details before running."
    )


@cli.command()
def topics():
    """Show all previously covered topics from topics_log.json."""
    if not TOPICS_LOG.exists() or not json.loads(TOPICS_LOG.read_text()).get("topics"):
        console.print("[dim]No topics logged yet.[/dim]")
        return

    log = json.loads(TOPICS_LOG.read_text())
    table = Table(title="Covered Topics", show_lines=True)
    table.add_column("Date", style="dim", no_wrap=True)
    table.add_column("Topic", style="cyan")
    table.add_column("Conference")

    for t in log["topics"]:
        table.add_row(t.get("date", ""), t.get("topic", ""), t.get("conference", ""))

    console.print(table)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_synthesis(synthesis: dict) -> str:
    lines = []
    summary = synthesis.get("conference_summary", "")
    if summary:
        lines.append(f"[bold]Summary:[/bold] {summary}\n")

    themes = synthesis.get("themes", [])
    if themes:
        lines.append(f"[bold]Themes ({len(themes)}):[/bold]")
        colour = {"high": "green", "medium": "yellow", "low": "dim"}
        for t in themes:
            c = colour.get(t.get("novelty", "medium"), "white")
            covered = " [dim](covered before)[/dim]" if t.get("previously_covered") else ""
            lines.append(f"  • [{c}]{t.get('title', 'Unknown')}[/{c}]{covered} — {t.get('insight', '')}")

    hot_takes = synthesis.get("hot_takes", [])
    if hot_takes:
        lines.append(f"\n[bold red]Hot Takes ({len(hot_takes)}):[/bold red]")
        for ht in hot_takes:
            lines.append(f"  🔥 {ht['claim']}  [dim][{ht.get('source', '')}][/dim]")

    hook = synthesis.get("best_hook", "")
    if hook:
        lines.append(f"\n[bold]Best hook:[/bold] {hook}")

    return "\n".join(lines)


def _update_topics_log(
    log: dict, synthesis: dict, manifest: dict, output_dir: str
) -> None:
    for theme in synthesis.get("themes", []):
        log["topics"].append(
            {
                "topic": theme["title"],
                "insight": theme["insight"],
                "date": date.today().isoformat(),
                "conference": manifest.get("conference_name", ""),
                "output_dir": output_dir,
            }
        )
    TOPICS_LOG.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    cli()
