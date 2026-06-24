# MARK:Sync with backend/local/src/middleware/logger_module.py
"""Logger - local logger with [LOCAL] prefix."""
import logging, sys

from uvicorn.logging import DefaultFormatter

log = logging.getLogger("local.logger")
if not log.handlers:
    log.setLevel(logging.INFO)
    _h = logging.StreamHandler(sys.stderr)
    # Match FastAPI/Uvicorn behavior: auto-enable colors only on supported terminals.
    _h.setFormatter(DefaultFormatter("[LOCAL] %(levelprefix)s %(message)s", use_colors=None))
    log.addHandler(_h)

if __name__ == "__main__":
    log.info("Logger initialized successfully.")
    log.debug("This is a debug message (should appear).")
    log.warning("This is a warning message.")
    log.error("This is an error message.")
    log.critical("This is a critical message.")
