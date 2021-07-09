import asyncio
from pathlib import Path

import click


@click.group()
def main():
    pass


@click.command(name="spider")
@click.option(
    "-s",
    "--start",
    default=1,
    type=int,
    help="start page of spider",
    show_default=True,
)
@click.option(
    "-e",
    "--end",
    default=-1,
    type=int,
    help="end page of spider, -1 for infinite",
    show_default=True,
)
@click.option(
    "-p",
    "--parallel",
    type=int,
    default=8,
    help="number of concurrent tasks",
    show_default=True,
)
@click.option(
    "-o",
    "--output",
    default=Path(".") / "data",
    type=Path,
    help="output directory",
    show_default=True,
)
def spider(start: int, end: int, parallel: int, output: Path):
    from SagasuSpider.spider import SagasuSpider

    instance = SagasuSpider(parallel, start, end, output)

    try:
        asyncio.run(instance())
    except KeyboardInterrupt:
        exit(1)


main.add_command(spider)

if __name__ == "__main__":
    main()
