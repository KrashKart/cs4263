from math import prod

def solve(data: dict):
    problem = build_csp_representation(data)
    assignment = search(problem)

    # Convert the assignment into the exact output format required by this
    # project. The required output may be a list of variable/value pairs, a
    # grid, or another JSON-serialisable structure; an unsatisfiable case
    # (assignment is None) usually maps to null.
    
    # return early if None
    if assignment is None:
        return None

    n = data["n"]
    grid = [[0] * n for _ in range(n)]
    for (r, c), val in assignment.items():
        grid[r][c] = val
    return grid

def build_csp_representation(data: dict) -> dict:
    """Build the project-specific CSP representation.
    Return a dictionary with at least these keys:
    - variables: sequence of hashable variable identifiers in a stable order
    - domain_values(variable): candidate values for that variable, in a
      stable order
    - constraints: sequence of {"scope": (variables...), "rel": callable}
      entries where rel takes one value per scope variable (in scope order)
      and returns whether the constraint is satisfied

    Extra keys are allowed
    """
    n = data["n"]
    variables = tuple((i, j) for i in range(n) for j in range(n))
    domain_values = {}
    constraints = []
    var_to_sections = {var: None for var in variables}

    def add_constraint(scope, op, target, rel):
        con = {"scope": scope, "rel": rel}
        constraints.append(con)
        for var in scope:
            var_to_sections[var] = {"scope": scope, "op": op, "target": target}

    rcs = {var: set() for var in variables}
    for r, c in variables:
        for col in range(n):
            if col != c:
                rcs[(r, c)].add((r, col))
        for row in range(n):
            if row != r:
                rcs[(r, c)].add((row, c))

    for section in data["sections"]:
        scope = tuple(tuple(cell) for cell in section[0])
        op = section[1]
        target = section[2]

        # for each section type, conduct stricter checks to
        # prune early even on partial assignments and preprocess domains
        if op == "+":
            def sum_rel(*vals, t = target):
                assigned = [v for v in vals if v is not None]
                if len(assigned) == len(vals):
                    return sum(assigned) == t
                unassigned = len(vals) - len(assigned)
                curr_sum = sum(assigned)
                return curr_sum + unassigned * 1 <= t and curr_sum + unassigned * n >= t

            add_constraint(scope, op, target, sum_rel)

            sz = len(scope)
            for var in scope:
                domain_values[var] = [v for v in range(1, n + 1) if (v + (sz - 1) * 1 <= target <= v + (sz - 1) * n)]

        elif op == "*":
            def prod_rel(*vals, t=target):
                assigned = [v for v in vals if v is not None]
                if len(assigned) == len(vals):
                    return prod(assigned) == t
                curr_prod = prod(assigned) if assigned else 1
                unassigned = len(vals) - len(assigned)
                return curr_prod <= t and t % curr_prod == 0 and curr_prod * (n ** unassigned) >= t

            add_constraint(scope, op, target, prod_rel)

            sz = len(scope)
            for var in scope:
                domain_values[var] = [v for v in range(1, n + 1) if target % v == 0]

        elif op == "-":
            def diff_rel(x, y, t=target):
                if x is None and y is None:
                    return True
                elif x is not None and y is not None:
                    return abs(x - y) == t
                val = x if x is not None else y
                return val + t <= n or val - t >= 1

            add_constraint(scope, op, target, diff_rel)

            for var in scope:
                domain_values[var] = [v for v in range(1, n + 1) if v + target <= n or v - target >= 1]

        elif op == "/":
            def div_rel(x, y, t=target):
                if x is None and y is None:
                    return True
                elif x is not None and y is not None:
                    return (x == y * t) if x >= y else (y == x * t)
                val = x if x is not None else y
                return val * t <= n or val % t == 0

            add_constraint(scope, op, target, div_rel)

            for var in scope:
                domain_values[var] = [v for v in range(1, n + 1) if v * target <= n or (v % target == 0)]

    degree = {var: len(rcs[var]) + len(var_to_sections[var]["scope"]) - 1 for var in variables}

    return {
        "variables": variables,
        "domain_values": lambda var: domain_values[var],
        "constraints": constraints,
        "initial_domains": domain_values,
        "var_to_sections": var_to_sections,
        "rcs": rcs,
        "degree": degree,
        "n": n,
    }

def search(problem: dict):
    """Run backtracking search over the CSP.
    This function must work using at least the required problem keys:
    variables, domain_values, constraints. Derive any indexes you need from
    them once at the start - for example constraints grouped by variable, so
    consistency checks only visit the constraints touching the variable just
    assigned.

    Return a dictionary mapping every variable to a domain value that
    satisfies all constraints, or None when no such assignment exists. The
    solve(data) function is responsible for converting the assignment into
    the exact output required by the project.
    """
    domains = {v: list(problem["initial_domains"][v]) for v in problem["variables"]}
    assignment = {}
    changelog = []
    unassigned = set(problem["variables"])
    return backtrack(problem, assignment, domains, changelog, unassigned)

def backtrack(problem, assignment, domains, changelog, unassigned):
    # legit bread and butter backtrack with forward checking
    # MRV + degree tiebreak and some extra pruning
    if not unassigned:
        return assignment

    var = select_unassigned_variable(problem, domains, unassigned)

    for val in domains[var]:
        if not is_consistent(problem, assignment, var, val):
            continue

        assignment[var] = val
        unassigned.discard(var)
        mark = len(changelog)

        if forward_checking(problem, assignment, domains, changelog, var, val):
            result = backtrack(problem, assignment, domains, changelog, unassigned)
            if result is not None:
                return result

        restore(domains, changelog, mark)
        del assignment[var]
        unassigned.add(var)

    return None

def select_unassigned_variable(problem, domains, unassigned):
    # MRV, tiebreak on degree with all variables, not only unassigned
    var_to_sections = problem["var_to_sections"]
    degree = problem["degree"]
    return min(unassigned, key=lambda v: (len(domains[v]), len(var_to_sections[v]["scope"]), -degree[v]))

def is_consistent(problem, assignment, var, val):
    # row and column checks alr guaranteed in forward checking
    section = problem["var_to_sections"][var]
    scope = section["scope"]
    op = section["op"]
    target = section["target"]

    assigned_vals = [val if v == var else assignment[v] for v in scope if v == var or v in assignment]

    if len(assigned_vals) == len(scope):
        if op == "+" and sum(assigned_vals) != target:
            return False
        elif op == "*" and prod(assigned_vals) != target:
            return False
        elif op == "-" and abs(assigned_vals[0] - assigned_vals[1]) != target:
            return False
        elif op == "/":
            a, b = assigned_vals[0], assigned_vals[1]
            if not ((a == b * target) if a >= b else (b == a * target)):
                return False

    return True

def forward_checking(problem, assignment, domains, changelog, var, val):
    # check row/column constraint here
    # 1. any previously assigned var is guaranteed to be consistent
    # 2. otherwise, remove val from the domain of unassigned vars
    for pos in problem["rcs"][var]:
        if pos not in assignment:
            dom = domains[pos]
            if val in dom:
                new_domain = [x for x in dom if x != val]
                if not new_domain:
                    return False
                set_domain(domains, changelog, pos, new_domain)

    n = problem["n"]
    section = problem["var_to_sections"][var]
    scope = section["scope"]
    op = section["op"]
    target = section["target"]

    unassigned_vars = [v for v in scope if v not in assignment]
    if not unassigned_vars:
        return True

    assigned_vals = [assignment[v] for v in scope if v in assignment]
    rem_len = len(unassigned_vars)

    # forward checking for section constraints
    if op == "+":
        curr_sum = sum(assigned_vals)
        if curr_sum + rem_len * 1 > target or curr_sum + rem_len * n < target:
            return False
    elif op == "*":
        curr_prod = prod(assigned_vals) if assigned_vals else 1
        if curr_prod > target or target % curr_prod != 0 or (curr_prod * (n ** rem_len) < target):
            return False

    if rem_len == 1:
        target_var = unassigned_vars[0]
        dom = domains[target_var]
        new_domain = []

        if op == "+":
            needed = target - sum(assigned_vals)
            if needed in dom:
                new_domain = [needed]
        elif op == "*":
            curr_p = prod(assigned_vals) if assigned_vals else 1
            if target % curr_p == 0:
                needed = target // curr_p
                if needed in dom:
                    new_domain = [needed]
        elif op == "-":
            other_val = assigned_vals[0]
            new_domain = [v for v in dom if abs(other_val - v) == target]
        elif op == "/":
            other_val = assigned_vals[0]
            new_domain = [v for v in dom if (other_val == v * target if other_val >= v else v == other_val * target)]

        if not new_domain:
            return False

        if len(new_domain) != len(dom):
            set_domain(domains, changelog, target_var, new_domain)

    else:
        other_unassigned_count = rem_len - 1
        curr_p = prod(assigned_vals) if assigned_vals else 1
        curr_s = sum(assigned_vals)

        for u_var in unassigned_vars:
            dom = domains[u_var]
            valid_vals = []

            for candidate in dom:
                if op == "+":
                    new_sum = curr_s + candidate
                    if new_sum + other_unassigned_count * 1 <= target <= new_sum + other_unassigned_count * n:
                        valid_vals.append(candidate)
                elif op == "*":
                    new_p = curr_p * candidate
                    if new_p <= target and target % new_p == 0 and (new_p * (n ** other_unassigned_count) >= target):
                        valid_vals.append(candidate)
                else:
                    valid_vals.append(candidate)

            if not valid_vals:
                return False

            if len(valid_vals) != len(dom):
                set_domain(domains, changelog, u_var, valid_vals)

    return True

def set_domain(domains, changelog, var, new_domain):
    # helper function to set domain and track changes
    changelog.append((var, domains[var]))
    domains[var] = new_domain

def restore(domains, changelog, mark):
    # undo changes
    while len(changelog) > mark:
        var, old_domain = changelog.pop()
        domains[var] = old_domain
