from asyncio import AbstractEventLoop, Future, Semaphore, wait_for
from typing import Optional


class AdvanceSemaphore(Semaphore):
    _loop: AbstractEventLoop
    _finshed_future: Optional[Future]

    def __init__(self, value: int) -> None:
        super().__init__(value=value)
        self._initial_value = value
        self._finshed_future = None

    def _check_value(self) -> None:
        if (
            (self._value >= self._initial_value)
            and (not self._waiters)
            and (self._finshed_future is not None)
            and (not self._finshed_future.done())
        ):
            self._finshed_future.set_result(None)

    def release(self) -> None:
        super().release()
        self._check_value()

    async def wait_all_finish(self, timeout: float = None):
        self._finshed_future = self._loop.create_future()
        self._check_value()
        await wait_for(self._finshed_future, timeout)
