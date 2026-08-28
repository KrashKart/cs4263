import heapq
from collections import deque

def solve(data: dict):
    problem = build_search_representation(data)
    action_path = search(problem)

    # Convert the path into the exact output format required by this
    # project. The required output may be a path, a cost, a list of
    # states/actions, or another JSON-serialisable structure.
    return action_path


def build_search_representation(data: dict) -> dict:
    """Build the project-specific informed-search representation.

    Return a dictionary with at least these keys:
    - initial_state: the start state
    - actions(state): iterable of legal actions from state
    - transition(state, action): next state after applying action
    - is_goal(state): whether state is a goal
    - action_cost(state, action, next_state): step cost
    - heuristic(state): numeric estimate from state to a goal

    Extra keys are allowed
    """
    # i was tilted by the fact that my runtime wasnt good enough
    # so i had to resort to bit manipulation booooo
    r, c = data["rows"], data["cols"]
    bitmap = {"u": 1, "r": 2, "d": 4, "l": 8}
    grid = 0
    for i in range(r):
        for j in range(c):
            local = 0
            for d in data["cells"][i][j]:
                local += bitmap[d]
            grid += local << (4 * (i * c + j))

    # grid is now a single integer with rightmost bit being (0, 0)
    initial_state = (grid, data["starting_position"][0], data["starting_position"][1])

    def _get_pos(grid, i, j):
        # essentially extract the last 4 bits to get integer at (i, j)
        offset = 4 * (i * c + j)
        return (grid >> offset) & 0b1111

    def _rotate_pos(grid, i, j):
        # rotate the 4 bits at (i, j) to the right by 1
        # first, get bits corresponding to cell (i, j) and clear the bits in the grid there
        offset = 4 * (i * c + j)
        curr = (grid >> offset) & 0b1111
        grid = grid & ~(0b1111 << offset) # basically grid & 1111...100001....1111

        # then, rotate the bits to the left by 1 then trim to 4 bits
        # handle wraparound for leftmost bit
        new_cell = ((curr << 1) | (curr >> 3)) & 0b1111

        # then then replace the bits at (i, j) with the rotated bits
        return grid | (new_cell << offset)

    didj = {1: (-1, 0), 2: (0, 1), 3: (1, 0), 4: (0, -1)}
    opps = {1: 3, 2: 4, 3: 1, 4: 2}
    
    def actions(state):
        grid, curri, currj = state
        curr = _get_pos(grid, curri, currj) # curr is 4 bits
        for a in range(1, 5):
            # guarantee that actions never result in an out of bounds mvmt
            # also ensure cell we want to move to has a connecting path
            newi, newj = curri + didj[a][0], currj + didj[a][1]
            if 0 <= newi < data["rows"] and 0 <= newj < data["cols"] and curr & (1 << (a - 1)) and _get_pos(grid, newi, newj) & (1 << (opps[a] - 1)):
                yield a

        # no point rotating if all paths available in a cell
        if curr != 15:
            yield 5

    def transition(state, action):
        grid, curri, currj = state

        # if rotate, modify current cell and send back state
        if action == 5:
            new_grid = _rotate_pos(grid, curri, currj)
            return (new_grid, curri, currj)
        
        # else, move the guy
        new_i, new_j = curri + didj[action][0], currj + didj[action][1]
        return (grid, new_i, new_j)

    def is_goal(state):
        _, curri, currj = state
        return [curri, currj] in data["goals"]

    # l1 distance will consistently underestimate/estimate exactly --> admissible
    def heuristic(state):
        _, curri, currj = state
        return min(abs(curri - gi) + abs(currj - gj) for gi, gj in data["goals"]) * data["movement_cost"]

    return {"initial_state": initial_state,
            "actions": actions,
            "transition": transition,
            "is_goal": is_goal,
            "action_cost": lambda s, a, ns: data["rotation_cost"] if a == 5 else data["movement_cost"],
            "heuristic": heuristic}

def search(problem: dict):
    """Run the required informed search algorithm.

    This function must work using at least the required problem keys:
    initial_state, actions, transition, is_goal, action_cost, heuristic.
    It must use heuristic(state) to score states.

    Return a list of actions. The solve(data) function is responsible for
    converting this action path into the exact output required by the project.
    """
    tiebreaker = 0
    init, actions, transition, is_goal, action_cost, h = problem.values()
    h_start = h(init)
    frontier = [(h_start, tiebreaker, 0, init, 0)] # f = h, tiebreaker, g, state, steps

    heapq.heapify(frontier)
    visited = {init: 0} # for lowest path cost (g) found for a state

    # use graph search V2 to prune paths with revisited nodes early as much as possible 
    while frontier:
        f, _, g, state, steps = heapq.heappop(frontier)

        if is_goal(state):
            final_path = deque()
            while steps:
                final_path.appendleft(steps % 10)
                steps //= 10
            return (list(final_path), g)

        for action in problem["actions"](state):
            next_state = problem["transition"](state, action)
            if next_state not in visited or g + problem["action_cost"](state, action, next_state) < visited[next_state]:
                tiebreaker += 1
                action_cost = problem["action_cost"](state, action, next_state)
                h_new = problem["heuristic"](next_state)
                heapq.heappush(frontier, (g + action_cost + h_new, tiebreaker, g + action_cost, next_state, steps * 10 + action))
                visited[next_state] = g + action_cost

    return ([], -1)