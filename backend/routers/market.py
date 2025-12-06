from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi_pagination import Page, Params
from fastapi_pagination.customization import CustomizedPage, UseParams
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import delete, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.esi_client import esi_app, esi_client
from backend.models import (
    MarketHistory,
)
from backend.models import MarketOrder as MarketOrderModel
from backend.models import (
    SdeMarketGroup,
    SdeRegion,
    SdeSolarSystem,
    SdeStation,
    SdeType,
)
from backend.worker import fetch_market_orders

router = APIRouter(prefix="/api/market", tags=["market"])


class MarketOrder(BaseModel):
    order_id: int
    type_id: int
    type_name: str
    region_id: int
    region_name: Optional[str]
    location_id: int
    station_name: Optional[str]
    price: float
    volume_remain: int
    is_buy_order: bool
    issued: datetime
    duration: int


class LocationSearchResponse(BaseModel):
    id: int
    name: str
    type: str  # 'region', 'system', 'station'
    parent_id: Optional[int] = None


class TypeSearchResponse(BaseModel):
    id: int
    name: str
    market_group_id: Optional[int]


class GroupTypeResponse(BaseModel):
    id: int
    name: str


@router.get("/types/search", response_model=Page[TypeSearchResponse])
async def search_types(q: str, db: AsyncSession = Depends(get_db)):
    """
    Search for types by name.
    """
    if len(q) < 3:
        return Page(items=[], total=0, page=1, size=50, pages=0)

    stmt = select(SdeType).where(SdeType.name.ilike(f"%{q}%"))

    return await paginate(
        db,
        stmt,
        transformer=lambda items: [
            {"id": item.type_id, "name": item.name, "market_group_id": item.market_group_id}
            for item in items
        ],
    )


@router.get("/locations/search", response_model=List[LocationSearchResponse])
async def search_locations(q: str, db: AsyncSession = Depends(get_db)):
    """
    Search for regions, solar systems, and stations by name.
    """
    if len(q) < 3:
        return []

    search_term = f"%{q}%"

    # Search Regions
    stmt_regions = select(SdeRegion).where(SdeRegion.name.ilike(search_term)).limit(200)
    regions = (await db.execute(stmt_regions)).scalars().all()

    # Search Solar Systems
    stmt_systems = select(SdeSolarSystem).where(SdeSolarSystem.name.ilike(search_term)).limit(300)
    systems = (await db.execute(stmt_systems)).scalars().all()

    # Search Stations
    stmt_stations = select(SdeStation).where(SdeStation.name.ilike(search_term)).limit(300)
    stations = (await db.execute(stmt_stations)).scalars().all()

    results = []
    for r in regions:
        results.append({"id": r.region_id, "name": r.name, "type": "region"})

    for s in systems:
        results.append(
            {"id": s.system_id, "name": s.name, "type": "system", "parent_id": s.region_id}
        )

    for st in stations:
        results.append(
            {
                "id": st.station_id,
                "name": st.name,
                "type": "station",
                "parent_id": st.solar_system_id,
            }
        )

    return results


@router.get("/regions")
async def get_regions(db: AsyncSession = Depends(get_db)):
    """
    Returns all available regions.
    """
    stmt = select(SdeRegion.region_id, SdeRegion.name).order_by(SdeRegion.name)
    result = await db.execute(stmt)
    regions = result.all()
    return [{"value": str(r.region_id), "label": r.name} for r in regions]


@router.get("/groups/tree")
async def get_market_groups_tree(db: AsyncSession = Depends(get_db)):
    """
    Returns the full market group hierarchy as a flat list.
    Frontend can reconstruct the tree.
    """
    stmt = select(
        SdeMarketGroup.market_group_id,
        SdeMarketGroup.parent_group_id,
        SdeMarketGroup.name,
        SdeMarketGroup.has_types,
    )
    result = await db.execute(stmt)
    groups = result.all()
    return [
        {
            "id": g.market_group_id,
            "parent_id": g.parent_group_id,
            "name": g.name,
            "has_types": g.has_types,
        }
        for g in groups
    ]


class LargeParams(Params):
    size: int = Query(50, ge=1, le=250, description="Page size")


LargePage = CustomizedPage[Page, UseParams(LargeParams)]


@router.get("/groups/{group_id}/types", response_model=LargePage[GroupTypeResponse])
async def get_group_types(group_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns types in a specific market group.
    """
    stmt = select(SdeType).where(SdeType.market_group_id == group_id)

    return await paginate(
        db,
        stmt,
        transformer=lambda items: [{"id": item.type_id, "name": item.name} for item in items],
    )


@router.get("/orders", response_model=Page[MarketOrder])
async def get_market_orders(
    search: Optional[str] = None,
    region_id: Optional[int] = None,
    solar_system_id: Optional[int] = None,
    station_id: Optional[int] = None,
    type_id: Optional[int] = None,
    market_group_id: Optional[int] = None,
    is_buy_order: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of market orders with filters.
    Limited to 250 total items (5 pages of 50 items each).
    """
    # Base query
    stmt = (
        select(
            MarketOrderModel,
            SdeType.name.label("type_name"),
            SdeRegion.name.label("region_name"),
            SdeStation.name.label("station_name"),
        )
        .outerjoin(SdeType, MarketOrderModel.type_id == SdeType.type_id)
        .outerjoin(SdeRegion, MarketOrderModel.region_id == SdeRegion.region_id)
        .outerjoin(SdeStation, MarketOrderModel.location_id == SdeStation.station_id)
    )

    # Apply filters
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                SdeType.name.ilike(search_term),
                SdeRegion.name.ilike(search_term),
                SdeStation.name.ilike(search_term),
            )
        )

    if station_id:
        stmt = stmt.where(MarketOrderModel.location_id == station_id)
    elif solar_system_id:
        stmt = stmt.where(SdeStation.solar_system_id == solar_system_id)
    elif region_id:
        stmt = stmt.where(MarketOrderModel.region_id == region_id)

    if type_id:
        stmt = stmt.where(MarketOrderModel.type_id == type_id)

    if market_group_id:
        # Include all descendant market groups of the provided market_group_id
        # Use a recursive CTE to collect the full subtree of group ids, then apply IN filter
        descendants_sql = text(
            """
            WITH RECURSIVE groups_tree AS (
                SELECT smg.market_group_id
                FROM sde_market_groups smg
                WHERE smg.market_group_id = :root_id
                UNION ALL
                SELECT child.market_group_id
                FROM sde_market_groups child
                INNER JOIN groups_tree gt ON child.parent_group_id = gt.market_group_id
            )
            SELECT market_group_id FROM groups_tree
            """
        )
        result = await db.execute(descendants_sql, {"root_id": market_group_id})
        group_ids = [row[0] for row in result.all()] or [market_group_id]
        stmt = stmt.where(SdeType.market_group_id.in_(group_ids))

    if is_buy_order is not None:
        stmt = stmt.where(MarketOrderModel.is_buy_order == (1 if is_buy_order else 0))

    # Order by issued desc, then order_id asc to guarantee deterministic ordering
    stmt = stmt.order_by(MarketOrderModel.issued.desc(), MarketOrderModel.order_id.asc())
    # Limit total results to 250 items maximum
    stmt = stmt.limit(250)

    def transform_orders(items):
        orders = []
        for order, type_name, region_name, station_name in items:
            orders.append(
                {
                    "order_id": order.order_id,
                    "type_id": order.type_id,
                    "type_name": type_name or f"Type {order.type_id}",
                    "region_id": order.region_id,
                    "region_name": region_name or f"Region {order.region_id}",
                    "location_id": order.location_id,
                    "station_name": station_name or f"Station {order.location_id}",
                    "price": float(order.price) if order.price else 0.0,
                    "volume_remain": order.volume_remain,
                    "is_buy_order": bool(order.is_buy_order),
                    "issued": order.issued,
                    "duration": order.duration,
                }
            )
        return orders

    return await paginate(db, stmt, transformer=transform_orders)


@router.post("/refresh")
async def refresh_market_data(region_id: int):
    """
    Triggers a background task to refresh market data for a region.
    """
    fetch_market_orders.delay(region_id)
    return {"message": f"Market refresh triggered for region {region_id}"}


@router.get("/types/{type_id}/details")
async def get_type_details(type_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns type details from the database.
    """
    stmt = select(SdeType).where(SdeType.type_id == type_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()

    if item:
        return {
            "description": item.description,
            "mass": item.mass,
            "volume": item.volume,
            "capacity": item.capacity,
        }

    return {"description": "Not available"}


@router.get("/history")
async def get_market_history(region_id: int, type_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches market history for a type in a region.
    Checks DB first. If empty or stale, fetches from ESI (max 90 days),
    merges with DB (upsert/replace), and cleans up old data.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=90)

    # Check DB for recent data
    stmt = (
        select(MarketHistory)
        .where(
            MarketHistory.region_id == region_id,
            MarketHistory.type_id == type_id,
            MarketHistory.date >= cutoff_date,
        )
        .order_by(MarketHistory.date.asc())
    )

    result = await db.execute(stmt)
    history_items = result.scalars().all()

    # Check if we have data and if it's fresh enough (e.g. latest entry is from today or yesterday)
    is_fresh = False
    if history_items:
        latest_date = history_items[-1].date
        # Normalize latest_date to a date object (it may already be a date)
        try:
            latest_as_date = latest_date.date()
        except Exception:
            latest_as_date = latest_date

        # If latest date is today or yesterday, consider it fresh
        if (datetime.utcnow().date() - latest_as_date).days < 1:
            is_fresh = True

    if not is_fresh:
        # Fetch from ESI
        try:
            op = esi_app.op["get_markets_region_id_history"](region_id=region_id, type_id=type_id)
            response = esi_client.request(op)

            if response.status == 200:
                esi_data = response.data

                # Filter and prepare new items
                new_items = []
                for entry in esi_data:
                    # entry.date is likely a bravado.core.date.Date or similar
                    # It might not have .year/.month/.day attributes directly accessible or they are named differently
                    # But it should support isoformat() or string conversion
                    try:
                        if hasattr(entry.date, "isoformat"):
                            date_str = entry.date.isoformat()
                        else:
                            date_str = str(entry.date)

                        # Parse YYYY-MM-DD
                        entry_dt = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception as e:
                        print(f"Error parsing date {entry.date}: {e}")
                        continue

                    if entry_dt >= cutoff_date:
                        new_items.append(
                            {
                                "region_id": region_id,
                                "type_id": type_id,
                                "date": entry_dt,
                                "average": entry.average,
                                "highest": entry.highest,
                                "lowest": entry.lowest,
                                "order_count": entry.order_count,
                                "volume": entry.volume,
                            }
                        )

                if new_items:
                    # Delete existing history for this item/region to ensure clean state and remove old data
                    delete_stmt = delete(MarketHistory).where(
                        MarketHistory.region_id == region_id, MarketHistory.type_id == type_id
                    )
                    await db.execute(delete_stmt)

                    # Insert new items
                    db.add_all([MarketHistory(**item) for item in new_items])
                    await db.commit()

                    # Re-query to get objects
                    result = await db.execute(stmt)
                    history_items = result.scalars().all()

        except Exception as e:
            print(f"Error fetching history from ESI: {e}")
            # Fallback to existing DB data if any
            pass

    return [
        {
            "date": item.date.isoformat(),
            "average": item.average,
            "highest": item.highest,
            "lowest": item.lowest,
            "order_count": item.order_count,
            "volume": item.volume,
        }
        for item in history_items
    ]
