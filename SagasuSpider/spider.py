import asyncio
from functools import wraps
from itertools import count
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, TypeVar

from httpx import AsyncClient, HTTPError, HTTPStatusError, Response, TransportError
from pydantic import ValidationError
from tqdm import tqdm

from .log import logger
from .models import BangumiSubject
from .utils import AdvanceSemaphore

AsyncCallable_T = TypeVar("AsyncCallable_T", bound=Callable[..., Coroutine])


def retry_transport(func: AsyncCallable_T) -> AsyncCallable_T:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        retried = 0
        while True:
            try:
                return await func(*args, **kwargs)
            except TransportError as e:
                logger.warning(
                    f"Transport error occurred: <r>{e}</r>, <y>{retried=}</y>"
                )
            except HTTPStatusError as e:
                response: Response = e.response
                logger.warning(
                    f"Invalid HTTP Status: <r><b>{response.status_code}</b> "
                    f"{response.reason_phrase}</r> for url <e>{response.url}</e>, "
                    f"<y>{retried=}</y>"
                )
            except HTTPError as e:
                logger.exception(f"Unknown HTTP error occurred for {e.request=}:")

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
        result = await self.client.get(f"/subject/{id}?responseGroup=large")
        result.raise_for_status()
        return result.json()

    async def persist(self, id: int, data: BangumiSubject) -> int:
        path = self.path / f"{id}.json"
        if path.is_file():
            logger.warning(
                f"Subject <g>{id=}</g> <e>{data.name_cn or data.name!r}</e> already "
                f"exists at <y>{path}</y>. Skip."
            )
            return 0
        path.parent.mkdir(exist_ok=True, parents=True)
        total = path.write_text(
            data=data.json(ensure_ascii=False, indent=4), encoding="utf-8"
        )
        return total

    async def spider(self, id: int):
        logger.debug(f"Bangumi {id=} task started.")
        try:
            result = await self.subject(id)
            deserialized = BangumiSubject.parse_obj(result)
            total = await self.persist(id, deserialized)
        except Exception as e:
            if isinstance(e, ValidationError):
                err_msg = ", ".join(
                    map(
                        lambda e: "(<b>"
                        + " ".join(
                            map(
                                lambda k, v: f"<e>{k}</e>=<y>{v!r}</y>",
                                e.keys(),
                                e.values(),
                            )
                        )
                        + "</b>)",
                        e.errors(),
                    )
                )
                logger.warning(
                    f"Failed to deserialize subject <r><b>{id=}</b></r>: {err_msg}"
                )
            else:
                logger.exception(f"Exception occurred while requiring subject {id=}")
            return
        if total <= 0:
            return
        logger.info(
            f"<b>Subject "
            f"<g>{id=}</g> <e>{deserialized.name_cn or deserialized.name!r}</e></b> "
            f"saved successfully. total=<y>{total}</y>bytes"
        )

    async def __call__(self):
        sem = AdvanceSemaphore(self.parallel)
        progress = tqdm(
            total=(self.end - self.begin) if self.end > 0 else None, colour="YELLOW"
        )

        def pagination():
            with progress:
                for current in count(self.begin):
                    if self.end > 0 and current >= self.end:
                        break
                    progress.update()
                    yield current
            return

        for page in pagination():
            await sem.acquire()
            task = asyncio.create_task(self.spider(page))
            task.add_done_callback(lambda _: sem.release())
            progress.set_description(f"Page {page}")

        await sem.wait_all_finish()
