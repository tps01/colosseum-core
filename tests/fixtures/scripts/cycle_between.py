"""Append between to the suite sequence log (cycle fixture)."""

LABEL = "between"


def main() -> None:
    from colosseum.context import get_context

    container = get_context().suite_output_dir
    if container is None:
        return
    path = container / "sequence.txt"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{LABEL}\n")
