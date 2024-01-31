"""Kassalapp CLI."""
from __future__ import annotations

import logging

import asyncclick as click
from tabulate import tabulate

from kassalappy import Kassalapp
from kassalappy.models import PhysicalStoreGroup, ProximitySearch

TABULATE_DEFAULTS = {
    "tablefmt": "rounded_grid",
}


@click.group()
@click.password_option("--token", type=str, required=True, confirmation_prompt=False, help="API Token")
@click.option("--debug", is_flag=True, help="Set logging level to DEBUG")
@click.pass_context
async def cli(ctx: click.Context, token: str, debug: bool):
    """Kassalapp CLI."""
    configure_logging(debug)
    client = Kassalapp(access_token=token)

    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["client"] = client
    await ctx.with_async_resource(client)


@cli.command("health")
@click.pass_context
async def health(ctx: click.Context):
    """Checks if the Kassalapp API is working."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.healthy()
    click.echo(data)


@cli.command("shopping-lists")
@click.option("--items", is_flag=True, help="Include shopping list items")
@click.pass_context
async def shopping_lists(ctx: click.Context, items: bool):
    """Get shopping lists associated with the authenticated user."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.get_shopping_lists(include_items=items)
    click.echo(tabulate([m.model_dump() for m in data], headers="keys", **TABULATE_DEFAULTS))


@cli.command("shopping-list")
@click.argument("list_id", type=int)
@click.option("--items", is_flag=True, help="Include shopping list items")
@click.pass_context
async def shopping_list(ctx: click.Context, list_id: int, items: bool):
    """Get details for a specific shopping list."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.get_shopping_list(list_id, include_items=items)
    data_model = data.model_dump()
    exclude_keys = ['items']
    new_d = {k: data_model[k] for k in set(list(data_model.keys())) - set(exclude_keys)}
    click.echo(tabulate([new_d], headers="keys", **TABULATE_DEFAULTS))
    click.echo("Items")
    click.echo(tabulate(data_model['items'], headers="keys", **TABULATE_DEFAULTS))


@cli.command("shopping-list-items")
@click.argument("list_id", type=int)
@click.pass_context
async def shopping_list_items(ctx: click.Context, list_id: int):
    """Get details for a specific shopping list."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.get_shopping_list_items(list_id)
    click.echo(tabulate([m.model_dump() for m in data], headers="keys", **TABULATE_DEFAULTS))


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


@cli.command("check-item")
@click.option("--list_id", type=int)
@click.argument("item_id", type=int)
@click.pass_context
async def check_item(ctx: click.Context, list_id: int, item_id: int):
    """Mark a shopping list item as checked."""
    client: Kassalapp = ctx.obj["client"]
    response = await client.update_shopping_list_item(list_id, item_id, checked=True)
    click.echo(response.model_dump())


@cli.command("delete-item")
@click.option("--list_id", type=int)
@click.argument("item_id", type=int)
@click.pass_context
async def delete_item(ctx: click.Context, list_id: int, item_id: int):
    """Delete a shopping list item."""
    client: Kassalapp = ctx.obj["client"]
    await client.delete_shopping_list_item(list_id, item_id)
    click.echo(f"Item #{item_id} successfully deleted.")


@cli.command("product")
@click.argument("search", type=str)
@click.option("--count", type=int, default=5, help="Number of results to return")
@click.pass_context
async def product_search(ctx: click.Context, search: str, count: int):
    """Search for products."""
    client: Kassalapp = ctx.obj["client"]
    results = await client.product_search(search=search, size=count, unique=True)
    click.echo(tabulate([r.model_dump() for r in results], headers="keys", **TABULATE_DEFAULTS))


@cli.command("store-groups")
async def store_groups():
    """Get list of available physical store groups."""
    groups = [g.value for g in PhysicalStoreGroup]
    groups.sort()
    click.echo(groups)


@cli.command("stores")
@click.option("--proximity",
              type=ProximitySearch,
              help="Proximity of stores to search for (latitude longitude radius)")
@click.option("--group", type=PhysicalStoreGroup)
@click.argument("search", type=str, required=False)
@click.option("--count", type=int, help="Number of results to return")
@click.pass_context
async def store_search(
    ctx: click.Context,
    proximity: ProximitySearch,
    group: PhysicalStoreGroup,
    search: str,
    count: int,
):
    """Search for physical stores."""
    proximity_search = None
    if proximity:
        lat, lng, radius = proximity
        proximity_search = ProximitySearch(lat=lat, lng=lng, km=radius)

    client: Kassalapp = ctx.obj["client"]
    results = await client.physical_stores(search=search, group=group, proximity=proximity_search, size=count)
    click.echo(tabulate([r.model_dump() for r in results], headers="keys", **TABULATE_DEFAULTS))


@cli.command("webhooks")
@click.pass_context
async def webhooks(ctx: click.Context):
    """Get webhooks."""
    client: Kassalapp = ctx.obj["client"]
    results = await client.get_webhooks()
    click.echo(tabulate([r.model_dump() for r in results], headers="keys", **TABULATE_DEFAULTS))


def configure_logging(debug: bool):
    """Set up logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
