"""Draw a practice world and an optional recorded Wumpus World episode.

Usage:
    python visualise_wumpus_world.py                  # all saved examples
    python visualise_wumpus_world.py case_01.json      # one saved example

To draw your agent's own run, uncomment the visualiser call in run_local.py.

These debugging maps reveal the practice case's hidden world. The agent
itself must learn through env.get_percept() and env.act(). The renderer
reads the recorded episode without running an agent or changing the data.
"""


def visualise_wumpus_world(
    example_input, expected_output=None, candidate_output=None, file_name=""
) -> str:
    """Draw the starting world, then the recorded steps and outcome.

    Use the agent's output when supplied, otherwise the saved example.
    """
    config, world = example_input["config"], example_input["world"]
    rows, cols = config["rows"], config["cols"]
    pits = {tuple(cell) for cell in world["pits"]}
    gold = {tuple(cell) for cell in world["gold"]}
    wumpus = tuple(world["wumpus"])
    neighbours = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def grid(cell_text):
        contents = [[cell_text(r, c) for c in range(cols)] for r in range(rows)]
        width = max(len(str(cols - 1)), *(len(text) for row in contents for text in row))
        label_width = len(str(rows - 1))
        lines = [" " * (label_width + 3) + "  ".join(
            str(c).center(width) for c in range(cols)
        )]
        for r, row in enumerate(contents):
            lines.append(f"{r:>{label_width}} | " + "  ".join(
                text.center(width) for text in row
            ))
        return lines

    def flag(value):
        return "T" if value is True else "." if value is False else "?"

    def object_glyph(r, c):
        cell = (r, c)
        if cell == (0, 0):
            return "S"
        if cell == wumpus:
            return "W"
        if cell in pits:
            return "P"
        if cell in gold:
            return "G"
        return "."

    def percept_glyph(r, c):
        breeze = any((r + dr, c + dc) in pits for dr, dc in neighbours)
        stench = any((r + dr, c + dc) == wumpus for dr, dc in neighbours)
        return ("b" if breeze else "") + ("s" if stench else "") or "-"

    lines = [
        f"Simple Wumpus World  {rows}x{cols}  gold_required={config.get('gold_required')}",
    ]
    if file_name:
        lines.append(f"Case: {file_name}")
    lines.extend([
        "Starting world (hidden objects revealed for debugging)",
        "Legend: S=start  W=wumpus  P=pit  G=gold  .=empty",
        *grid(object_glyph),
        "",
        "Percepts: b=breeze  s=stench  bs=both  -=neither",
        "Glitter occurs only when fresh gold is collected, not on every visit.",
        *grid(percept_glyph),
        "\n"+"-"*67  # >:)
    ])

    ref = candidate_output if candidate_output is not None else expected_output
    if ref is None:
        return "\n".join(lines + ["", "No episode supplied; showing the world only."])
    label = "Your agent's episode" if candidate_output is not None else "Saved example episode"
    episode = ref["episode"]
    lines.extend([
        "", label,
        "Steps: T=true  .=false  ?=no percept",
        "  #  action                  breeze stench glitter terminal",
    ])
    for index, step in enumerate(episode["steps"]):
        action = step["action"]
        if action is None:
            action_text = "start"
        else:
            action_text = f"{action[0]}({', '.join(repr(arg) for arg in action[1:])})"
        # Rejected actions have no percept; keep them visible in the trace.
        percept = step["percept"] or {}
        note = "  rejected (no movement)" if step["percept"] is None else ""
        lines.append(
            f"{index:>3}  {action_text:<22}  "
            f"{flag(percept.get('breeze')):^6} {flag(percept.get('stench')):^6} "
            f"{flag(percept.get('glitter')):^7} {flag(percept.get('is_terminal')):^8}"
            f"{note}"
        )
    lines.append(f"Outcome: status={episode['status']!r}  reason={episode['reason']!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent
    names = sys.argv[1:] or sorted(path.name for path in (root / "input").glob("*.json"))
    for name in names:
        data = json.loads((root / "input" / name).read_text(encoding="utf-8"))
        output_path = root / "output" / name
        expected = json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        print(visualise_wumpus_world(data, expected_output=expected, file_name=name))
        print()
