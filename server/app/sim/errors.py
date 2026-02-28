"""Simulation errors and canonical invalid action codes."""

INVALID_OUT_OF_BOUNDS = "invalid_action.out_of_bounds"
INVALID_NON_ADJACENT_MOVE = "invalid_action.non_adjacent_move"
INVALID_NO_ENERGY = "invalid_action.no_energy"
INVALID_PRECONDITION = "invalid_action.precondition_failed"
TERMINAL_WORLD = "terminal_world"


class SimulationError(Exception):
    """Base simulation error."""
