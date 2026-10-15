"""Run your agent on this project's practice cases.

Each run calls your run_agent(env) and prints its return value next to a
saved example answer. Other gold subsets and orders may also be valid.

Usage, from this folder:

    python run_local.py                  # every case in input/
    python run_local.py case_01.json     # only the named case(s)

You may edit or change this file however you like.
"""

import json
import sys
import time
from pathlib import Path
from pprint import pprint

import environment  # registers the Wumpus World rules with the runtime
import solution
from logic import Environment


ROOT = Path(__file__).resolve().parent


def run_case(name):
    data = json.loads((ROOT / "input" / name).read_text(encoding="utf-8"))
    expected_path = ROOT / "output" / name
    expected = (
        json.loads(expected_path.read_text(encoding="utf-8"))
        if expected_path.is_file()
        else None
    )

    env = Environment(data)
    start = time.perf_counter()
    observed = solution.run_agent(env)
    elapsed = time.perf_counter() - start

    print(f"== {name}  ({elapsed:.3f}s)")
    print("-- your agent returned:")
    pprint(observed)
    if expected is None:
        print(f"-- no expected output saved (output/{name})")
    else:
        print(f"-- example answer (output/{name}; other answers may be valid):")
        pprint(expected["answer"])
    # To draw this case and your agent's own run, uncomment:
    from visualise_wumpus_world import visualise_wumpus_world
    print(visualise_wumpus_world(
        example_input=data,
        expected_output=expected,
        candidate_output={"answer": observed, "episode": env.result()},
        file_name=name,
    ))
    print()


def main():
    names = sys.argv[1:] or sorted(
        path.name for path in (ROOT / "input").glob("*.json")
    )
    for name in names:
        run_case(name)


if __name__ == "__main__":
    main()
