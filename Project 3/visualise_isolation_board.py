"""Draw an Isolation board, optionally showing a supplied sequence of turns.

From this folder:
    python visualise_isolation_board.py input/case_001.json
    python visualise_isolation_board.py input/case_001.json output/case_001.json

The second file can also be your own solution's output saved as JSON.
"""


def visualise_isolation_board(
    example_input, expected_output=None, candidate_output=None, file_name=""
):
    """Return plain text for the starting board and each supplied turn.

    candidate_output takes precedence over expected_output, including when it
    is an empty list. Each turn is a (destination, removed_cell) pair.
    A complete sequence shows the game through its end.
    To draw a single position, pass its player coordinates in starting_positions
    and its removed cells in removed_cells, with no output argument.
    """
    rows = example_input["rows"]
    cols = example_input["cols"]
    row_width = len(str(rows - 1))
    cell_width = max(3, len(str(cols - 1)) + 2)
    indent = " " * (row_width + 1)

    def draw_board(turns):
        # Read each player's latest recorded coordinate for this frame.
        positions = []
        for player, start in enumerate(example_input["starting_positions"]):
            player_turns = turns[player::2]
            positions.append(tuple(player_turns[-1][0] if player_turns else start))
        removed = {tuple(cell) for cell in example_input["removed_cells"]}
        removed.update(tuple(cell) for _, cell in turns)

        lines = [indent + "".join(str(c).center(cell_width) for c in range(cols))]
        for r in range(rows):
            cells = []
            for c in range(cols):
                cell = (r, c)
                if cell == positions[0]:
                    symbol = "1"
                elif cell == positions[1]:
                    symbol = "2"
                elif cell in removed:
                    symbol = "#"
                else:
                    symbol = "."
                cells.append(symbol.center(cell_width))
            lines.append(str(r).rjust(row_width) + " " + "".join(cells))
        return "\n".join(lines)

    out = [
        f"Isolation {rows}x{cols}" + (f" — {file_name}" if file_name else ""),
        "Legend: 1=Player 1  2=Player 2  #=Removed  .=Empty",
        "",
        "Starting board",
        draw_board([]),
    ]
    trace = candidate_output if candidate_output is not None else expected_output
    if trace is not None:
        label = "Your solution" if candidate_output is not None else "Saved output"
        out.extend(["", label])
        for step, (destination, removed_cell) in enumerate(trace, start=1):
            out.extend([
                "",
                f"Turn {step}: player {(step - 1) % 2 + 1}, "
                f"destination {tuple(destination)}, removed {tuple(removed_cell)}",
                draw_board(trace[:step]),
            ])
        out.extend(["", f"End of supplied sequence ({len(trace)} turns)."])
    return "\n".join(out)


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input case JSON file")
    parser.add_argument("output", type=Path, nargs="?", help="Optional turns JSON file")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    turns = (
        json.loads(args.output.read_text(encoding="utf-8"))
        if args.output is not None
        else None
    )
    print(visualise_isolation_board(data, expected_output=turns, file_name=args.input.name))
