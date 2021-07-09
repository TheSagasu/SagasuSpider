from typing import List
from pydantic import BaseModel
from enum import IntEnum
from datetime import date

from pydantic.fields import Field


class BangumiSubjectType(IntEnum):
    Book = 1
    Anime = 2
    Music = 3
    Game = 4
    Real = 6


class BangumiEpisodeType(IntEnum):
    Main = 0
    Special = 1
    Opening = 2
    Ending = 3
    Advertising = 4
    MAD = 5
    Other = 6


class BangumiEpisode(BaseModel):
    id: int
    type: BangumiEpisodeType
    name: str
    name_cn: str
    sort: float
    air_date: date = Field(alias="airdate")


class BangumiSubject(BaseModel):
    id: int
    type: BangumiSubjectType
    name: str
    name_cn: str
    summary: str
    air_date: date
    eps: List[BangumiEpisode] = []
