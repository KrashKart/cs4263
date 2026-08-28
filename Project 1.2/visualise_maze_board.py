def visualise_maze_board(example_input, expected_output=None, candidate_output=None, file_name=''):
    """
    Render the Shifting Maze grid showing each cell's openings, the start
    position (S) and goal positions (G).

    Each cell is drawn as a 3-character-wide × 3-line-tall ASCII tile:

        · | ·      '|' in the top row  → cell has an 'up'    opening
        - + -      '-' on the left     → cell has a 'left'   opening
        · | ·      '-' on the right    → cell has a 'right'  opening
                   '|' in the bottom   → cell has a 'down'   opening

    Tiles are placed directly adjacent, so the boundary between two
    neighbouring cells shows each side's opening independently — a valid
    two-way passage requires both sides to be open toward each other.

    When candidate_output is supplied the solution's action sequence and
    cost are appended as a footer; otherwise expected_output is used if
    available.
    """
    rows = example_input['rows']
    cols = example_input['cols']
    cells = example_input['cells']

    # Support both 'starting_position' and the spaced variant 'starting position'
    start_raw = (example_input.get('starting_position')
                 or example_input.get('starting position')
                 or [0, 0])
    start = tuple(start_raw)

    goals = {tuple(g) for g in example_input.get('goals', [])}

    rotation_cost = example_input.get('rotation_cost', '?')
    movement_cost = example_input.get('movement_cost', '?')

    # ── cell tile renderer ────────────────────────────────────────────────────

    def tile(cell_type, centre):
        """Return (top, mid, bot) — three 3-char strings for one cell tile."""
        u = '|' if 'u' in cell_type else ' '
        d = '|' if 'd' in cell_type else ' '
        l = '-' if 'l' in cell_type else ' '
        r = '-' if 'r' in cell_type else ' '
        return (f' {u} ', f'{l}{centre}{r}', f' {d} ')

    # ── assemble grid display rows ────────────────────────────────────────────

    grid_rows = []          # list of (top_str, mid_str, bot_str) per maze row
    for r in range(rows):
        tops, mids, bots = [], [], []
        for c in range(cols):
            ct = cells[r][c]
            if (r, c) == start:
                centre = 'S'
            elif (r, c) in goals:
                centre = 'G'
            else:
                centre = '+'
            t, m, b = tile(ct, centre)
            tops.append(t)
            mids.append(m)
            bots.append(b)
        grid_rows.append((''.join(tops), ''.join(mids), ''.join(bots)))

    # ── coordinate labels ─────────────────────────────────────────────────────

    rw = max(1, len(str(rows - 1)))      # width needed for row index labels
    indent = ' ' * (rw + 1)             # blank prefix aligning grid to labels

    col_header = indent + ''.join(str(c).center(3) for c in range(cols))

    # ── build output ──────────────────────────────────────────────────────────

    out = [
        f'Shifting Maze  {rows}x{cols}    '
        f'move_cost={movement_cost}  rotate_cost={rotation_cost}',
        f'Start: {list(start)}    Goals: {sorted(goals)}',
        'Legend:  S=Start  G=Goal  +=Cell  '
        '| =up/down opening  - =left/right opening',
        '',
        col_header,
    ]

    for r, (top, mid, bot) in enumerate(grid_rows):
        row_label = str(r).rjust(rw) + ' '
        out.append(indent   + top)
        out.append(row_label + mid)
        out.append(indent   + bot)

    # ── optional solution / run-trace footer ──────────────────────────────────

    ref = candidate_output if candidate_output is not None else expected_output
    if ref is not None:
        label = 'Candidate' if candidate_output is not None else 'Optimal'
        actions, cost = ref
        out.append('')
        if cost == -1:
            out.append(f'{label}: No path found  (cost = -1)')
        else:
            names = {1: 'U', 2: 'R', 3: 'D', 4: 'L', 5: 'rot'}
            steps = ' '.join(names.get(a, str(a)) for a in actions)
            out.append(f'{label} path cost: {cost}  ({len(actions)} actions)')
            out.append(f'Actions: {steps}')

    return '\n'.join(out)
