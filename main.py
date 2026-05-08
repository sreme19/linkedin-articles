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

# Explicitly load .env from the project root so it works regardless of cwd
load_dotenv(Path(__file__).parent / ".env", override=True)

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
    "--input", "-i", "input_path", default=None,
    help="Path to a single file or directory (PDF, PNG, JPG, WEBP, TXT, MD).",
)
@click.option(
    "--manifest", "-m", default=None,
    help="Path to manifest.yaml. Auto-selected when using --rotate.",
)
@click.option(
    "--format", "-f", "fmt",
    type=click.Choice(
        [
            "article", "carousel", "infographic", "short_post", "hot_take",
            "reaction_post", "story_post", "non_ai_post", "all", "auto",
        ],
        case_sensitive=False,
    ),
    default="auto",
    help="Content format to generate (default: auto-recommended).",
)
@click.option(
    "--output-dir", "-o", default=None,
    help="Output directory (default: data/output or data/private_output in privacy mode).",
)
@click.option(
    "--no-review", is_flag=True, default=False,
    help="Skip human review gates — useful for automation.",
)
@click.option(
    "--sample", "-n", default=0, type=int,
    help="Randomly sample N files from the input (0 = use all).",
)
@click.option(
    "--rotate", is_flag=True, default=False,
    help="Auto-select a conference different from the last posted one.",
)
@click.option(
    "--privacy-mode", is_flag=True, default=False,
    help="Process private notes with git-ignore checks and anonymized output.",
)
def run(input_path, manifest, fmt, output_dir, no_review, sample, rotate, privacy_mode):
    """Process conference artefacts and generate LinkedIn content."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[red]Error: ANTHROPIC_API_KEY not set. "
            "Add it to .env or export it as an environment variable.[/red]"
        )
        sys.exit(1)

    from pipeline.ingest import (
        collect_files, group_by_event, select_event,
        sample_files, load_seen_hashes, filter_new_files,
        mark_processed, load_manifest,
    )
    from pipeline.extract import extract_artifact
    from pipeline.synthesize import synthesize
    from pipeline.format_recommender import recommend_and_confirm
    from pipeline.generate import generate_content
    from pipeline.export import export_run
    from pipeline.editorial import enrich_synthesis
    from pipeline.privacy import anonymize_artifacts, assert_private_path, private_manifest

    # ── Rotate: auto-pick a different conference than last posted ─────────────
    if rotate:
        input_path, manifest = _resolve_rotate(input_path, manifest)
        if not input_path:
            sys.exit(1)

    if not input_path:
        console.print("[red]Error: --input is required unless using --rotate.[/red]")
        sys.exit(1)

    if privacy_mode:
        if fmt not in {"auto", "all", "non_ai_post"}:
            console.print("[red]Privacy mode currently supports only --format non_ai_post (or auto/all).[/red]")
            sys.exit(1)
        try:
            assert_private_path(input_path, BASE_DIR)
            if output_dir:
                assert_private_path(output_dir, BASE_DIR)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)

    # ── 1. Ingest ─────────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 1 / 6 — Ingesting artefacts[/bold blue]"))

    manifest_data = load_manifest(manifest or "manifest.yaml")
    if privacy_mode:
        manifest_data = private_manifest(manifest_data)
    conference = manifest_data.get("conference_name", "Unknown Conference")
    # Will be updated after synthesis if manifest has no real conference name

    all_files = collect_files(input_path)
    if not all_files:
        console.print(f"[red]No supported files found at: {input_path}[/red]")
        sys.exit(1)

    console.print(f"Found [green]{len(all_files)}[/green] file(s) in {input_path}")

    # Group by event date and let user pick (or auto-select most recent)
    groups = group_by_event(all_files)
    if len(groups) > 1:
        files = select_event(groups, no_review)
    else:
        files = all_files

    # Optional random sample
    if sample > 0:
        files = sample_files(files, sample)

    processed_dir = DATA_DIR / "processed"
    seen, hashes_file = load_seen_hashes(processed_dir)
    new_files = filter_new_files(files, seen)

    if not new_files:
        console.print("[yellow]All files already processed. Delete data/processed/seen_hashes.json to re-process.[/yellow]")
        sys.exit(0)

    console.print(f"[green]{len(new_files)}[/green] new file(s) to process")

    # ── 2. Extract ────────────────────────────────────────────────────────────
    console.print(Panel("[bold blue]Step 2 / 6 — Extracting content[/bold blue]"))

    artifacts = []
    skipped = 0
    image_count = 0
    file_speakers = manifest_data.get("file_speakers", {})

    for f, file_hash in new_files:
        ctx = manifest_data.copy()
        if f.name in file_speakers:
            ctx["speaker"] = file_speakers[f.name]

        try:
            artifact = extract_artifact(f, ctx)
        except Exception as e:
            console.print(f"  [yellow]Skipped {f.name}: {e}[/yellow]")
            skipped += 1
            continue

        if artifact:
            artifacts.append(artifact)
            mark_processed(file_hash, f, hashes_file, seen)
            if artifact.get("source_type") == "image":
                image_count += 1
            elif artifact.get("source_type") == "pdf":
                image_count += artifact.get("page_count", 0)

    if skipped:
        console.print(f"[yellow]Skipped {skipped} file(s) due to errors.[/yellow]")

    if not artifacts:
        console.print("[red]No content could be extracted from the provided files.[/red]")
        sys.exit(1)

    if privacy_mode:
        artifacts = anonymize_artifacts(artifacts)
        console.print("[dim]Privacy mode: anonymized extracted notes before synthesis/export[/dim]")

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

    # Upgrade conference name if manifest had a placeholder
    detected = synthesis.get("detected_conference_name", "")
    if detected and conference in ("Unknown Conference", ""):
        conference = detected
        manifest_data["conference_name"] = detected
        console.print(f"  [dim]Conference identified: {detected}[/dim]")

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
        if privacy_mode:
            formats = ["non_ai_post"]
        else:
            formats = recommend_and_confirm(synthesis, image_count, no_review)
    elif fmt == "all":
        formats = ["non_ai_post"] if privacy_mode else ["article", "carousel", "infographic", "short_post", "hot_take"]
    else:
        formats = [fmt]

    synthesis = enrich_synthesis(synthesis, manifest_data)
    editorial = synthesis.get("_editorial", {})
    if editorial.get("repeat_warnings"):
        console.print("[yellow]Editorial repeat warnings:[/yellow]")
        for warning in editorial["repeat_warnings"]:
            console.print(f"  - {warning}")
    if editorial.get("post_mode"):
        console.print(f"Editorial mode: [cyan]{editorial['post_mode']}[/cyan]")

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
        out_slug = conference.lower().replace(" ", "-").replace("/", "-")[:30]
        base_output = DATA_DIR / ("private_output" if privacy_mode else "output")
        output_dir = str(base_output / f"{date.today().isoformat()}_{out_slug}")

    export_run(generated, synthesis, manifest_data, Path(output_dir))
    if privacy_mode:
        console.print("  [dim]Privacy mode: skipped tracked topics_log.json update[/dim]")
    else:
        _update_topics_log(topics_log, synthesis, manifest_data, output_dir)

    console.print(
        f"\n[bold green]Done![/bold green]  "
        f"Output → [cyan]{output_dir}[/cyan]"
    )


@cli.command()
@click.option(
    "--input", "-i", "input_path", default="data/raw/",
    help="Directory containing all artefacts (default: data/raw/).",
)
@click.option(
    "--sample", "-n", default=12, type=int,
    help="Images to sample per event group (default: 12).",
)
def scan(input_path, sample):
    """Scan all event groups, extract topics, and save to topics_log.json without generating content."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set.[/red]")
        sys.exit(1)

    from pipeline.ingest import collect_files, group_by_event, sample_files, load_seen_hashes, filter_new_files, mark_processed
    from pipeline.extract import extract_artifact
    from pipeline.synthesize import synthesize

    all_files = collect_files(input_path)
    if not all_files:
        console.print(f"[red]No supported files found at: {input_path}[/red]")
        sys.exit(1)

    groups = group_by_event(all_files)
    console.print(f"Found [green]{len(groups)}[/green] event group(s) across [green]{len(all_files)}[/green] files\n")

    topics_log = (
        json.loads(TOPICS_LOG.read_text()) if TOPICS_LOG.exists() else {"topics": []}
    )
    existing_topics = {t["topic"] for t in topics_log.get("topics", [])}

    processed_dir = DATA_DIR / "processed"
    seen, hashes_file = load_seen_hashes(processed_dir)

    added_total = 0

    for event_date, files in groups.items():
        console.print(Panel(f"[bold blue]Event: {event_date}  ({len(files)} files)[/bold blue]"))

        sampled = sample_files(files, sample)
        new_files = filter_new_files(sampled, seen)

        if not new_files:
            console.print("  [dim]All sampled files already processed — skipping.[/dim]\n")
            continue

        artifacts = []
        for f, file_hash in new_files:
            try:
                artifact = extract_artifact(f, {})
                if artifact:
                    artifacts.append(artifact)
                    mark_processed(file_hash, f, hashes_file, seen)
            except Exception as e:
                console.print(f"  [yellow]Skipped {f.name}: {e}[/yellow]")

        if not artifacts:
            console.print("  [yellow]No content extracted — skipping.[/yellow]\n")
            continue

        synthesis = synthesize(artifacts, {}, topics_log)

        conference = (
            synthesis.get("detected_conference_name")
            or f"Event {event_date}"
        )

        console.print(f"  Conference: [cyan]{conference}[/cyan]")
        console.print(f"  Summary: {synthesis.get('conference_summary', '')[:120]}...")

        added = 0
        for theme in synthesis.get("themes", []):
            if theme["title"] not in existing_topics:
                topics_log["topics"].append({
                    "topic": theme["title"],
                    "insight": theme["insight"],
                    "date": date.today().isoformat(),
                    "conference": conference,
                    "output_dir": "",
                })
                existing_topics.add(theme["title"])
                added += 1
                console.print(f"  + [green]{theme['title']}[/green]")

        if added == 0:
            console.print("  [dim]No new topics (all already covered).[/dim]")
        else:
            added_total += added

        TOPICS_LOG.write_text(json.dumps(topics_log, indent=2))
        console.print()

    console.print(f"[bold green]Done.[/bold green] Added [green]{added_total}[/green] new topic(s) to topics_log.json")


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


@cli.command("check-post")
@click.option("--file", "post_file", required=True, type=click.Path(exists=True), help="Post file to validate.")
@click.option("--privacy-mode", is_flag=True, default=False, help="Apply private-note risk checks.")
@click.option(
    "--mode",
    default="",
    type=click.Choice(
        [
            "",
            "management_reflection",
            "career_transition",
            "leadership_lesson",
            "ai_data_practitioner",
            "public_example_analysis",
        ],
        case_sensitive=False,
    ),
    help="Editorial post mode for style checks.",
)
def check_post(post_file, privacy_mode, mode):
    """Run privacy, style, and topic-cluster checks on a post draft."""
    from pipeline.editorial import validate_post_text

    path = Path(post_file)
    result = validate_post_text(path.read_text(), privacy_mode=privacy_mode, mode=mode)
    console.print(Panel(json.dumps(result, indent=2), title="[bold blue]Post Checks[/bold blue]"))
    if not result["ok"]:
        sys.exit(1)


@cli.command("record-final")
@click.option("--file", "post_file", required=True, type=click.Path(exists=True), help="Final edited post file.")
@click.option("--generated-file", default="", help="Original generated draft path, if any.")
@click.option(
    "--mode",
    default="management_reflection",
    type=click.Choice(
        [
            "management_reflection",
            "career_transition",
            "leadership_lesson",
            "ai_data_practitioner",
            "public_example_analysis",
        ],
        case_sensitive=False,
    ),
    help="Editorial post mode.",
)
@click.option("--topic", default="", help="Human-readable topic label.")
@click.option("--notes", default="", help="What changed or why the final worked.")
def record_final(post_file, generated_file, mode, topic, notes):
    """Record a user-approved final post so future runs learn from it."""
    from pipeline.editorial import record_final_post

    path = Path(post_file)
    entry = record_final_post(
        path.read_text(),
        source_generated_file=generated_file,
        mode=mode,
        topic=topic,
        notes=notes,
    )
    console.print(Panel(json.dumps(entry, indent=2), title="[bold green]Recorded Final Post[/bold green]"))


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

def _resolve_rotate(input_path, manifest):
    """Pick an event directory different from the last posted conference."""
    import re

    posts_log_path = BASE_DIR / "data" / "posts_log.json"
    last_conference = ""
    if posts_log_path.exists():
        log = json.loads(posts_log_path.read_text())
        posted = [p for p in log.get("posts", []) if p.get("posted_date") or p.get("engagement", {}).get("likes")]
        if not posted:
            posted = log.get("posts", [])
        if posted:
            last_conference = posted[-1].get("conference", "").lower()

    events_dir = CONFIG_DIR / "events"
    raw_dir = DATA_DIR / "raw"

    # Build event options: {date_cluster: (manifest_path, raw_date_dirs)}
    options = {}
    if events_dir.exists():
        for mf in sorted(events_dir.glob("*.yaml")):
            import yaml
            data = yaml.safe_load(mf.read_text()) or {}
            name = data.get("conference_name", "")
            clusters = data.get("_date_cluster", [])
            if name.lower() == last_conference:
                continue
            # Find images for this event
            imgs = []
            for cluster in clusters:
                imgs.extend(sorted(raw_dir.glob(f"IMG{cluster}*.jpg")))
                imgs.extend(sorted(raw_dir.glob(f"IMG{cluster}*.jpeg")))
                imgs.extend(sorted(raw_dir.glob(f"IMG{cluster}*.png")))
            if imgs:
                options[name] = (str(mf), str(raw_dir), clusters)

    if not options:
        console.print("[yellow]--rotate: no alternative conference found, using default input.[/yellow]")
        return input_path, manifest

    # Pick the event with most unprocessed images (richest new content)
    processed_dir = DATA_DIR / "processed"
    seen_path = processed_dir / "seen_hashes.json"
    seen_names: set = set()
    if seen_path.exists():
        seen_data = json.loads(seen_path.read_text())
        seen_names = {Path(p).name for p in seen_data.values()}

    best_name, best_manifest, best_dir, best_clusters = "", "", str(raw_dir), []
    best_count = -1
    for name, (mf_path, raw_path, clusters) in options.items():
        unprocessed = sum(
            1 for c in clusters
            for f in Path(raw_path).glob(f"IMG{c}*")
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"} and f.name not in seen_names
        )
        if unprocessed > best_count:
            best_count = unprocessed
            best_name = name
            best_manifest = mf_path
            best_dir = raw_path
            best_clusters = clusters

    if not best_name:
        console.print("[yellow]--rotate: all alternative conferences already processed. Picking least-recently used.[/yellow]")
        best_name, (best_manifest, best_dir, best_clusters) = next(iter(options.items()))

    console.print(f"[cyan]--rotate: selected [bold]{best_name}[/bold] ({best_count} unprocessed images)[/cyan]")
    return best_dir, best_manifest


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
    conference = (
        manifest.get("conference_name")
        or synthesis.get("detected_conference_name")
        or ""
    )
    for theme in synthesis.get("themes", []):
        log["topics"].append(
            {
                "topic": theme["title"],
                "insight": theme["insight"],
                "date": date.today().isoformat(),
                "conference": conference,
                "output_dir": output_dir,
            }
        )
    TOPICS_LOG.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    cli()
