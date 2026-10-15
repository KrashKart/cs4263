"""CS4246 Logical Agents runtime: sentence language, knowledge base, environment.

SENTENCE LANGUAGE
    Sentences are plain strings over propositional symbols in lecture
    notation::

        operators   ~ (not)   & (and)   | (or)   => (implies)   <=> (iff)
        precedence  ~ , then &, then |, then the implications
        symbols     letters/digits/underscores, starting with a letter
                    (leading underscores are disallowed)

    Examples::

        "B_1_1 <=> (P_1_2 | P_2_1)"
        "~B_1_1"
        "(A => B) <=> C"

    Rules worth knowing:

    - Chained or mixed arrows without parentheses are rejected: write
      ``(A => B) => C``, never ``A => B => C``.
    - When building sentences using f-strings, parenthesise
      every fragment: ``f"~({x})"`` because the unparenthesised ``f"~{x}"`` applied
      to ``x = "A | B"`` silently means ``(~A) | B`` rather than ``f"~(A | B")``.
    - ``pretty(sentence)`` returns the fully parenthesised reading the parser
      understood; use it whenever an axiom misbehaves.

KNOWLEDGE BASE
    ``kb = KnowledgeBase()``

    - ``kb.tell(sentence)`` adds a sentence to the KB. It parses immediately
      (raising ``SentenceError`` on bad syntax) but performs NO inference,
      and it can accept sentences that contradict the KB .
    - ``kb.ask(sentence) -> bool`` Checks whether the KB entails this sentence.
    - ``kb.consistent() -> bool`` — Checks if the KB is satisfiable or contains contradictions.
    - ``kb.print_kb()`` prints the numbered, prettified KB and returns None.

ENVIRONMENT
    - ``env.config`` — a copy of the case's public config dict.
    - ``env.get_percept()`` — a copy of the current percept (pure read).
    - ``env.act(name, *args)`` — perform an action: records it, advances the
      world, and returns the new percept dict.
    - ``env.result()`` — the recorded episode:
      ``{"steps": [...], "status": ..., "reason": ...}``.
"""

import ast as _ast
import json as _json
import re as _re
import sys as _sys

__all__ = [
    "Environment",
    "IllegalAction",
    "KnowledgeBase",
    "SentenceError",
    "pretty",
    "register_environment",
]


class SentenceError(ValueError):
    """A sentence string could not be parsed."""


class IllegalAction(Exception):
    """Raised by environment rules when an action is not permitted right now.

    Also raised for any action once the episode has ended — the terminal
    percept (``is_terminal: true``) is the signal to stop acting.
    """



_TOKEN_RE = _re.compile(r"\s+|<=>|=>|[~&|()]|[A-Za-z_][A-Za-z0-9_]*")


def _prescan(text):
    """Reject anything outside the sentence vocabulary, with a column."""
    position = 0
    while position < len(text):
        match = _TOKEN_RE.match(text, position)
        if match is None:
            raise SentenceError(
                "unexpected character %r at column %d in: %s"
                % (text[position], position + 1, text)
            )
        token = match.group()
        if token.startswith("_"):
            raise SentenceError(
                "symbol %r at column %d starts with an underscore, which is "
                "reserved for engine internals: %s" % (token, position + 1, text)
            )
        position = match.end()


def _parse(text):
    if not isinstance(text, str):
        raise SentenceError(
            "sentence must be a string, got %s" % type(text).__name__
        )
    if not text.strip():
        raise SentenceError("empty sentence")
    _prescan(text)
    pythonish = text.replace("<=>", "== ").replace("=>", ">=")
    try:
        node = _ast.parse(pythonish, mode="eval")
    except SyntaxError as error:
        column = error.offset or 1
        raise SentenceError(
            "could not parse sentence at column %d: %s" % (column, text)
        ) from None
    return _from_ast(node.body, text)


def _from_ast(node, text):
    if isinstance(node, _ast.Name):
        return ("sym", node.id)
    if isinstance(node, _ast.Constant):
        raise SentenceError(
            "%r is not a symbol — True/False constants are not part of the "
            "sentence language: %s" % (node.value, text)
        )
    if isinstance(node, _ast.UnaryOp):
        if isinstance(node.op, _ast.Invert):
            return ("~", _from_ast(node.operand, text))
        if isinstance(node.op, _ast.Not):
            raise SentenceError("use ~ rather than 'not': %s" % text)
        raise SentenceError("unsupported operator in sentence: %s" % text)
    if isinstance(node, _ast.BinOp) and isinstance(node.op, (_ast.BitAnd, _ast.BitOr)):
        operator = "&" if isinstance(node.op, _ast.BitAnd) else "|"
        return (
            operator,
            _from_ast(node.left, text),
            _from_ast(node.right, text),
        )
    if isinstance(node, _ast.BoolOp):
        raise SentenceError("use & and | rather than 'and'/'or': %s" % text)
    if isinstance(node, _ast.Compare):
        if len(node.ops) != 1:
            raise SentenceError(
                "chained or mixed arrows need parentheses, for example "
                "(A => B) <=> C: %s" % text
            )
        operation = node.ops[0]
        if isinstance(operation, _ast.GtE):
            operator = "=>"
        elif isinstance(operation, _ast.Eq):
            operator = "<=>"
        else:
            raise SentenceError("unsupported comparison in sentence: %s" % text)
        return (
            operator,
            _from_ast(node.left, text),
            _from_ast(node.comparators[0], text),
        )
    raise SentenceError("unsupported construct in sentence: %s" % text)


def _render(tree):
    kind = tree[0]
    if kind == "sym":
        return tree[1]
    if kind == "~":
        return "(~%s)" % _render(tree[1])
    return "(%s %s %s)" % (_render(tree[1]), kind, _render(tree[2]))


def pretty(sentence):
    """Return the fully parenthesised reading of ``sentence``.

    ``pretty("~A | B & C")`` -> ``"((~A) | (B & C))"``. Use it to check that
    a built-up sentence groups the way you meant.
    """
    return _render(_parse(sentence))



def _clauses(trees):
    """Return CNF clauses (tuples of ``(symbol, polarity)``) for the trees."""
    memo = {}
    clauses = []
    counter = [0]

    def walk(tree):
        if tree in memo:
            return memo[tree]
        kind = tree[0]
        if kind == "sym":
            memo[tree] = tree[1]
            return tree[1]
        variable = "__aux%d" % counter[0]
        counter[0] += 1
        if kind == "~":
            a = walk(tree[1])
            clauses.append(((variable, False), (a, False)))
            clauses.append(((variable, True), (a, True)))
        else:
            a = walk(tree[1])
            b = walk(tree[2])
            if kind == "&":
                clauses.append(((variable, False), (a, True)))
                clauses.append(((variable, False), (b, True)))
                clauses.append(((variable, True), (a, False), (b, False)))
            elif kind == "|":
                clauses.append(((variable, False), (a, True), (b, True)))
                clauses.append(((variable, True), (a, False)))
                clauses.append(((variable, True), (b, False)))
            elif kind == "=>":
                clauses.append(((variable, False), (a, False), (b, True)))
                clauses.append(((variable, True), (a, True)))
                clauses.append(((variable, True), (b, False)))
            else:  # "<=>"
                clauses.append(((variable, False), (a, False), (b, True)))
                clauses.append(((variable, False), (a, True), (b, False)))
                clauses.append(((variable, True), (a, True), (b, True)))
                clauses.append(((variable, True), (a, False), (b, False)))
        memo[tree] = variable
        return variable

    for tree in trees:
        clauses.append(((walk(tree), True),))
    return clauses

# DPLL algorithm for satisfiability

def _satisfiable(raw_clauses):
    clauses = []
    for clause in raw_clauses:
        literals = tuple(dict.fromkeys(clause))
        literal_set = set(literals)
        if any((symbol, not polarity) in literal_set for symbol, polarity in literals):
            continue  # tautological clause
        clauses.append(literals)
    symbols = {symbol for clause in clauses for symbol, _ in clause}
    needed = 2 * len(symbols) + 1000
    if _sys.getrecursionlimit() < needed:
        _sys.setrecursionlimit(needed)
    return _dpll(clauses)


def _assign(clauses, symbol, polarity):
    remaining = []
    for clause in clauses:
        if (symbol, polarity) in clause:
            continue  # clause satisfied
        if (symbol, not polarity) in clause:
            remaining.append(
                tuple(
                    literal for literal in clause if literal != (symbol, not polarity)
                )
            )
        else:
            remaining.append(clause)
    return remaining


def _dpll(clauses):
    while True:
        if not clauses:
            return True
        if any(not clause for clause in clauses):
            return False
        unit = next((clause[0] for clause in clauses if len(clause) == 1), None)
        if unit is not None:
            clauses = _assign(clauses, unit[0], unit[1])
            continue
        polarities = {}
        for clause in clauses:
            for symbol, polarity in clause:
                polarities.setdefault(symbol, set()).add(polarity)
        pure = next(
            (
                (symbol, next(iter(seen)))
                for symbol, seen in polarities.items()
                if len(seen) == 1
            ),
            None,
        )
        if pure is not None:
            clauses = _assign(clauses, pure[0], pure[1])
            continue
        break
    scores = {}
    for clause in clauses:
        weight = 2.0 ** -len(clause)
        for symbol, _ in clause:
            scores[symbol] = scores.get(symbol, 0.0) + weight
    branch = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return _dpll(_assign(clauses, branch, True)) or _dpll(
        _assign(clauses, branch, False)
    )


# --------------------------------------------------------------------------
# The knowledge base.
# --------------------------------------------------------------------------


class KnowledgeBase:
    """A monotonic propositional KB with TELL/ASK in lecture notation.

    """

    def __init__(self):
        self._sentences = []

    def tell(self, sentence):
        """Add ``sentence`` to the KB. Parses now; infers nothing."""
        self._sentences.append(_parse(sentence))

    def ask(self, sentence):
        """Return whether the KB entails ``sentence``.

        ``False`` means NOT PROVEN — it does not mean the sentence is false.
        """
        query = _parse(sentence)
        # Full reconversion on every call — deliberate; see the DESIGN
        # CHOICE note above the DPLL section before optimising this.
        return not _satisfiable(_clauses(self._sentences + [("~", query)]))

    def consistent(self):
        """Return whether the KB is satisfiable (debugging aid)."""
        return _satisfiable(_clauses(list(self._sentences)))

    def print_kb(self):
        """Print the KB, numbered and fully parenthesised. Returns None."""
        for index, tree in enumerate(self._sentences, 1):
            print("%3d. %s" % (index, _render(tree)))
        return None

# The Environment

def _copy_json(value):
    return _json.loads(_json.dumps(value))


_ENVIRONMENTS = {}


def register_environment(definition, _registry=_ENVIRONMENTS):
    """Register an environment definition (see the contract documented above).

    Raises if the object is missing contract members or if the name is
    already taken — a duplicate registration can only be an authoring bug
    or tampering, and overwriting a definition would change grading physics.
    (``_registry`` is bound at definition time on purpose: rebinding the
    module global later cannot redirect registrations.)
    """
    required = (
        "name",
        "required_config",
        "percept_schema",
        "action_schema",
        "handlers",
        "load_world",
        "initial_state",
        "percepts",
        "terminal",
    )
    missing = [attr for attr in required if not hasattr(definition, attr)]
    if missing:
        raise ValueError(
            "environment definition is missing contract member(s): "
            + ", ".join(missing)
        )
    if not isinstance(definition.name, str) or not definition.name:
        raise ValueError("environment definition needs a non-empty string name")
    if definition.name in _registry:
        raise ValueError(
            "an environment named %r is already registered" % definition.name
        )
    _registry[definition.name] = definition
    return definition

class Environment:
    """The world your agent acts in. Constructed from a case's input data.

    The only channel from the hidden world to your agent is the percepts
    that ``act()`` (and the initial step) produce. ``env.config`` holds the
    case's public facts; everything else must be learned by acting.
    """

    # Bound at class-definition time: rebinding the module-global
    # _ENVIRONMENTS name later cannot swap the registry grading resolves
    # definitions from.
    _registry = _ENVIRONMENTS

    def __init__(self, data):
        if not isinstance(data, dict) or "config" not in data or "world" not in data:
            raise ValueError('input data must be {"config": ..., "world": ...}')
        config = data["config"]
        if not isinstance(config, dict):
            raise ValueError("config must be an object")
        env_name = config.get("environment")
        if env_name not in self._registry:
            raise ValueError(
                "config.environment must be one of: %s"
                % ", ".join(sorted(self._registry))
            )
        definition = self._registry[env_name]
        missing = [key for key in definition.required_config if key not in config]
        if missing:
            raise ValueError(
                "config for %r is missing required key(s): %s"
                % (env_name, ", ".join(missing))
            )
        self._definition = definition
        self._config = _copy_json(config)
        self._hidden = definition.load_world(self._config, data["world"])
        self._snapshot = _json.dumps(self._hidden, sort_keys=True)
        self._state = definition.initial_state(self._config)
        self._status = None
        self._reason = None
        initial = definition.percepts(self._config, self._hidden, self._state, None)
        outcome = definition.terminal(self._config, self._hidden, self._state)
        if outcome is not None:
            self._end(outcome[0], outcome[1])
        self._steps = [{"action": None, "percept": self._stamped(initial)}]

    @property
    def config(self):
        """A copy of the case's public config dict."""
        return _copy_json(self._config)

    def get_percept(self):
        """A copy of the current percept. Pure read; records nothing."""
        return _copy_json(self._steps[-1]["percept"])

    def act(self, name, *args):
        """Perform an action; return the resulting percept dict.

        The returned percept's ``is_terminal`` turning ``True`` means the
        episode just ended — stop acting and return your answer. Any action
        taken past that point raises ``IllegalAction``.
        """
        if self._status is not None:
            raise IllegalAction(
                "the episode is over (%s: %s); no further actions are allowed"
                % (self._status, self._reason)
            )
        self._assert_static()
        action = [name] + [self._json_arg(arg) for arg in args]
        if not isinstance(name, str) or name not in self._definition.handlers:
            self._steps.append({"action": action, "percept": None})
            self._end("failure", "illegal_action")
            raise IllegalAction("unknown action %r" % (name,))
        try:
            self._definition.handlers[name](
                self._config, self._hidden, self._state, *args
            )
        except IllegalAction:
            self._steps.append({"action": action, "percept": None})
            self._end("failure", "illegal_action")
            raise
        self._assert_static()
        percept = self._definition.percepts(
            self._config, self._hidden, self._state, action
        )
        outcome = self._definition.terminal(self._config, self._hidden, self._state)
        if outcome is not None:
            self._end(outcome[0], outcome[1])
        self._steps.append({"action": action, "percept": self._stamped(percept)})
        return _copy_json(percept)

    def result(self):
        """The recorded episode: steps, terminal status, and reason."""
        return {
            "steps": _copy_json(self._steps),
            "status": self._status if self._status is not None else "done",
            "reason": self._reason if self._reason is not None else "returned",
        }

    def _end(self, status, reason):
        self._status = status
        self._reason = reason

    def _stamped(self, percept):
        """Stamp the reserved is_terminal flag onto a definition's percept."""
        if not isinstance(percept, dict):
            raise ValueError(
                "percepts(...) must return a dict, got %s"
                % type(percept).__name__
            )
        if "is_terminal" in percept:
            raise ValueError(
                "percepts(...) must not emit the reserved key 'is_terminal' "
                "(the environment adds it)"
            )
        percept["is_terminal"] = self._status is not None
        return percept

    def _assert_static(self):
        if _json.dumps(self._hidden, sort_keys=True) != self._snapshot:
            raise RuntimeError(
                "hidden world mutated mid-episode; the static-truth guard "
                "forbids this"
            )

    @staticmethod
    def _json_arg(value):
        try:
            return _json.loads(_json.dumps(value))
        except (TypeError, ValueError):
            return repr(value)

# if __name__ == "__main__":
#     kb = KnowledgeBase()
#     kb.tell("A => B")
#     kb.tell("A")
#     print(kb.ask("A"))
#     print(kb.ask("(~B) => (~A)"))
#     print(kb.ask("C"))
#     kb.print_kb()
