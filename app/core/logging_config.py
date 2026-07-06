"""Central logging setup for Argus.

Modules do `log = get_logger(__name__)` and call `log.warning(...)` etc. instead
of bare `print()`, so handled-but-noteworthy errors are visible in real
deployments (Docker/systemd) instead of vanishing to stdout. `configure_logging()`
is called once at process start (server.main, eval runner); level is controlled by
`ARGUS_LOG_LEVEL` (default INFO).
"""
import logging
import os

_configured = False


def configure_logging() -> None:
    """Install a root handler once. Idempotent; safe to call from any entrypoint."""
    global _configured
    if _configured:
        return
    level = os.environ.get("ARGUS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _configured = True


def get_logger(name: str = "argus") -> logging.Logger:
    """Logger under the `argus` namespace (or the module name passed in)."""
    return logging.getLogger(name)
