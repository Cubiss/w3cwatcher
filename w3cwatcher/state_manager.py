from __future__ import annotations
from datetime import datetime, timedelta
from .logging import Logger
from typing import Callable


STATE_WAITING = 'waiting'
STATE_IN_QUEUE = 'in-queue'
STATE_IN_GAME = 'in-game'
STATE_DISABLED = 'disabled'

StateChangeListener = Callable[[str, timedelta],None]

class StateManager:
    def __init__(self,logger: Logger):
        self.state_change_listeners = []
        self.current_state = STATE_DISABLED
        self.last_state_change = datetime.now()
        self.logger = logger

    def add_state_change_listener(self, listener: StateChangeListener):
        self.state_change_listeners.append(listener)

    def update_state(self, new_state):
        if self.current_state == new_state:
            self.logger.debug(f"Ignoring state update: current=new ({new_state})")
            return
        after = datetime.now() - self.last_state_change
        self.logger.debug(f"Updating status to {new_state} after {after}")
        self.current_state = new_state
        self.last_state_change = datetime.now()

        self.logger.debug(f"Invoking {len(self.state_change_listeners)} state change listeners.")
        for l in self.state_change_listeners:
            l(new_state, after)
