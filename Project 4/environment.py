"""Environment definition for the Simple Wumpus World project.

The hidden world is a ``rows`` x ``cols`` grid holding three kinds of object:

    world = {
        "pits":   [[r, c], ...],   # zero or more pit cells
        "wumpus": [r, c],          # exactly one wumpus cell
        "gold":   [[r, c], ...],   # zero or more gold cells
    }

Public config carries ``rows``, ``cols`` and ``gold_required``.
The agent starts on the top-left cell ``[0, 0]``
and learns the world only through percepts:

    breeze   a pit is orthogonally adjacent to the current cell
    stench   the wumpus is orthogonally adjacent to the current cell
    glitter  the current cell held gold, which was just collected

Its only action is ``move(row, col)``: a jump onto any in-grid cell that
touches the visited region. The episode ends as a loss on stepping into a
pit or the wumpus, and as a win once ``gold_required`` gold has been
collected. The expected answer is the list of collected gold cells (length
equal to ``gold_required``) — derivable purely from glitter percepts, never
from reading the hidden world.

"""

try:
    from logic import IllegalAction, register_environment
except ImportError:
    pass


# Orthogonal (north/south/west/east) neighbour offsets, in fixed order so
# every percept and legality check iterates deterministically.
_ORTHOGONAL = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _int_args(args, count, action):
    """Shared handler guard: exactly ``count`` integer arguments."""
    if len(args) != count or not all(type(arg) is int for arg in args):
        raise IllegalAction(
            "%s expects %d integer argument(s), got %r" % (action, count, list(args))
        )
    return args


def _require_int(config, key, minimum):
    """Validate a config integer so students may TELL it as an axiom."""
    value = config.get(key)
    if type(value) is not int or value < minimum:
        raise ValueError(
            "config[%r] must be an integer >= %d, got %r" % (key, minimum, value)
        )
    return value


class _SimpleWumpusWorld:
    """The Simple Wumpus World rules (see the module docstring)."""

    # config.environment value that selects this definition in every case.
    name = "simple_wumpus_world"
    # Public config keys this definition cannot run without.
    required_config = ("rows", "cols", "gold_required")

    percept_schema = {
        "breeze": (
            "bool - True iff at least one pit sits on a cell orthogonally "
            "adjacent (north/south/east/west, inside the grid) to your "
            "current cell; False otherwise. Diagonal and out-of-grid cells "
            "never contribute."
        ),
        "stench": (
            "bool - True iff the single wumpus sits on a cell orthogonally "
            "adjacent (north/south/east/west, inside the grid) to your "
            "current cell; False otherwise. Diagonal and out-of-grid cells "
            "never contribute."
        ),
        "glitter": (
            "bool - True only on the step that enters a cell holding gold, "
            "signalling that the gold was just picked up (that cell's "
            "[row, col] belongs in the answer). A cell glitters at most once; "
            "re-entering an already-collected cell reports False."
        ),
    }

    action_schema = {
        "move": (
            "move(row, col) - attempt to step onto grid cell [row, col]; row "
            "and col are integers. The move is legal iff [row, col] lies "
            "inside the grid (0 <= row < rows and 0 <= col < cols) AND is "
            "orthogonally adjacent to at least one cell you have already "
            "entered (the start cell [0, 0] counts as visited from the "
            "outset); an illegal move raises IllegalAction and ends the "
            "episode. A legal move relocates you to [row, col] and "
            "automatically collects any gold there, while entering a pit or "
            "the wumpus cell ends the episode as a loss."
        ),
    }

    def __init__(self):
        self.handlers = {"move": self._move}

    # -- construction ------------------------------------------------------
    def load_world(self, config, world):
        """Validate the hidden world against config; return it JSON-able."""
        rows = _require_int(config, "rows", 1)
        cols = _require_int(config, "cols", 1)
        # gold_required is validated for soundness but is a goal threshold,
        # not a claim about how much gold exists; total-gold sufficiency and
        # winnability are the input validators' concern.
        _require_int(config, "gold_required", 0)

        if not isinstance(world, dict):
            raise ValueError(
                "world must be an object with 'pits', 'wumpus' and 'gold'"
            )
        for key in ("pits", "wumpus", "gold"):
            if key not in world:
                raise ValueError("world is missing required key %r" % key)
        extra = sorted(set(world) - {"pits", "wumpus", "gold"})
        if extra:
            raise ValueError("world has unexpected key(s): %s" % ", ".join(extra))

        def parse_cell(value, label):
            if (
                not isinstance(value, (list, tuple))
                or len(value) != 2
                or not all(type(coord) is int for coord in value)
            ):
                raise ValueError(
                    "%s must be a [row, col] pair of integers, got %r"
                    % (label, value)
                )
            r, c = value
            if not (0 <= r < rows and 0 <= c < cols):
                raise ValueError(
                    "%s %r is outside the %dx%d grid" % (label, [r, c], rows, cols)
                )
            return (r, c)

        if not isinstance(world["pits"], list):
            raise ValueError("world['pits'] must be a list of [row, col] pairs")
        pits = [parse_cell(entry, "pit") for entry in world["pits"]]
        if len(set(pits)) != len(pits):
            raise ValueError("world['pits'] lists a cell more than once")

        if not isinstance(world["gold"], list):
            raise ValueError("world['gold'] must be a list of [row, col] pairs")
        gold = [parse_cell(entry, "gold") for entry in world["gold"]]
        if len(set(gold)) != len(gold):
            raise ValueError("world['gold'] lists a cell more than once")

        # Exactly one wumpus always exists in the grid.
        wumpus = parse_cell(world["wumpus"], "wumpus")

        pit_set, gold_set = set(pits), set(gold)
        # At most one object per cell (a cell may still reveal many percepts).
        if wumpus in pit_set or wumpus in gold_set:
            raise ValueError("the wumpus cell also holds another object")
        if pit_set & gold_set:
            raise ValueError("a pit cell also holds gold")
        # The start cell is known-safe and, by this project's rule, empty of
        # gold (initial_state cannot see the world, so start-cell gold could
        # not be collected consistently).
        if (0, 0) in pit_set:
            raise ValueError("the start cell [0, 0] must not contain a pit")
        if wumpus == (0, 0):
            raise ValueError("the start cell [0, 0] must not contain the wumpus")
        if (0, 0) in gold_set:
            raise ValueError("the start cell [0, 0] must not contain gold")

        return {
            "pits": sorted([list(cell) for cell in pits]),
            "wumpus": list(wumpus),
            "gold": sorted([list(cell) for cell in gold]),
        }

    def initial_state(self, config):
        """The visible state before any action: on the start cell, empty-handed."""
        return {
            "position": [0, 0],
            "visited": [[0, 0]],
            "collected": [],
            "picked_gold": False,
        }

    # -- observation -------------------------------------------------------
    def percepts(self, config, hidden, state, last_action):
        """The percept dict for the current cell (never emits is_terminal)."""
        row, col = state["position"]
        pits = {tuple(cell) for cell in hidden["pits"]}
        wumpus = tuple(hidden["wumpus"])
        breeze = any((row + dr, col + dc) in pits for dr, dc in _ORTHOGONAL)
        stench = any((row + dr, col + dc) == wumpus for dr, dc in _ORTHOGONAL)
        return {
            "breeze": breeze,
            "stench": stench,
            "glitter": bool(state["picked_gold"]),
        }

    def terminal(self, config, hidden, state):
        """End on death (loss) or once enough gold has been collected (win)."""
        position = tuple(state["position"])
        if position == tuple(hidden["wumpus"]):
            return ("failure", "eaten_by_wumpus")
        if position in {tuple(cell) for cell in hidden["pits"]}:
            return ("failure", "fell_in_pit")
        if len(state["collected"]) >= config["gold_required"]:
            return ("success", "collected_required_gold")
        return None

    # -- handlers ----------------------------------------------------------
    def _move(self, config, hidden, state, *args):
        row, col = _int_args(args, 2, "move")  # validate arguments first...
        rows, cols = config["rows"], config["cols"]
        if not (0 <= row < rows and 0 <= col < cols):
            raise IllegalAction(
                "move(%d, %d) leaves the %dx%d grid" % (row, col, rows, cols)
            )
        visited = {tuple(cell) for cell in state["visited"]}
        if not any((row + dr, col + dc) in visited for dr, dc in _ORTHOGONAL):
            raise IllegalAction(
                "move(%d, %d) is not orthogonally adjacent to any visited cell"
                % (row, col)
            )
        # ...then apply effects to the visible state only (each stored cell is
        # its own list, so nothing aliases the position across steps).
        state["position"] = [row, col]
        if (row, col) not in visited:
            state["visited"].append([row, col])
            state["visited"].sort()
        gold = {tuple(cell) for cell in hidden["gold"]}
        collected = {tuple(cell) for cell in state["collected"]}
        if (row, col) in gold and (row, col) not in collected:
            state["collected"].append([row, col])
            state["collected"].sort()
            state["picked_gold"] = True
        else:
            state["picked_gold"] = False


register_environment(_SimpleWumpusWorld())
