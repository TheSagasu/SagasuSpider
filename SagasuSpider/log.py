import sys
from typing import TYPE_CHECKING

from loguru import logger as _logger

if TYPE_CHECKING:
    from loguru import Logger

logger: "Logger" = _logger
logger.remove()
logger.add(
    sys.stdout,
    format=(
        "<level>"
        "<v>{level:^8}</v>"
        "[{time:YYYY/MM/DD} {time:HH:mm:ss.SSS} <d>{module}:{name}</d>]</level>"
        " {message} "
    ),
    level="INFO",
    colorize=True,
)
logger = logger.opt(colors=True)
