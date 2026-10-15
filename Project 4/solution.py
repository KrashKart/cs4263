# ===== LOCKED (do not edit) =================================================

from logic import Environment, KnowledgeBase, pretty
import environment

def solve(data):
    env = Environment(data)
    answer = run_agent(env)
    return {"answer": answer, "episode": env.result()}

# ===== YOUR CODE (everything below is your Coursemology submission) =========
# from pprint import pprint

def run_agent(env):
    r, c, gold_required = env.config["rows"], env.config["cols"], env.config["gold_required"]

    # standard bounds checking and neighbour functions
    def in_bounds(i, j):
        return 0 <= i < r and 0 <= j < c

    def neighbours(i, j):
        return [(i + di, j + dj) for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)) if in_bounds(i + di, j + dj)]

    def _pit(i, j): 
        return f"p_{i}_{j}"
    
    def _wumpus(i, j): 
        return f"w_{i}_{j}"

    # tell kb initial knowledge
    kb = KnowledgeBase()
    kb.tell(f"~{_pit(0, 0)}")
    kb.tell(f"~{_wumpus(0, 0)}")

    def update_kb(i, j, percept):
        # assume all cells visited are safe so no pit no wumpus
        visited.add((i, j))
        safe.add((i, j))
        kb.tell(f"~{_pit(i, j)}")
        kb.tell(f"~{_wumpus(i, j)}")

        nbrs = neighbours(i, j)

        # tell adjacent conditions regardless of if there are 
        # actually pits/wumpuses (vacuously true)
        if percept["breeze"]:
            kb.tell(" | ".join(_pit(*n) for n in nbrs))
        else:
            for n in nbrs:
                kb.tell(f"~{_pit(*n)}")

        if percept["stench"]:
            kb.tell(" | ".join(_wumpus(*n) for n in nbrs))

            # 1 wumpus only
            # for all stench neighbours not in the wumpus_candidates, 
            # wumpus is either the wumpus_candidates or in these stench neighbours
            for n in nbrs:
                if n not in wumpus_candidates:
                    for m in wumpus_candidates:
                        kb.tell(f"~{_wumpus(*n)} | ~{_wumpus(*m)}")
                    wumpus_candidates.add(n)
        else:
            for n in nbrs:
                kb.tell(f"~{_wumpus(*n)}")

        if percept["glitter"] and (i, j) not in gold:
            gold.append((i, j))

    # setup and main loop
    visited = set()
    safe = set()
    wumpus_candidates = set()
    frontier = set()
    gold = []

    # initialise frontier
    for ni, nj in neighbours(0, 0):
        frontier.add((ni, nj))

    # get initial percepts at (0, 0), update KB
    percept = env.get_percept()
    update_kb(0, 0, percept)
    if percept["is_terminal"] or len(gold) >= gold_required:
        return gold
    
    while True:
        # if known to be safe, visit
        target = None
        for (i, j) in sorted(frontier):
            if (i, j) in safe:
                target = (i, j)
                break

        # else, ask KB is this safe? and visit if it is
        if target is None:
            for (i, j) in sorted(frontier):
                if kb.ask(f"(~{_wumpus(i, j)})&(~{_pit(i, j)})"):
                    safe.add((i, j))
                    if target is None:
                        target = (i, j)

        if target is None:
            break

        ni, nj = target

        # update frontier
        frontier.remove((ni, nj))
        for nni, nnj in neighbours(ni, nj):
            if (nni, nnj) not in visited:
                frontier.add((nni, nnj))

        # move and update KB with new percepts
        env.act("move", ni, nj)
        percept = env.get_percept()
        update_kb(ni, nj, percept)

        # quit early if can pangkang
        if percept["is_terminal"] or len(gold) >= gold_required:
            break

    return gold