import logging
from typing import Callable

try:
    import winsound
except ImportError:
    winsound = None

log = logging.getLogger(__name__)

BEEP_HZ = 1000
BEEP_MS = 500
BEEP_REPEATS = 3


def notify_success(message: str, beep: Callable[[int, int], None] | None = None) -> None:
    log.info(message)
    beep = beep or (winsound.Beep if winsound else None)
    if beep is None:
        return
    try:
        for _ in range(BEEP_REPEATS):
            beep(BEEP_HZ, BEEP_MS)
    except Exception as exc:
        log.warning("Não foi possível tocar o som: %s", exc)
