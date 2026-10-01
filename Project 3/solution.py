# helper globals
_WILL_WIN = {}
_NEXT_MOVES = [] # next moves for each cell (no diagonal)
_NEIGHBOURS = [] # possible neighbours to remove
_NEXT_MOVES_SET = [] # frozenset for fast lookup

def solve(data: dict):
    problem = build_search_representation(data)
    actions = search(problem)

    # must unflatten the coordinates
    cols = data["cols"]
    return [
        ((d // cols, d % cols), (r // cols, r % cols))
        for d, r in actions
    ]

def _make(board, prev_pos, next_pos, removal_pos):
    # copy board and set prev pos to free (prev_pos = 1), 
    # dest pos and removed pos to unavailable (next_pos = removal_pos = 0)
    nb = bytearray(board)
    nb[prev_pos] = 1
    nb[next_pos] = 0
    nb[removal_pos] = 0
    return bytes(nb)

def _actions(state):
    # draw from ranked actions
    return [(d, r) for _, d, r in _rank(state)]

def _transition(state, action):
    board, a, b, turn = state
    d, r = action

    # rmb to flip turn
    return (_make(board, a, d, r), b, d, 1 - turn)

def _is_terminal(state):
    # terminate check
    board = state[0]
    for x in _NEXT_MOVES[state[1]]:
        if board[x]:
            return False
    return True

def _utility(state):
    return 1 if state[3] == 1 else -1

def build_search_representation(data: dict) -> dict:
    global _WILL_WIN, _NEXT_MOVES, _NEIGHBOURS, _NEXT_MOVES_SET
    rows, cols = data["rows"], data["cols"]
    n = rows * cols
    next_moves = []
    neighbours = []

    # construct neighbour and next_moves
    for r in range(rows):
        for c in range(cols):
            nm = []
            ne = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = r + dr
                    nc = c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        idx = nr * cols + nc
                        ne.append(idx)
                        if dr == 0 or dc == 0:
                            nm.append(idx)
            next_moves.append(tuple(nm))
            neighbours.append(tuple(ne))
    
    _NEXT_MOVES = next_moves
    _NEIGHBOURS = neighbours
    _NEXT_MOVES_SET = [frozenset(o) for o in next_moves]
    _WILL_WIN = {}

    # create start pos for player 1 and 2
    p1 = data["starting_positions"][0]
    p2 = data["starting_positions"][1]
    a = p1[0] * cols + p1[1]
    b = p2[0] * cols + p2[1]

    # board is a flattened bytearray representation of a r x c grid
    # if bit = 1, free, else occupied/cannot move there
    board = bytearray([1]) * n
    for r, c in data["removed_cells"]:
        board[r * cols + c] = 0
    board[a] = 0
    board[b] = 0

    return {
        "initial_state": (bytes(board), a, b, 0),
        "actions": _actions,
        "transition": _transition,
        "is_terminal": _is_terminal,
        "utility": _utility,
    }

def _rank(state, prune=False):
    # crucial ranking for pruning and action decision
    board, a, b, turn = state
    next_moves = _NEXT_MOVES
    neighbours = _NEIGHBOURS
    next_moves_b = next_moves[b]
    next_moves_b_set = _NEXT_MOVES_SET[b]
    out = []

    for next_cell in next_moves[a]:
        if not board[next_cell]:
            continue # skip if out of bounds or occupied
        
        # count how many moves the opponent has left if move to next_cell
        opp_moves_left = 0
        for opp_next_cell in next_moves_b:
            if opp_next_cell != next_cell and (board[opp_next_cell] or opp_next_cell == a):
                opp_moves_left += 1

        # count how many moves curr player has left if move to next_cell
        next_next_moves = next_moves[next_cell]
        next_next_moves_set = _NEXT_MOVES_SET[next_cell]
        curr_moves_left = 0
        for next_next_cell in next_next_moves:
            if board[next_next_cell] or next_next_cell == a:
                curr_moves_left += 1

        # consider all cell removals curr player can make
        for next_removal in neighbours[next_cell]:
            if next_removal == a:
                pass # don't consider removing curr cell
            elif not board[next_removal] or next_removal == next_cell:
                continue # skip if out of bounds or occupied

            # count how many moves opp has left if curr player removes next_removal
            # if no moves left, immediately sort to front
            opp_moves_after_removal = opp_moves_left - 1 if next_removal in next_moves_b_set else opp_moves_left
            if opp_moves_after_removal == 0 and prune:
                return [(-99, next_cell, next_removal)]

            # count how many moves curr player has left if curr player removes next_removal
            curr_moves_after_removal = curr_moves_left - 1 if next_removal in next_next_moves_set else curr_moves_left

            # condense tuple into 1 metric for sorting
            # smaller opp_moves_left and larger curr_moves_left == first in output
            # "base 5" since curr_moves_left <= 4
            out.append((opp_moves_after_removal * 5 - curr_moves_after_removal, next_cell, next_removal))
    out.sort()
    return out

def search(problem: dict):
    actions = problem["actions"]
    transition = problem["transition"]
    is_terminal = problem["is_terminal"]
    state = problem["initial_state"]
    path = []
    turns = 0

    while not is_terminal(state):
        acts = actions(state)
        target = 1 if turns % 2 == 0 else -1 # select which player moving
        chosen, chosen_state = None, None
        for act in acts:
            child = transition(state, act)
            if minimax(child) == target:
                # basically ezwin for this player
                chosen, chosen_state = act, child
                break

        # otherwise, rank the children by potential and pick the best
        # basically want to restrict opponent and dont restrict self as much as possible
        if chosen is None:
            chosen = acts[0]
            chosen_state = transition(state, chosen)
        path.append(chosen)
        state = chosen_state
        turns += 1
    return path


def minimax(state, alpha=-1, beta=1):
    board, a, b, turn = state
    maximizing = turn == 0
    stuck = True

    for next_move in _NEXT_MOVES[a]:
        if board[next_move]:
            stuck = False # if there's a valid move, ur not stuck duh
            break
    
    if stuck:
        return -1 if maximizing else 1 # auto lose
    
    key = (board, a, b)
    cached = _WILL_WIN.get(key)

    # if cache, return approppriate result
    if cached is not None:
        if maximizing:
            return 1 if cached else -1
        return -1 if cached else 1
    
    # else compute the best value for this state
    nt = 1 - turn
    if maximizing:
        best = -1
        for _, next_cell, next_removal in _rank(state, True):
            v = minimax((_make(board, a, next_cell, next_removal), b, next_cell, nt), alpha, beta)
            if v > best:
                best = v
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    break
        _WILL_WIN[key] = best == 1 # cache result
    else:
        best = 1
        for _, next_cell, next_removal in _rank(state, True):
            v = minimax((_make(board, a, next_cell, next_removal), b, next_cell, nt), alpha, beta)
            if v < best:
                best = v
                if best < beta:
                    beta = best
                if alpha >= beta:
                    break
        _WILL_WIN[key] = best == -1
    return best
