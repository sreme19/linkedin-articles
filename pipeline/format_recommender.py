from typing import Dict, List, Tuple

import click
from rich.console import Console
from rich.table import Table

console = Console()

FORMAT_DESCRIPTIONS = {
    "article": "Long-form 600–900 words — hook, insights, your take, CTA",
    "carousel": "8–12 slide visual post + PPTX file ready for design",
    "infographic": "Single-image visual concept + DALL-E prompt + caption",
    "short_post": "Punchy 150–250 word post — hot take hook + bullet takeaways",
}

ALL_FORMATS = ["article", "carousel", "infographic", "short_post"]


def _recommend(synthesis: Dict, image_count: int) -> Tuple[List[str], Dict[str, str]]:
    scores: Dict[str, int] = {f: 0 for f in ALL_FORMATS}
    reasons: Dict[str, str] = {}

    hot_takes = synthesis.get("hot_takes", [])
    themes = synthesis.get("themes", [])
    data_points = synthesis.get("top_data_points", [])
    llm_rec = synthesis.get("recommended_format", "").split("|")[0].strip().split("—")[0].strip()

    if image_count >= 6:
        scores["carousel"] += 3
        reasons["carousel"] = f"{image_count} slides — carousel fits naturally"

    if len(themes) >= 3:
        scores["article"] += 2
        reasons["article"] = f"{len(themes)} strong themes for long-form"

    if hot_takes:
        scores["short_post"] += 2
        reasons["short_post"] = f"{len(hot_takes)} hot take(s) — great for punchy post"

    if len(data_points) >= 3:
        scores["infographic"] += 2
        reasons["infographic"] = f"{len(data_points)} data points — visual treatment works well"

    # LLM recommendation gets a small boost
    if llm_rec in scores:
        scores[llm_rec] += 1
        if llm_rec not in reasons:
            reasons[llm_rec] = "LLM-recommended based on content"

    ranked = sorted(
        [(fmt, score) for fmt, score in scores.items() if score > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    recommended = [fmt for fmt, _ in ranked]

    return recommended or ["article"], reasons


def recommend_and_confirm(
    synthesis: Dict, image_count: int, no_review: bool = False
) -> List[str]:
    recommended, reasons = _recommend(synthesis, image_count)

    table = Table(title="Format Recommendation", show_lines=True)
    table.add_column("Format", style="cyan", no_wrap=True)
    table.add_column("What it produces")
    table.add_column("Reason", style="green")

    for fmt in recommended:
        table.add_row(fmt, FORMAT_DESCRIPTIONS[fmt], reasons.get(fmt, ""))

    console.print(table)

    if no_review:
        console.print(f"Auto-selecting: [cyan]{', '.join(recommended)}[/cyan]")
        return recommended

    console.print(
        "\nOptions: [cyan]article, carousel, infographic, short_post, all[/cyan] "
        "or comma-separated list"
    )
    choice = click.prompt(
        "Select format(s) to generate", default=",".join(recommended)
    )

    if choice.strip().lower() == "all":
        return ALL_FORMATS

    selected = [c.strip() for c in choice.split(",") if c.strip() in ALL_FORMATS]
    return selected or recommended
