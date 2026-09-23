def ac3(problem, var, assignment):
    # copy domain and assign assigned variables
    domains = {v: list(problem["domain_values"][v]) for v in problem["variables"]}
    for v, assigned_val in assignment.items():
        domains[v] = [assigned_val]

    queue = deque()
    in_queue = set()

    for c in problem["constraints_by_variable"].get(var, []):
        for neighbor in c["scope"]:
            if neighbor not in assignment:
                arc = (c["scope"], neighbor)
                if arc not in in_queue:
                    queue.append((c, neighbor))
                    in_queue.add(arc)

    while queue:
        c, x = queue.popleft()
        in_queue.remove((c["scope"], x))

        revised = False
        new_domain_x = []

        other_vars = [v for v in c["scope"] if v != x]
        other_domains = [domains[v] for v in other_vars]

        for val_x in domains[x]:
            has_support = False
            for combination in itproduct(*other_domains):
                val_map = {v: combination[i] for i, v in enumerate(other_vars)}
                val_map[x] = val_x

                args = [val_map[v] for v in c["scope"]]
                if c["rel"](*args):
                    has_support = True
                    break

            if has_support:
                new_domain_x.append(val_x)
            else:
                revised = True

        if revised:
            if not new_domain_x:
                return None

            domains[x] = new_domain_x

            # re-queue constraints
            for c_neighbor in problem["constraints_by_variable"].get(x, []):
                if c_neighbor != c:
                    for v in c_neighbor["scope"]:
                        if v != x and v not in assignment:
                            arc = (c_neighbor["scope"], v)
                            if arc not in in_queue:
                                queue.append((c_neighbor, v))
                                in_queue.add(arc)

    for v in assignment:
        domains[v] = problem["domain_values"][v]

    return domains