"""Game modules.

Every module in here is a pure state machine conforming to the contract in
`../view.py`. No I/O, no module-level mutable state, standard library only.

Do not import anything from this package at module level — `engine.py`
imports each game lazily from the registry in `../games.json`.
"""
