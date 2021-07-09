import re
from datetime import date
from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel, validator
from pydantic.fields import Field
from pydantic.main import Extra


class BangumiDate(date):
    regex = re.compile(r"(\d+)\D+(\d+)\D+(\d+)\D*")

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        elif isinstance(value, str):
            try:
                return cls.fromisoformat(value)
            except Exception:
                pass
            year, month, day = map(
                int, cls.regex.match(value).groups()  # type:ignore
            )
            try:
                return cls(year, month, day)
            except Exception:
                return None
        else:
            raise TypeError("Expected str or date")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate


class DataModel(BaseModel):
    class Config:
        extra = Extra.allow


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


class BangumiEpisode(DataModel):
    id: int
    type: BangumiEpisodeType
    name: Optional[str] = None
    name_cn: Optional[str] = None
    sort: float
    air_date: Optional[BangumiDate] = Field(alias="airdate")

    @validator("name", "name_cn")
    def validate_string(cls, value):
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped if stripped else None


class BangumiSubject(DataModel):
    id: int
    type: BangumiSubjectType
    name: str
    name_cn: Optional[str] = None
    summary: Optional[str] = None
    air_date: Optional[BangumiDate] = None
    eps: List[BangumiEpisode] = []

    @validator("name_cn", "summary")
    def validate_string(cls, value):
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @validator("eps", pre=True)
    def validate_eps(cls, value):
        return value if isinstance(value, list) else []
