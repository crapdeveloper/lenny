import collections
import collections.abc

collections.MutableMapping = collections.abc.MutableMapping
collections.Mapping = collections.abc.Mapping
import asyncio
import csv
import io
import os
from datetime import datetime, timedelta, timezone

import redis
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from celery.utils.log import get_task_logger

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from backend.config import settings
from backend.database import SessionLocal
from backend.esi_client import esi_app, esi_client
from backend.models import (
    MarketHistory,
    MarketOrder,
    RegionEtag,
    RegionFetchStatus,
    SdeRegion,
)
from backend.sde_service import run_sde_update


# Setup OpenTelemetry
@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        resource = Resource(
            attributes={SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "lenny-worker")}
        )
        trace.set_tracer_provider(TracerProvider(resource=resource))

        otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

        CeleryInstrumentor().instrument()


def _normalize_etag_for_request(etag):
    """
    Normalize a stored ETag value for use in an If-None-Match header.
    - Preserve weak prefix W/ if present.
    - Ensure the value is quoted (e.g. "abc" or W/"abc").
    - Accept already-quoted or unquoted stored values.
    """
    if not etag:
        return None
    e = str(etag).strip()
    weak = False
    if e.startswith("W/") or e.startswith("w/"):
        weak = True
        e = e[2:].strip()

    # strip surrounding quotes if present
    if e.startswith('"') and e.endswith('"') and len(e) >= 2:
        e = e[1:-1]

    quoted = '"' + e + '"'
    return f"W/{quoted}" if weak else quoted


def _get_resp_header(resp, key):
    """Return header value from response in a case-insensitive way.

    The ESI client may expose headers under `.header` or `.headers` and
    may have keys in different casing. This helper handles those cases and
    returns the matching value or None.
    """
    hdrs = None
    if hasattr(resp, "header") and resp.header is not None:
        hdrs = resp.header
    elif hasattr(resp, "headers") and resp.headers is not None:
        hdrs = resp.headers
    else:
        return None

    # direct lookup for common forms
    for k in (key, key.lower(), key.upper()):
        if k in hdrs:
            return hdrs.get(k)

    # fallback: iterate keys case-insensitively
    for k, v in hdrs.items():
        try:
            if k.lower() == key.lower():
                return v
        except Exception:
            continue
    return None


celery_app = Celery(
    "lenny_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

redis_client = redis.from_url(settings.CELERY_BROKER_URL)
logger = get_task_logger(__name__)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "fetch-all-regions-every-minute": {
        "task": "fetch_all_regions_orders",
        "schedule": crontab(minute="*/5"),  # Run every 5 minutes
    },
    "update-sde-daily": {
        "task": "update_sde",
        "schedule": crontab(hour=0, minute=0),  # Run every day at midnight
    },
    "fetch-history-daily": {
        "task": "fetch_all_regions_history",
        "schedule": crontab(hour=1, minute=0),  # Run every day at 1 AM
    },
}


@celery_app.task(name="worker.fetch_all_regions_orders")
def fetch_all_regions_orders():
    """
    Triggers market order fetch for all regions, ensuring only one instance runs at a time.
    """
    # Lock expires after 5 minutes, matching the schedule interval.
    lock = redis_client.lock("lock:fetch_all_regions_orders", timeout=300)

    if not lock.acquire(blocking=False):
        logger.info("Skipping fetch_all_regions_orders: task is already running.")
        return

    try:
        logger.info("Starting market order fetch for all regions...")
        db = SessionLocal()
        try:
            regions = db.query(SdeRegion).all()
            for region in regions:
                fetch_market_orders.delay(region.region_id)
            logger.info(f"Triggered fetch for {len(regions)} regions.")
        except Exception as e:
            logger.error(f"Error fetching regions: {e}", exc_info=True)
        finally:
            db.close()
    finally:
        lock.release()


@celery_app.task(name="update_sde")
def update_sde():
    """
    Updates the Static Data Export (SDE) from Fuzzwork.
    """
    print("Starting SDE update...")
    try:
        run_sde_update()
        print("SDE update finished successfully.")
        return {"status": "success"}
    except Exception as e:
        print(f"Error updating SDE: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="fetch_market_orders")
def fetch_market_orders(region_id: int, type_id: int = None):
    """
    Fetches market orders for a given region using ETags for differential updates.
    Only fetches changed pages and removes expired orders.
    """
    logger.info(f"Fetching market orders for Region {region_id}...")

    db = SessionLocal()
    try:
        fetch_start_time = datetime.now(timezone.utc)

        # Update fetch status - started
        stmt = insert(RegionFetchStatus).values(
            region_id=region_id,
            last_fetch_started=fetch_start_time,
            last_fetch_success=False,
            orders_fetched=0,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["region_id"],
            set_={"last_fetch_started": fetch_start_time, "last_fetch_success": False},
        )
        db.execute(stmt)
        db.commit()

        # Optimization: Pre-fetch all ETags for this region to reduce DB queries
        existing_etags = {
            row.page: row.etag for row in db.query(RegionEtag).filter_by(region_id=region_id).all()
        }

        # Initial request for page 1
        kwargs = {"region_id": region_id, "order_type": "all", "page": 1}
        if type_id is not None:
            kwargs["type_id"] = type_id

        # Get ETag for Page 1
        current_etag = existing_etags.get(1)
        headers = {}
        if current_etag:
            headers["If-None-Match"] = _normalize_etag_for_request(current_etag)
            print(f"Using ETag {headers['If-None-Match']} for Region {region_id} Page 1")

        op = esi_app.op["get_markets_region_id_orders"](**kwargs)
        res = esi_client.request(op, headers=headers)

        orders_to_process = []
        etags_to_update = []  # List of (page, etag)
        seen_order_ids = set()  # Track all order IDs from this fetch
        any_page_changed = False
        any_page_unchanged = False  # Track if any page returned 304

        x_pages = 1

        if res.status == 304:
            logger.info(f"Region {region_id} Page 1 unchanged.")
            any_page_unchanged = True
            x_pages = _get_resp_header(res, "X-Pages") or 1
        elif res.status == 200:
            logger.info(f"Region {region_id} Page 1 updated.")
            any_page_changed = True
            orders_to_process.extend(res.data)
            seen_order_ids.update(order.order_id for order in res.data)
            x_pages = _get_resp_header(res, "X-Pages") or 1
            new_etag = _get_resp_header(res, "ETag")
            if new_etag:
                etags_to_update.append((1, new_etag))
        else:
            logger.error(
                f"Error fetching orders for Region {region_id} Page 1: {res.status} - {res.data}"
            )
            # Mark fetch as failed
            stmt = insert(RegionFetchStatus).values(region_id=region_id, last_fetch_success=False)
            stmt = stmt.on_conflict_do_update(
                index_elements=["region_id"], set_={"last_fetch_success": False}
            )
            db.execute(stmt)
            db.commit()
            return {"status": "error", "code": res.status}

        if isinstance(x_pages, list):
            x_pages = x_pages[0]
        pages = int(x_pages)
        print(f"Total pages: {pages}")

        # Fetch remaining pages
        for page in range(2, pages + 1):
            kwargs["page"] = page

            current_etag = existing_etags.get(page)
            headers = {}
            if current_etag:
                headers["If-None-Match"] = _normalize_etag_for_request(current_etag)

            op = esi_app.op["get_markets_region_id_orders"](**kwargs)
            page_res = esi_client.request(op, headers=headers)

            if page_res.status == 304:
                any_page_unchanged = True
                continue
            elif page_res.status == 200:
                print(f"Page {page} updated.")
                any_page_changed = True
                orders_to_process.extend(page_res.data)
                seen_order_ids.update(order.order_id for order in page_res.data)
                new_etag = _get_resp_header(page_res, "ETag")
                if new_etag:
                    etags_to_update.append((page, new_etag))
            else:
                logger.warning(
                    f"Error fetching page {page} for Region {region_id}: {page_res.status}"
                )

        logger.info(
            f"Total new/modified orders to process for Region {region_id}: {len(orders_to_process)}"
        )

        if orders_to_process:
            # Use a temporary table and COPY for bulk upsert
            temp_table_name = "temp_market_orders"

            # Use raw SQL to create a temporary table like market_orders
            # ON COMMIT DROP ensures it's cleaned up automatically
            # Using raw connection from SQLAlchemy session
            with db.connection().connection.cursor() as cursor:
                cursor.execute(
                    f"""
                CREATE TEMP TABLE {temp_table_name} (
                    order_id BIGINT PRIMARY KEY,
                    type_id INTEGER,
                    region_id INTEGER,
                    price TEXT,
                    volume_remain INTEGER,
                    is_buy_order INTEGER,
                    issued TIMESTAMP WITH TIME ZONE,
                    duration INTEGER,
                    min_volume INTEGER,
                    range TEXT,
                    location_id BIGINT,
                    updated_at TIMESTAMP WITH TIME ZONE
                ) ON COMMIT DROP;
                """
                )

                # Use an in-memory string buffer for CSV data, tab-delimited
                f = io.StringIO()
                writer = csv.writer(f, delimiter="\t")

                # Write order data to the in-memory file
                for order in orders_to_process:
                    writer.writerow(
                        [
                            order.order_id,
                            order.type_id,
                            region_id,
                            str(order.price),
                            order.volume_remain,
                            1 if order.is_buy_order else 0,
                            order.issued.v.isoformat(),
                            order.duration,
                            order.min_volume,
                            order.range,
                            order.location_id,
                            fetch_start_time.isoformat(),
                        ]
                    )

                # Rewind the buffer to the beginning
                f.seek(0)

                # Use copy_expert to stream data into the temp table
                cursor.copy_expert(
                    f"COPY {temp_table_name} FROM STDIN WITH (FORMAT csv, DELIMITER '\t')",
                    f,
                )

                # Now, do a single bulk upsert from the temp table to the main table
                upsert_sql = f"""
                INSERT INTO market_orders (order_id, type_id, region_id, price, volume_remain, is_buy_order, issued, duration, min_volume, range, location_id, updated_at)
                SELECT * FROM {temp_table_name}
                ON CONFLICT (order_id) DO UPDATE SET
                    price = EXCLUDED.price,
                    volume_remain = EXCLUDED.volume_remain,
                    issued = EXCLUDED.issued,
                    updated_at = EXCLUDED.updated_at;
                """
                cursor.execute(upsert_sql)

                logger.info(
                    f"Bulk upserted {len(orders_to_process)} orders for Region {region_id}."
                )

        # Clean up expired/completed orders (not seen in this fetch)
        # Only delete if at least one page changed (to avoid false deletions when all pages return 304)
        if any_page_changed and type_id is None:  # Only cleanup when fetching all types
            # Get last successful fetch time for this region
            last_fetch = (
                db.query(RegionFetchStatus.last_fetch_completed)
                .filter_by(region_id=region_id)
                .scalar()
            )

            if last_fetch:
                # CRITICAL FIX: If any page returned 304, those orders are still valid
                # but weren't upserted, so their updated_at is old. Update all existing
                # orders' timestamps to prevent incorrect deletion.
                if any_page_unchanged:
                    update_stmt = (
                        update(MarketOrder)
                        .where(MarketOrder.region_id == region_id)
                        .values(updated_at=fetch_start_time)
                    )
                    db.execute(update_stmt)
                    print(
                        f"Updated timestamps for all orders in Region {region_id} (some pages unchanged)"
                    )

                # Delete orders that weren't updated in this fetch
                delete_stmt = delete(MarketOrder).where(
                    MarketOrder.region_id == region_id,
                    MarketOrder.updated_at < fetch_start_time,
                )
                result = db.execute(delete_stmt)
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info(
                        f"Removed {deleted_count} expired/completed orders from Region {region_id}"
                    )

        # Update ETags
        for page, etag in etags_to_update:
            stmt = insert(RegionEtag).values(region_id=region_id, page=page, etag=etag)
            stmt = stmt.on_conflict_do_update(
                index_elements=["region_id", "page"],
                set_={"etag": stmt.excluded.etag, "last_updated": func.now()},
            )
            db.execute(stmt)

        # Update fetch status - completed successfully
        stmt = insert(RegionFetchStatus).values(
            region_id=region_id,
            last_fetch_completed=fetch_start_time,
            last_fetch_success=True,
            orders_fetched=len(orders_to_process),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["region_id"],
            set_={
                "last_fetch_completed": fetch_start_time,
                "last_fetch_success": True,
                "orders_fetched": len(orders_to_process),
            },
        )
        db.execute(stmt)

        db.commit()

    except Exception:
        logger.error(f"Error in fetch_market_orders for region {region_id}", exc_info=True)
        db.rollback()
        # Mark fetch as failed
        try:
            stmt = insert(RegionFetchStatus).values(region_id=region_id, last_fetch_success=False)
            stmt = stmt.on_conflict_do_update(
                index_elements=["region_id"], set_={"last_fetch_success": False}
            )
            db.execute(stmt)
            db.commit()
        except Exception:
            logger.error(
                f"Could not update fetch status to failed for region {region_id}",
                exc_info=True,
            )
            pass
    finally:
        db.close()

    return {
        "status": "success",
        "region_id": region_id,
        "orders_count": len(orders_to_process),
    }


@celery_app.task(name="fetch_all_regions_history")
def fetch_all_regions_history():
    """
    Triggers market history fetch for all regions.
    """
    logger.info("Triggering market history fetch for all regions...")
    db = SessionLocal()
    try:
        regions = db.query(SdeRegion).all()
        for region in regions:
            fetch_region_history.delay(region.region_id)
        logger.info(f"Triggered history fetch for {len(regions)} regions.")
    except Exception as e:
        logger.error("Error fetching regions for history task", exc_info=True)
    finally:
        db.close()


@celery_app.task(name="fetch_region_history")
def fetch_region_history(region_id: int):
    """
    Fetches market history for all active types in a region.
    """
    print(f"Fetching market history for Region {region_id}...")
    db = SessionLocal()
    try:
        # 1. Get all active types in the region
        type_ids = set()
        pages = 1

        # Fetch first page to get total pages
        op = esi_app.op["get_markets_region_id_types"](region_id=region_id, page=1)
        res = esi_client.request(op)

        if res.status == 200:
            type_ids.update(res.data)
            x_pages = _get_resp_header(res, "X-Pages") or 1
            if isinstance(x_pages, list):
                x_pages = x_pages[0]
            pages = int(x_pages)
        else:
            logger.error(f"Error fetching types for region {region_id}: {res.status}")
            return

        for page in range(2, pages + 1):
            op = esi_app.op["get_markets_region_id_types"](region_id=region_id, page=page)
            res = esi_client.request(op)
            if res.status == 200:
                type_ids.update(res.data)

        logger.info(
            f"Found {len(type_ids)} active types in Region {region_id}. Checking for stale data..."
        )

        # Optimization: Check DB for latest history date to avoid unnecessary ESI calls
        stmt = (
            select(MarketHistory.type_id, func.max(MarketHistory.date))
            .where(MarketHistory.region_id == region_id)
            .group_by(MarketHistory.type_id)
        )

        existing_history = db.execute(stmt).all()
        last_updates = {row[0]: row[1] for row in existing_history}

        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

        types_to_fetch = []
        for type_id in type_ids:
            last_date = last_updates.get(type_id)
            if last_date:
                if last_date < yesterday:
                    types_to_fetch.append(type_id)
            else:
                types_to_fetch.append(type_id)

        logger.info(
            f"Fetching history for {len(types_to_fetch)} types in Region {region_id} (skipped {len(type_ids) - len(types_to_fetch)} up-to-date types)..."
        )

        # 2. Fetch history for each type
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=90)).date()

        # Optimization: Load all existing dates for this region in one query
        existing_dates_stmt = select(MarketHistory.type_id, MarketHistory.date).where(
            MarketHistory.region_id == region_id, MarketHistory.date >= cutoff_date
        )
        all_existing = db.execute(existing_dates_stmt).all()
        existing_dates_by_type = {}
        for tid, date in all_existing:
            if tid not in existing_dates_by_type:
                existing_dates_by_type[tid] = set()
            existing_dates_by_type[tid].add(date)

        for type_id in types_to_fetch:
            try:
                op = esi_app.op["get_markets_region_id_history"](
                    region_id=region_id, type_id=type_id
                )
                res = esi_client.request(op)

                if res.status == 200:
                    history_data = res.data
                    # Filter for last 90 days
                    recent_history = [h for h in history_data if h.date.v >= cutoff_date]

                    if recent_history:
                        # Use a temporary table and COPY for bulk insert
                        temp_table_name = "temp_market_history"
                        with db.connection().connection.cursor() as cursor:
                            cursor.execute(
                                f"""
                            CREATE TEMP TABLE {temp_table_name} (
                                region_id INTEGER,
                                type_id INTEGER,
                                date DATE,
                                average FLOAT,
                                highest FLOAT,
                                lowest FLOAT,
                                order_count BIGINT,
                                volume BIGINT
                            ) ON COMMIT DROP;
                            """
                            )

                            f = io.StringIO()
                            writer = csv.writer(f, delimiter="\t")

                            existing_dates = existing_dates_by_type.get(type_id, set())

                            rows_to_insert = []
                            for entry in recent_history:
                                entry_date = entry.date.v
                                if entry_date not in existing_dates:
                                    rows_to_insert.append(
                                        [
                                            region_id,
                                            type_id,
                                            entry_date.isoformat(),
                                            entry.average,
                                            entry.highest,
                                            entry.lowest,
                                            entry.order_count,
                                            entry.volume,
                                        ]
                                    )

                            if rows_to_insert:
                                writer.writerows(rows_to_insert)
                                f.seek(0)
                                cursor.copy_expert(
                                    f"COPY {temp_table_name} FROM STDIN WITH (FORMAT csv, DELIMITER '\t')",
                                    f,
                                )

                                # Insert from temp table, ignoring conflicts (though we already filtered)
                                insert_sql = f"""
                                INSERT INTO market_history (region_id, type_id, date, average, highest, lowest, order_count, volume)
                                SELECT region_id, type_id, date, average, highest, lowest, order_count, volume FROM {temp_table_name}
                                ON CONFLICT (region_id, type_id, date) DO NOTHING;
                                """
                                cursor.execute(insert_sql)
                                db.commit()
                elif res.status == 404:
                    # Type might not have history or invalid
                    pass
                else:
                    logger.warning(
                        f"Error fetching history for Region {region_id} Type {type_id}: {res.status}"
                    )
            except Exception:
                logger.error(
                    f"Exception fetching history for Region {region_id} Type {type_id}",
                    exc_info=True,
                )
                db.rollback()

    except Exception:
        logger.error(f"Error in fetch_region_history for region {region_id}", exc_info=True)
    finally:
        db.close()
