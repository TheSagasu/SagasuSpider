import asyncio
import json
from functools import wraps
from itertools import count
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, TypeVar

import aiofiles
from httpx import AsyncClient, HTTPError

from .log import logger

AsyncCallable_T = TypeVar("AsyncCallable_T", bound=Callable[..., Coroutine])


def retry_transport(func: AsyncCallable_T) -> AsyncCallable_T:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        retried = 0
        while True:
            try:
                return await func(*args, **kwargs)
            except HTTPError as e:
                logger.warning(
                    f"Transport error occurred: <r>{e}</r>, <y>{retried=}</y>"
                )
                retried += 1

    return wrapper  # type:ignore


class SagasuSpider:
    def __init__(
        self,
        parallel: int = 16,
        begin: int = 1,
        end: int = -1,
        strore_path: Path = Path(".") / "data",
    ):
        self.parallel, self.path = parallel, strore_path
        self.begin, self.end = begin, end
        self.client = AsyncClient(http2=True, base_url="https://api.bgm.tv")

    @retry_transport
    async def subject(self, id: int) -> Dict[str, Any]:
        result = await self.client.get(
            f"/subject/{id}", params={"resposeGroup": "large"}
        )
        result.raise_for_status()
        return result.json()

    async def persist(self, id: int, data: Dict[str, Any]) -> int:
        path = self.path / f"{id}.json"
        path.parent.mkdir(exist_ok=True, parents=True)
        async with aiofiles.open(path, "wt", encoding="utf-8") as f:  # type:ignore
            total = await f.write(
                json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True)
            )
        return total

    async def spider(self, id: int, sem: asyncio.Semaphore):
        async with sem:
            try:
                result = await self.subject(id)
                total = await self.persist(id, result)
            except Exception:
                logger.exception(f"Exception occurred while requiring subject {id}")
            else:
                logger.debug(f"Subject <g>{id}</g> saved successfully. {total=}")

    async def __call__(self):
        sem = asyncio.Semaphore(self.parallel)

        def pagination():
            for begin in count(self.begin, self.parallel * 2):
                if (begin >= self.end) and (self.end >= 0):
                    break

                yield [*range(begin, begin + self.parallel * 2)]
            return

        for page in pagination():
            logger.info(f"Next pages: <e>{', '.join(map(str, page))}</e>")
            if not page:
                break
            await asyncio.gather(
                *map(lambda id: self.spider(id, sem), page), return_exceptions=True
            )
