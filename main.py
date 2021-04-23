import asyncio

from SagasuSpider.core import SagasuSpider

instance = SagasuSpider()

asyncio.run(instance())
