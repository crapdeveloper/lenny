from collections import deque

from sqlalchemy import Float, and_, cast, desc, func, inspect, select, text

from backend.database import AsyncSessionLocal, sync_engine
from backend.esi_client import (
    auth_header_for_user,
    ensure_valid_token,
    esi_app,
    esi_client,
)
from backend.models import (
    MarketOrder,
    SdeRegion,
    SdeSolarSystem,
    SdeSolarSystemJump,
    SdeStation,
    SdeType,
    User,
)

SCHEMA_DESCRIPTIONS = {
    "sde_types": {
        "description": "Static Data Export (SDE) table containing all item types in EVE Online.",
        "columns": {
            "type_id": "Unique identifier for the type.",
            "name": "Name of the type.",
            "group_id": "ID of the group this type belongs to.",
            "volume": "Volume of the item in m3.",
            "mass": "Mass of the item in kg.",
            "capacity": "Capacity of the item in m3 (if applicable, e.g., ships, containers).",
            "description": "Description of the type.",
            "market_group_id": "ID of the market group this type belongs to (if published on market).",
        },
    },
    "sde_market_groups": {
        "description": "Static Data Export (SDE) table containing market groups (categories) for items.",
        "columns": {
            "market_group_id": "Unique identifier for the market group.",
            "parent_group_id": "ID of the parent market group (for hierarchy).",
            "name": "Name of the market group.",
            "description": "Description of the market group.",
            "has_types": "Boolean indicating if this group directly contains types.",
        },
    },
    "sde_regions": {
        "description": "Static Data Export (SDE) table containing all regions in the EVE universe.",
        "columns": {
            "region_id": "Unique identifier for the region.",
            "name": "Name of the region.",
        },
    },
    "sde_solar_systems": {
        "description": "Static Data Export (SDE) table containing all solar systems.",
        "columns": {
            "system_id": "Unique identifier for the solar system.",
            "region_id": "ID of the region this system belongs to.",
            "name": "Name of the solar system.",
            "security": "Security status of the solar system (0.0 to 1.0).",
        },
    },
    "sde_solar_system_jumps": {
        "description": "Static Data Export (SDE) table defining connections (stargates) between solar systems.",
        "columns": {
            "from_solar_system_id": "ID of the origin solar system.",
            "to_solar_system_id": "ID of the destination solar system.",
        },
    },
    "sde_stations": {
        "description": "Static Data Export (SDE) table containing NPC stations.",
        "columns": {
            "station_id": "Unique identifier for the station.",
            "solar_system_id": "ID of the solar system where the station is located.",
            "name": "Name of the station.",
        },
    },
    "market_orders": {
        "description": "Live market orders fetched from ESI.",
        "columns": {
            "order_id": "Unique identifier for the market order.",
            "type_id": "ID of the item type being traded.",
            "region_id": "ID of the region where the order is located.",
            "price": "Price of the item.",
            "volume_remain": "Number of items remaining in the order.",
            "is_buy_order": "1 if it is a buy order, 0 if it is a sell order.",
            "issued": "Date and time when the order was issued.",
            "duration": "Duration of the order in days.",
            "min_volume": "Minimum volume required for the order (usually 1).",
            "range": "Range of the order (e.g., 'region', 'station', 'solarsystem').",
            "location_id": "ID of the location (station or structure) where the order is.",
            "updated_at": "Timestamp when this record was last updated in the local database.",
        },
    },
    "market_history": {
        "description": "Historical market data (daily statistics) for items in regions.",
        "columns": {
            "id": "Primary key.",
            "region_id": "ID of the region.",
            "type_id": "ID of the item type.",
            "date": "Date of the history record.",
            "average": "Average price for the day.",
            "highest": "Highest price for the day.",
            "lowest": "Lowest price for the day.",
            "order_count": "Number of orders executed that day.",
            "volume": "Total volume traded that day.",
        },
    },
}


def inspect_database_schema():
    """
    Inspects the database schema and returns a list of tables and their columns,
    enriched with descriptions where available.
    """
    inspector = inspect(sync_engine)
    schema_info = {}

    for table_name in inspector.get_table_names():
        columns = []
        table_desc = SCHEMA_DESCRIPTIONS.get(table_name, {})

        for column in inspector.get_columns(table_name):
            col_name = column["name"]
            col_desc = table_desc.get("columns", {}).get(col_name, "")

            columns.append(
                {
                    "name": col_name,
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                    "primary_key": column.get("primary_key", False),
                    "description": col_desc,
                }
            )

        schema_info[table_name] = {
            "description": table_desc.get("description", ""),
            "columns": columns,
        }

    return schema_info


async def run_sql_query(query: str):
    """Execute a raw SQL query."""
    cleaned_query = query.strip().upper()
    if not (cleaned_query.startswith("SELECT") or cleaned_query.startswith("WITH")):
        return {"error": "Only SELECT queries (including CTEs) are allowed."}

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(query))
            # If it's a SELECT query, return rows
            if result.returns_rows:
                rows = result.mappings().all()
                # Convert to list of dicts and handle non-serializable types if necessary
                return [dict(row) for row in rows]
            else:
                await session.commit()
                return {"status": "success", "rowcount": result.rowcount}
        except Exception as e:
            return {"error": str(e)}


async def list_regions():
    """List all available regions in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SdeRegion))
        regions = result.scalars().all()
        return [{"region_id": r.region_id, "name": r.name} for r in regions]


async def search_types(name: str, limit: int = 250):
    """Search for item types by name."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SdeType).where(SdeType.name.ilike(f"%{name}%")).limit(limit)
        )
        types = result.scalars().all()
        return [{"type_id": t.type_id, "name": t.name, "group_id": t.group_id} for t in types]


async def get_market_orders(region_id: int, type_id: int, is_buy_order: bool = None):
    """Get market orders for a specific region and type."""
    async with AsyncSessionLocal() as session:
        query = select(MarketOrder).where(
            MarketOrder.region_id == region_id, MarketOrder.type_id == type_id
        )
        if is_buy_order is not None:
            query = query.where(MarketOrder.is_buy_order == (1 if is_buy_order else 0))

        result = await session.execute(query)
        orders = result.scalars().all()
        return [
            {
                "order_id": o.order_id,
                "price": o.price,
                "volume_remain": o.volume_remain,
                "is_buy_order": bool(o.is_buy_order),
                "location_id": o.location_id,
                "issued": o.issued.isoformat() if o.issued else None,
            }
            for o in orders
        ]


async def get_top_orders(region_id: int, limit: int = 10, is_buy_order: bool = None):
    """Get top market orders by price for a specific region."""
    async with AsyncSessionLocal() as session:
        query = (
            select(MarketOrder, SdeType.name)
            .join(SdeType, MarketOrder.type_id == SdeType.type_id)
            .where(MarketOrder.region_id == region_id)
        )

        if is_buy_order is not None:
            query = query.where(MarketOrder.is_buy_order == (1 if is_buy_order else 0))

        # Sort by price descending (cast to Float because price is Text)
        query = query.order_by(desc(cast(MarketOrder.price, Float))).limit(limit)

        result = await session.execute(query)
        rows = result.all()

        return [
            {
                "order_id": o.order_id,
                "type_name": type_name,
                "price": float(o.price) if o.price else 0.0,
                "volume_remain": o.volume_remain,
                "is_buy_order": bool(o.is_buy_order),
                "location_id": o.location_id,
                "issued": o.issued.isoformat() if o.issued else None,
            }
            for o, type_name in rows
        ]


async def find_trade_routes(start_system_name: str, max_jumps: int, budget: float, limit: int = 5):
    """
    Find profitable trade routes starting from a given system.
    """
    async with AsyncSessionLocal() as session:
        # 1. Resolve Start System
        result = await session.execute(
            select(SdeSolarSystem).where(SdeSolarSystem.name == start_system_name)
        )
        start_system = result.scalars().first()
        if not start_system:
            return {"error": f"System '{start_system_name}' not found."}

        start_system_id = start_system.system_id

        # 2. Find Neighbors (BFS)
        # This is a simplified in-memory BFS. For production, use a graph DB or recursive CTE.
        # We need to fetch all jumps first or do iterative queries. Iterative is slower but safer for memory.
        # Let's fetch all jumps once (it's not that big, ~10k rows)
        jumps_result = await session.execute(
            select(SdeSolarSystemJump.from_solar_system_id, SdeSolarSystemJump.to_solar_system_id)
        )
        all_jumps = jumps_result.all()

        adj = {}
        for from_sys, to_sys in all_jumps:
            if from_sys not in adj:
                adj[from_sys] = []
            adj[from_sys].append(to_sys)

        # BFS
        visited = {start_system_id: 0}
        queue = deque([start_system_id])
        valid_systems = {start_system_id}

        while queue:
            current = queue.pop(0)
            dist = visited[current]
            if dist >= max_jumps:
                continue

            if current in adj:
                for neighbor in adj[current]:
                    if neighbor not in visited:
                        visited[neighbor] = dist + 1
                        valid_systems.add(neighbor)
                        queue.append(neighbor)

        valid_system_ids = list(valid_systems)

        # 3. Find Arbitrage
        # Buy from Sell Orders in Start System (or nearby? Prompt says "I am in Jita", implies buying there)
        # Sell to Buy Orders in Destination Systems (within range)

        # We need to map MarketOrder.location_id to System ID.
        # Join MarketOrder -> SdeStation -> SdeSolarSystem
        # Note: This ignores player structures for now as they aren't in SDE.

        # Query: Find Sell Orders (is_buy_order=0) in Start System (Jita)
        # We assume the user buys from the cheapest sell order in the current system.

        # Step 3a: Get Sell Orders in Start System
        sell_orders_query = (
            select(MarketOrder.type_id, MarketOrder.price, MarketOrder.volume_remain)
            .join(SdeStation, MarketOrder.location_id == SdeStation.station_id)
            .where(
                SdeStation.solar_system_id == start_system_id,
                MarketOrder.is_buy_order == 0,  # Selling to us
            )
        )

        sell_orders_res = await session.execute(sell_orders_query)
        sell_orders = sell_orders_res.all()

        # Group by Type to find min price
        best_sell_prices = {}  # type_id -> {price, volume}
        for type_id, price_str, vol in sell_orders:
            price = float(price_str)
            if type_id not in best_sell_prices or price < best_sell_prices[type_id]["price"]:
                best_sell_prices[type_id] = {"price": price, "volume": vol}

        if not best_sell_prices:
            return {"error": "No sell orders found in start system."}

        # Step 3b: Get Buy Orders in Range Systems
        buy_orders_query = (
            select(
                MarketOrder.type_id,
                MarketOrder.price,
                MarketOrder.volume_remain,
                SdeStation.solar_system_id,
                SdeStation.name,
            )
            .join(SdeStation, MarketOrder.location_id == SdeStation.station_id)
            .where(
                SdeStation.solar_system_id.in_(valid_system_ids),
                MarketOrder.is_buy_order == 1,  # Buying from us
            )
        )

        buy_orders_res = await session.execute(buy_orders_query)
        buy_orders = buy_orders_res.all()

        # Step 3c: Get all relevant type names in one query to avoid N+1 problem
        all_type_ids = list(best_sell_prices.keys())
        type_names_res = await session.execute(
            select(SdeType.type_id, SdeType.name).where(SdeType.type_id.in_(all_type_ids))
        )
        type_name_map = {type_id: name for type_id, name in type_names_res}

        opportunities = []

        for type_id, price_str, vol, sys_id, station_name in buy_orders:
            if type_id not in best_sell_prices:
                continue

            buy_price = float(price_str)
            sell_info = best_sell_prices[type_id]
            sell_price = sell_info["price"]

            if buy_price <= sell_price:
                continue

            # Calculate Profit
            margin = buy_price - sell_price
            tradeable_vol = min(vol, sell_info["volume"])

            # Check Budget
            total_cost = sell_price * tradeable_vol
            if total_cost > budget:
                # Adjust volume to budget
                tradeable_vol = int(budget / sell_price)
                total_cost = sell_price * tradeable_vol

            if tradeable_vol <= 0:
                continue

            total_profit = margin * tradeable_vol

            opportunities.append(
                {
                    "item": type_name_map.get(type_id, "Unknown Item"),
                    "buy_from": start_system_name,
                    "sell_to": station_name,
                    "buy_price": sell_price,
                    "sell_price": buy_price,
                    "quantity": tradeable_vol,
                    "total_cost": total_cost,
                    "total_profit": total_profit,
                    "jumps": visited[sys_id],
                }
            )

        # Sort by profit
        opportunities.sort(key=lambda x: x["total_profit"], reverse=True)

        return opportunities[:limit]


async def call_esi(operation_id: str, params: dict = None):
    """
    Call a generic ESI endpoint using the operation ID.
    """
    if params is None:
        params = {}

    if operation_id not in esi_app.op:
        return {"error": f"Operation '{operation_id}' not found in ESI swagger spec."}

    try:
        # Create the operation
        # Note: esipy/bravado validates parameters here
        operation = esi_app.op[operation_id](**params)
        # Prepare headers
        headers = {}

        # If caller provided a 'character_id' param, try to load the user and ensure tokens are valid
        char_id = None
        if params and "character_id" in params:
            char_id = params.get("character_id")

        if char_id:
            # Create an async DB session to refresh tokens if needed
            async with AsyncSessionLocal() as session:
                try:
                    result = await session.execute(
                        select(User).filter(User.character_id == int(char_id))
                    )
                    user = result.scalars().first()
                except Exception:
                    user = None

                if user:
                    # Ensure token is valid and persisted
                    await ensure_valid_token(user, session)
                    headers.update(auth_header_for_user(user))

        # Execute the request (synchronous)
        # In a high-concurrency app, run this in a thread pool
        response = esi_client.request(operation, headers=headers)

        # If unauthorized and we used a user header, try once more after refreshing tokens
        if response.status in (401, 403) and char_id:
            # Try to refresh tokens and retry once
            async with AsyncSessionLocal() as session:
                try:
                    result = await session.execute(
                        select(User).filter(User.character_id == int(char_id))
                    )
                    user = result.scalars().first()
                except Exception:
                    user = None

                if user:
                    await ensure_valid_token(user, session)
                    headers.update(auth_header_for_user(user))
                    # Retry the request
                    response = esi_client.request(operation, headers=headers)

        if 200 <= response.status < 300:
            data = response.data

            # Helper to convert Bravado models to dicts
            def serialize(obj):
                if hasattr(obj, "to_dict"):
                    # to_dict() might return datetime objects, which json.dumps can't handle by default
                    # We'll let the caller (server.py) handle JSON serialization with a custom encoder if needed
                    # or convert datetimes here.
                    d = obj.to_dict()
                    for k, v in d.items():
                        if hasattr(v, "isoformat"):
                            d[k] = v.isoformat()
                    return d
                return obj

            if isinstance(data, list):
                return [serialize(x) for x in data]
            else:
                return serialize(data)
        else:
            return {"error": f"ESI status {response.status}", "content": str(response.data)}

    except Exception as e:
        return {"error": f"ESI Request failed: {str(e)}"}


async def get_route(
    origin_name: str, destination_name: str, preference: str = "shortest", security: object = None
):
    """
    Get the route between two systems using ESI.
    """
    async with AsyncSessionLocal() as session:
        # Resolve Origin
        res_origin = await session.execute(
            select(SdeSolarSystem).where(SdeSolarSystem.name == origin_name)
        )
        origin_sys = res_origin.scalars().first()
        if not origin_sys:
            return {"error": f"Origin system '{origin_name}' not found."}

        # Resolve Destination
        res_dest = await session.execute(
            select(SdeSolarSystem).where(SdeSolarSystem.name == destination_name)
        )
        dest_sys = res_dest.scalars().first()
        if not dest_sys:
            return {"error": f"Destination system '{destination_name}' not found."}

        origin_id = origin_sys.system_id
        destination_id = dest_sys.system_id

    # Call ESI
    params = {"origin": origin_id, "destination": destination_id, "flag": preference}

    route_ids = await call_esi("get_route_origin_destination", params)

    if isinstance(route_ids, dict) and "error" in route_ids:
        return route_ids

    if not route_ids:
        return {
            "origin": origin_name,
            "destination": destination_name,
            "jumps": 0,
            "route": [],
            "route_security": [],
            "route_ok": True,
        }
    # Fetch system names and security values from local SDE
    async with AsyncSessionLocal() as session:
        stmt = select(SdeSolarSystem.system_id, SdeSolarSystem.name, SdeSolarSystem.security).where(
            SdeSolarSystem.system_id.in_(route_ids)
        )
        result = await session.execute(stmt)
        rows = result.all()

        # Map by id for quick lookup
        system_map = {row.system_id: {"name": row.name, "security": row.security} for row in rows}

        route_names = []
        route_security = []
        route_ok = True

        # Helper to classify security into 'null'|'low'|'high' per requested rules
        def classify(sec):
            if sec is None:
                return "unknown"
            try:
                s = float(sec)
            except Exception:
                return "unknown"
            if s == 0.0:
                return "null"
            if 0.0 < s < 0.5:
                return "low"
            # Option A: treat 0.5 as high
            if s >= 0.5:
                return "high"
            return "unknown"

        # Normalize and validate requested security parameter
        security_mode = None
        security_threshold = None
        if security is not None:
            # Accept strings 'null','low','high' or numeric thresholds
            if isinstance(security, str):
                sec_lower = security.lower()
                if sec_lower not in ("null", "low", "high"):
                    return {
                        "error": "Invalid security parameter. Allowed strings: 'null','low','high' or numeric 0.0-1.0"
                    }
                security_mode = sec_lower
            else:
                try:
                    security_threshold = float(security)
                    if not (0.0 <= security_threshold <= 1.0):
                        return {"error": "Numeric security threshold must be between 0.0 and 1.0"}
                    security_mode = "threshold"
                except Exception:
                    return {
                        "error": "Invalid security parameter. Allowed strings: 'null','low','high' or numeric 0.0-1.0"
                    }

        for sys_id in route_ids:
            info = system_map.get(sys_id)
            if info:
                name = info.get("name")
                sec = info.get("security")
            else:
                name = str(sys_id)
                sec = None

            cls = classify(sec)
            route_names.append(name)
            route_security.append(
                {
                    "system_id": sys_id,
                    "name": name,
                    "security": (float(sec) if sec is not None else None),
                    "class": cls,
                }
            )

            # Evaluate filter if requested
            if security_mode is not None:
                if cls == "unknown":
                    route_ok = False
                elif security_mode == "threshold":
                    if sec is None or float(sec) < security_threshold:
                        route_ok = False
                else:
                    # string modes
                    if cls != security_mode:
                        route_ok = False

        return {
            "origin": origin_name,
            "destination": destination_name,
            "jumps": len(route_ids),
            "route": route_names,
            "route_security": route_security,
            "route_ok": route_ok,
        }
