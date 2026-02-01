import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_NAME = __name__

def setup_logger(
    name: str = DEFAULT_LOG_NAME,
    log_file: str | Path | None = None,
    enable_console: bool = True, 
    level: int | None =logging.INFO,
    formatter: logging.Formatter | None = None, 
    propagate: bool = False 
) -> logging.Logger:

    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    logger.propagate = propagate

    if logger.handlers:
        return logger

    if formatter is None:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    if enable_console:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    if log_file:
        Path(log_file).parent.mkdir(exist_ok=True, parents=True)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=1 * 1024 * 1024,  # 1MB
            backupCount=5,
            encoding="utf-8"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger