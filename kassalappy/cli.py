"""Kassalapp CLI."""
from __future__ import annotations

import asyncio
import logging

import aiohttp
import asyncclick as click
from tabulate import tabulate

from kassalappy import Kassalapp

TABULATE_DEFAULTS = {
    "tablefmt": "rounded_grid",
}

@click.group()
@click.password_option("--token", type=str, required=True, confirmation_prompt=False, help="API Token")
@click.option("--debug", is_flag=True, help="Set logging level to DEBUG")
@click.pass_context
async def cli(ctx: click.Context, token: str, debug: bool):
    """Kassalapp CLI."""
    session = aiohttp.ClientSession()
    client = Kassalapp(access_token=token, websession=session)

    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["client"] = client

    configure_logging(debug)


@cli.command("shopping-lists")
@click.pass_context
async def shopping_lists(ctx: click.Context):
    """Get shopping lists associated with the authenticated user."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.execute("shopping-lists")
    click.echo(tabulate(data, headers="keys", **TABULATE_DEFAULTS))
    await client.close_connection()


@cli.command("shopping-list")
@click.argument("list_id", type=int)
@click.pass_context
async def shopping_list(ctx: click.Context, list_id: int):
    """Get details for a specific shopping list."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.execute(f"shopping-lists/{list_id}")
    click.echo(tabulate([data], headers="keys", **TABULATE_DEFAULTS))
    await client.close_connection()


@cli.command("add-item")
@click.option("--list_id", type=int)
@click.argument("text", required=True)
@click.argument("product_id", type=int, required=False, default=None)
@click.pass_context
async def add_item(ctx: click.Context, list_id: int, text: str, product_id: int | None = None):
    """Add an item to shopping list."""
    client: Kassalapp = ctx.obj["client"]
    response = await client.add_shopping_list_item(list_id, text, product_id)
    click.echo(response)
    await client.close_connection()


@cli.command("product")
@click.argument("search", type=str)
@click.option("--count", type=int, default=5)
@click.pass_context
async def product_search(ctx: click.Context, search: str, count: int):
    """Search for products."""
    client: Kassalapp = ctx.obj["client"]
    results = await client.product_search(search=search, size=count, unique=True)
    click.echo(tabulate(results, headers="keys", **TABULATE_DEFAULTS))
    await client.close_connection()



def configure_logging(debug: bool):
    """Set up logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cli())


if __name__ == '__main__':
    main()
