from typing import Dict, Any, Optional, Tuple
import threading

class LiveStateStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def update(self, state: Dict[str, Any]) -> None:
        key = (str(state["race_id"]), str(state["driver"]))
        with self._lock:
            self._store[key] = dict(state)

    def get(self, race_id: str, driver: str) -> Optional[Dict[str, Any]]:
        key = (str(race_id), str(driver))
        with self._lock:
            return self._store.get(key)
