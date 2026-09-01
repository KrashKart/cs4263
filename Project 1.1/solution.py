from collections import deque

def solve(data: dict):
    problem = build_search_representation(data)
    action_path = search(problem)
    clean_path = None if not action_path else list(map(lambda x: [x[0][1], x[0][0]], action_path))
    # Convert the path into the exact output format required by this
    # project. The required output may be a path, a cost, a list of
    # states/actions, or another JSON-serialisable structure.
    return clean_path


def build_search_representation(data: dict) -> dict:
    """Build the project-specific search representation.

    Return a dictionary with at least these keys:
    - initial_state: the start state
    - actions(state): iterable of legal actions from state
    - transition(state, action): next state after applying action
    - is_goal(state): whether state is a goal
    - action_cost(state, action, next_state): step cost

    Extra keys are allowed
    """
    n, m = data["rows"], data["cols"]
    grid = tuple(tuple(data["grid"][i][j] for i in range(n)) for j in range(m))
    n, m = m, n # swap cos stupid transpose

    def action(grid):
        visited = [[False for _ in range(m)] for _ in range(n)]
        groups = []

        def neighbors(i, j):
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < n and 0 <= nj < m:
                    # generator is btr than returning list for lazy loading
                    yield ni, nj

        # recursively checks neighbours of grid[i][j] and adds to group
        # if no neighbours, terminates
        def flood_fill(i, j):
            curr = grid[i][j]
            stack = [(i, j)]
            visited[i][j] = True
            group = [(i, j)]
            while stack:
                curri, currj = stack.pop()
                for ni, nj in neighbors(curri, currj):
                    if not visited[ni][nj] and grid[ni][nj] == curr and curr != 0:
                        visited[ni][nj] = True
                        stack.append((ni, nj))
                        group.append((ni, nj))
            return group

        for i in range(n):
            for j in range(m):
                if not visited[i][j] and grid[i][j] is not None:
                    group = flood_fill(i, j)
                    if len(group) >= 3:
                        # must transform by leftmost column first (cos of the removal process)
                        groups.append(sorted(group, key=lambda x: x[1]))

        return groups

    def trans(grid, action):
        new_grid = list(grid)
        for i, j in action:
            new_grid[i] = (0,) + new_grid[i][:j] + new_grid[i][j + 1:]
        return tuple(new_grid)
    
    is_goal = lambda x: all(all(not z for z in y) for y in x)
    action_cost = lambda s, a, ns: 1

    return {"initial_state": grid,
            "actions": action,
            "transition": trans,
            "is_goal": is_goal,
            "action_cost": action_cost}

def search(problem: dict):
    start = problem["initial_state"]
    if problem["is_goal"](start):
        return []

    # track nodes for backtracking
    nodes = [(start, None, None)]
    visited = {start: 0}
    frontier = deque([0])

    while frontier:
        curr_idx = frontier.popleft()
        curr_state = nodes[curr_idx][0]

        for action in problem["actions"](curr_state):
            new_state = problem["transition"](curr_state, action)

            if problem["is_goal"](new_state):
                # late checking + backtrack
                final_path = [action]
                idx = curr_idx
                while nodes[idx][1] is not None:
                    _, parent_idx, a = nodes[idx]
                    final_path.append(a)
                    idx = parent_idx
                final_path.reverse()
                return final_path

            if new_state not in visited:
                new_idx = len(nodes)
                nodes.append((new_state, curr_idx, action))
                visited[new_state] = new_idx
                frontier.append(new_idx)

    return None