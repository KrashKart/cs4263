def render_starting_grid(example_input, file_name=""):
    """Return the starting Bubble Pop grid as readable terminal text.

    A lightweight, case-only view: it draws the saved input grid (the board
    the solver begins from) and nothing about any solution run. Empty cells
    render as '.', bubbles render as their colour number, and both rows and
    columns are labelled with zero-indexed coordinates.

    example_input may be the raw input dict or a case wrapper of the form
    {"input": {...}, "output": ...}; both are handled.
    """

    def error(message):
        return "Bubble Pop starting grid\n" + f"Input error: {message}"

    # Unwrap a {"input": {...}, "output": ...} case record if given one.
    if (
        isinstance(example_input, dict)
        and "input" in example_input
        and "grid" not in example_input
    ):
        example_input = example_input["input"]

    if not isinstance(example_input, dict):
        return error("input must be an object")

    rows = example_input.get("rows")
    cols = example_input.get("cols")
    grid = example_input.get("grid")
    num_colours = example_input.get("num_colours", "?")

    if type(rows) is not int or rows < 1:
        return error("rows must be a positive integer")
    if type(cols) is not int or cols < 1:
        return error("cols must be a positive integer")
    if not isinstance(grid, list) or len(grid) != rows:
        return error("grid must contain exactly rows lists")

    # Validate every cell and copy defensively so the input is never mutated.
    board = []
    for row_index, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != cols:
            return error(f"grid row {row_index} must contain exactly cols values")
        copied = []
        for col_index, cell in enumerate(row):
            if type(cell) is not int or cell < 0:
                return error(
                    f"grid cell [{row_index}, {col_index}] must be nonnegative"
                )
            copied.append(cell)
        board.append(copied)

    area = rows * cols
    bubble_count = sum(1 for row in board for cell in row if cell != 0)

    max_cell = max((cell for row in board for cell in row), default=0)
    cell_width = max(len(str(max_cell)), len(str(cols - 1)), 1) + 1
    row_label_width = max(len(f"r{rows - 1}"), 2)

    lines = ["Bubble Pop starting grid"]
    if file_name:
        lines.append(f"Case: {file_name}")
    lines.append(
        f"Grid: {rows} rows x {cols} cols; colours: 1..{num_colours}; "
        f"bubbles: {bubble_count}/{area}"
    )
    lines.append(
        "Zero-indexed [row, col]; empty cells shown as '.', "
        "other numbers are bubble colours."
    )
    lines.append("")

    header = "".join(str(col).rjust(cell_width) for col in range(cols))
    lines.append(" " * (row_label_width + 1) + header)
    for row_index, row in enumerate(board):
        cells = "".join(
            ("." if cell == 0 else str(cell)).rjust(cell_width) for cell in row
        )
        lines.append(f"r{row_index}".rjust(row_label_width) + " " + cells)

    return "\n".join(lines)

if __name__ == '__main__':
    import json
    with open('input/case_003.json') as f:
        input_dict = json.load(f)
        print(render_starting_grid(input_dict))
