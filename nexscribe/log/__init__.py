import logging
from typing import Final

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install


console: Final[Console] = Console()

def _init(
    *,
    format: str = logging.BASIC_FORMAT,
    date_format: str | None = None,
    level: int | str | None = None,
    force: bool | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> None:
    logging.basicConfig(
        format=format,
        datefmt=date_format,
        level=level,
        handlers=[RichHandler(console=console, markup=True, rich_tracebacks=True, tracebacks_show_locals=True)],
        force=force,
        encoding=encoding,
        errors=errors,
    )

def set_logging_level(level: int | str) -> None: logging.getLogger().setLevel(level)


install(show_locals=True, console=console)
_init(level=logging.INFO, format='%(message)s', date_format="[%X]")
