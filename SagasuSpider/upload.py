import asyncio
import json
import os
from pathlib import Path
from typing import List

import aiofiles
import httpx

from .log import logger
from .models import (
    BangumiSubject,
    BangumiSubjectType,
    CreateSagasuEpisodes,
    CreateSagasuSeries,
    ReadSagasuEpisodes,
    ReadSagasuSeries,
)


class SagasuUpload:
    def __init__(
        self, base: str, path: Path = Path(".") / "data", parallel: int = 8
    ) -> None:
        self.client = httpx.AsyncClient(http2=True, base_url=base)
        self.path, self.parallel = path, parallel

    def subject2series(self, subject: BangumiSubject) -> CreateSagasuSeries:
        return CreateSagasuSeries(
            name=subject.name,
            name_cn=subject.name_cn,
            description=subject.summary,
            air_date=subject.air_date if subject.air_date else None,
            bangumi_id=subject.id,
        )

    def subject2episodes(
        self, subject: BangumiSubject, series: ReadSagasuSeries
    ) -> List[CreateSagasuEpisodes]:
        return [
            CreateSagasuEpisodes(
                name=episode.name,
                name_cn=episode.name_cn,
                sort=episode.sort,
                type=episode.type,
                series=series.id,
                air_date=subject.air_date if episode.air_date else None,
            )
            for episode in subject.eps
        ]

    async def upload(self, subject: BangumiSubject):
        try:
            (await self.client.get(f"/api/series/bgm/{subject.id}")).raise_for_status()
        except httpx.HTTPError:
            pass
        else:
            return
        series_result = await self.client.post(
            "/api/series", json=self.subject2series(subject).export()
        )
        series_result.raise_for_status()
        series = ReadSagasuSeries.parse_obj(series_result.json())
        bulk = [episode.export() for episode in self.subject2episodes(subject, series)]
        if not bulk:
            return
        episodes_result = await self.client.post(
            "/api/episodes/bulk",
            json={"bulk": bulk},
        )
        episodes_result.raise_for_status()
        episodes = [
            ReadSagasuEpisodes.parse_obj(episode) for episode in episodes_result.json()
        ]
        return episodes

    async def process(self, file: Path):
        logger.info(f"Processing file {file}")
        try:
            async with aiofiles.open(file, "rt") as f:  # type:ignore
                data = json.loads(await f.read())
                subject = BangumiSubject.parse_obj(data)
            if subject.type is not BangumiSubjectType.Anime:
                return
            await self.upload(subject)
        except Exception as e:
            logger.exception(f'Exception "{e}" occurred during upload file {file}:')

    async def __call__(self):
        sem = asyncio.Semaphore(self.parallel)

        for file in sorted(os.listdir(self.path)):
            path = self.path / file
            await sem.acquire()
            task = asyncio.create_task(self.process(path))
            task.add_done_callback(lambda _: sem.release())
            task.set_name(f"Upload-{file}")
