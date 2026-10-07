import logging
import sys
from .config import settings


def setup_logging() -> logging.Logger:
    """Configures application-wide structured logging."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    app_logger = logging.getLogger("authentica")
    app_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return app_logger


logger = setup_logging()
