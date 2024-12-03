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


def tabulate_model(data: list[dict], keys: list[str]) -> list[list[str]]:
    result = [keys]
    for item in data:
        row = [item.get(key) for key in keys]
        result.append(row)
    return result


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
    """Check if the Kassalapp API is working."""
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
    lists = tabulate_model(
        [r.to_base_dict() for r in data],
        [
            "id",
            "title",
            "created_at",
            "updated_at",
        ],
    )
    click.echo(tabulate(lists, headers="firstrow", **TABULATE_DEFAULTS))


@cli.command("shopping-list")
@click.argument("list_id", type=int)
@click.option("--no-items", is_flag=True, help="Don't include list items")
@click.pass_context
async def shopping_list(ctx: click.Context, list_id: int, no_items: bool):
    """Get details for a specific shopping list."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.get_shopping_list(list_id, include_items=not no_items)
    data_model = data.to_base_dict()
    click.echo(
        tabulate(
            tabulate_model([data_model], ["id", "title", "created_at"]),
            headers="firstrow",
            **TABULATE_DEFAULTS,
        )
    )
    click.echo("Items")
    click.echo(
        tabulate(
            tabulate_model(data_model["items"], ["id", "checked", "text"]),
            headers="firstrow",
            **TABULATE_DEFAULTS,
        )
    )


@cli.command("shopping-list-items")
@click.argument("list_id", type=int)
@click.pass_context
async def shopping_list_items(ctx: click.Context, list_id: int):
    """Get details for a specific shopping list."""
    client: Kassalapp = ctx.obj["client"]
    data = await client.get_shopping_list_items(list_id)
    click.echo(
        tabulate(
            tabulate_model([m.to_base_dict() for m in data], ["id", "checked", "text"]),
            headers="firstrow",
            **TABULATE_DEFAULTS,
        )
    )


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
    click.echo(response.to_dict())


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
    products = tabulate_model(
        [r.to_dict() for r in results],
        [
            "id",
            "ean",
            "name",
            "image",
            "current_price",
        ],
    )
    click.echo(tabulate(products, headers="firstrow", **TABULATE_DEFAULTS))


@cli.command("store-groups")
async def store_groups():
    """Get list of available physical store groups."""
    groups = [str(g) for g in PhysicalStoreGroup]
    click.echo(tabulate([{"value": v} for v in sorted(groups)], **TABULATE_DEFAULTS))


def _parse_proximity(_ctx, _param, value: str):
    proximity = [c.strip() for c in value.split(",")]
    if len(proximity) != 3:  # noqa: PLR2004
        raise click.BadParameter("Proximity must be in the format 'lat,lng,radius'")
    return ProximitySearch(float(proximity[0]), float(proximity[1]), float(proximity[2]))


@cli.command("stores")
@click.option(
    "--proximity",
    type=str,
    help="Proximity of stores to search for (latitude,longitude,radius)",
    callback=_parse_proximity,
)
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
    client: Kassalapp = ctx.obj["client"]
    results = await client.physical_stores(search=search, group=group, proximity=proximity, size=count)

    stores = tabulate_model(
        [r.to_dict() for r in results],
        [
            "id",
            "name",
            "address",
            "website",
            "position",
        ],
    )
    click.echo(tabulate(stores, headers="firstrow", **TABULATE_DEFAULTS))


@cli.command("webhooks")
@click.pass_context
async def webhooks(ctx: click.Context):
    """Get webhooks."""
    client: Kassalapp = ctx.obj["client"]
    results = await client.get_webhooks()
    if len(results) > 0:
        click.echo(tabulate([r.to_dict() for r in results], headers="keys", **TABULATE_DEFAULTS))
    else:
        click.echo("No webhooks defined.")


def configure_logging(debug: bool):
    """Set up logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
