from typing import TYPE_CHECKING

from loguru import logger as _logger
from tqdm import tqdm

if TYPE_CHECKING:
    from loguru import Logger

logger: "Logger" = _logger
logger.remove()
logger.add(
    lambda s: tqdm.write(s, end=""),
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
