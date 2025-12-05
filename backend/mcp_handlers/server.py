from mcp.server import Server
import mcp.types as types
from .tools import list_regions, search_types, get_market_orders, find_trade_routes, get_top_orders, call_esi, run_sql_query, inspect_database_schema, get_route
import json

mcp_server = Server("lenny-mcp")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="inspect_database_schema",
            description="Inspect the database schema to see available tables and columns.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
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
                    "name": {"type": "string", "description": "Name of the item to search for (partial match supported)"},
                    "limit": {"type": "integer", "description": "Number of results to return (default 250)"}
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
                    "is_buy_order": {"type": "boolean", "description": "Filter by buy orders (true) or sell orders (false). If omitted, returns both."}
                },
                "required": ["region_id", "type_id"],
            },
        ),
        types.Tool(
            name="get_top_orders",
            description="Get top market orders by price for a specific region. Useful for finding most expensive items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "region_id": {"type": "integer", "description": "ID of the region"},
                    "limit": {"type": "integer", "description": "Number of results to return (default 10)"},
                    "is_buy_order": {"type": "boolean", "description": "Filter by buy orders (true) or sell orders (false). If omitted, returns both."}
                },
                "required": ["region_id"],
            },
        ),
        types.Tool(
            name="find_trade_routes",
            description="Find profitable trade routes starting from a specific system. Calculates arbitrage opportunities based on budget and range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_system_name": {"type": "string", "description": "Name of the starting solar system (e.g., 'Jita')"},
                    "max_jumps": {"type": "integer", "description": "Maximum number of jumps to travel"},
                    "budget": {"type": "number", "description": "Maximum ISK to spend"},
                    "limit": {"type": "integer", "description": "Number of top results to return (default 5)"}
                },
                "required": ["start_system_name", "max_jumps", "budget"],
            },
        ),
        types.Tool(
            name="get_route",
            description="Get the route between two solar systems using ESI. Returns the list of systems to jump through.",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin_name": {"type": "string", "description": "Name of the origin solar system (e.g., 'Jita')"},
                    "destination_name": {"type": "string", "description": "Name of the destination solar system (e.g., 'Amarr')"},
                    "preference": {"type": "string", "description": "Route preference: 'shortest', 'secure', 'insecure'. Default is 'shortest'.", "enum": ["shortest", "secure", "insecure"]}
                        ,"security": {"oneOf": [{"type": "string", "enum": ["null", "low", "high"]}, {"type": "number", "minimum": 0.0, "maximum": 1.0}], "description": "Optional security filter: 'null' (0.0), 'low' (>0.0 & <0.5), 'high' (>=0.5) or numeric threshold"}
                },
                "required": ["origin_name", "destination_name"],
            },
        ),
        types.Tool(
            name="call_esi",
            description="Generic tool to call any EVE Swagger Interface (ESI) endpoint. Use this when other tools don't cover the specific data you need.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string", "description": "The ESI operation ID (e.g., 'get_markets_region_id_orders', 'get_universe_systems_system_id')"},
                    "params": {"type": "object", "description": "Dictionary of parameters for the operation (path and query parameters)"}
                },
                "required": ["operation_id"],
            },
        ),
        types.Tool(
            name="run_sql_query",
            description="Execute a raw SQL query against the database. Use this for complex queries not covered by other tools. Tables: users, sde_types, sde_regions, sde_solar_systems, sde_solar_system_jumps, sde_stations, market_orders.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The SQL query to execute"}
                },
                "required": ["query"],
            },
        ),
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "inspect_database_schema":
        data = inspect_database_schema()
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "list_regions":
        data = await list_regions()
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
    
    elif name == "search_types":
        if not arguments or "name" not in arguments:
            raise ValueError("Missing 'name' argument")
        limit = int(arguments.get("limit", 250))
        data = await search_types(arguments["name"], limit)
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
        
    elif name == "get_market_orders":
        if not arguments or "region_id" not in arguments or "type_id" not in arguments:
            raise ValueError("Missing arguments")
        data = await get_market_orders(
            arguments["region_id"], 
            arguments["type_id"], 
            arguments.get("is_buy_order")
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
    
    elif name == "get_top_orders":
        if not arguments or "region_id" not in arguments:
            raise ValueError("Missing 'region_id' argument")
        
        # Cast arguments to correct types
        region_id = int(arguments["region_id"])
        limit = int(arguments.get("limit", 10))
        is_buy_order = arguments.get("is_buy_order")
        if is_buy_order is not None:
             # Handle string 'true'/'false' if passed as string
            if isinstance(is_buy_order, str):
                is_buy_order = is_buy_order.lower() == 'true'
            else:
                is_buy_order = bool(is_buy_order)

        data = await get_top_orders(
            region_id,
            limit,
            is_buy_order
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
    
    elif name == "find_trade_routes":
        if not arguments or "start_system_name" not in arguments or "max_jumps" not in arguments or "budget" not in arguments:
            raise ValueError("Missing arguments")
        data = await find_trade_routes(
            arguments["start_system_name"],
            arguments["max_jumps"],
            arguments["budget"],
            arguments.get("limit", 5)
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "get_route":
        if not arguments or "origin_name" not in arguments or "destination_name" not in arguments:
            raise ValueError("Missing arguments")
        data = await get_route(
            arguments["origin_name"],
            arguments["destination_name"],
            arguments.get("preference", "shortest"),
            arguments.get("security")
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "call_esi":
        if not arguments or "operation_id" not in arguments:
            raise ValueError("Missing 'operation_id' argument")
        data = await call_esi(
            arguments["operation_id"],
            arguments.get("params", {})
        )
        return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

    elif name == "run_sql_query":
        if not arguments or "query" not in arguments:
            raise ValueError("Missing 'query' argument")
        data = await run_sql_query(arguments["query"])
        # Handle datetime serialization if necessary, but run_sql_query returns dicts which json.dumps handles mostly fine
        # except for datetime objects. Let's use a custom encoder or stringify in tools.py?
        # tools.py returns [dict(row)]. SQLAlchemy rows might contain datetimes.
        # Let's use the default=str in json.dumps to be safe.
        return [types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]
    
    raise ValueError(f"Unknown tool: {name}")
