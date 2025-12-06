import json

import mcp.types as types
from mcp import Server

from .tools import find_trade_routes, get_market_orders, list_regions, search_types

mcp_server = Server("lenny-mcp")


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_regions",
            description="List all available regions in the EVE universe that are stored in the database.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="search_types",
            description="Search for EVE Online item types by name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the item to search for (partial match supported)",
                    }
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="get_market_orders",
            description="Get raw market orders for a specific region and item type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "region_id": {"type": "integer", "description": "ID of the region"},
                    "type_id": {"type": "integer", "description": "ID of the item type"},
                    "is_buy_order": {
                        "type": "boolean",
                        "description": "Filter by buy orders (true) or sell orders (false). If omitted, returns both.",
                    },
                },
                "required": ["region_id", "type_id"],
            },
        ),
        types.Tool(
            name="find_trade_routes",
            description="Find profitable trade routes starting from a specific system. Calculates arbitrage opportunities based on budget and range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_system_name": {
                        "type": "string",
                        "description": "Name of the starting solar system (e.g., 'Jita')",
                    },
                    "max_jumps": {
                        "type": "integer",
                        "description": "Maximum number of jumps to travel",
                    },
                    "budget": {"type": "number", "description": "Maximum ISK to spend"},
                    "limit": {
                        "type": "integer",
                        "description": "Number of top results to return (default 5)",
                    },
                },
                "required": ["start_system_name", "max_jumps", "budget"],
            },
        ),
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "list_regions":
        data = await list_regions()
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "search_types":
        if not arguments or "name" not in arguments:
            raise ValueError("Missing 'name' argument")
        data = await search_types(arguments["name"])
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "get_market_orders":
        if not arguments or "region_id" not in arguments or "type_id" not in arguments:
            raise ValueError("Missing arguments")
        data = await get_market_orders(
            arguments["region_id"], arguments["type_id"], arguments.get("is_buy_order")
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "find_trade_routes":
        if (
            not arguments
            or "start_system_name" not in arguments
            or "max_jumps" not in arguments
            or "budget" not in arguments
        ):
            raise ValueError("Missing arguments")
        data = await find_trade_routes(
            arguments["start_system_name"],
            arguments["max_jumps"],
            arguments["budget"],
            arguments.get("limit", 5),
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    raise ValueError(f"Unknown tool: {name}")
