#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the database with SDE data and triggers initial market data fetching.
Run this manually during development or initial deployment setup.

Usage:
    python init_database.py
    
Or via Docker:
    docker compose exec backend python init_database.py
"""

import sys
from database import SessionLocal
from models import SdeRegion
from sde_service import run_sde_update
from sqlalchemy import func
from worker import celery_app


def main():
    """Initialize the database with SDE data and trigger market data fetching."""
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Check if SDE data already exists
        region_count = db.query(func.count(SdeRegion.region_id)).scalar()
        
        if region_count > 0:
            print(f"\n⚠️  SDE already initialized with {region_count} regions.")
            response = input("Do you want to re-initialize? This will update SDE data. (y/N): ")
            if response.lower() != 'y':
                print("Initialization cancelled.")
                return 0
        
        # Run SDE update
        print("\n📦 Step 1/3: Updating SDE (Static Data Export)...")
        print("This may take several minutes...")
        run_sde_update()
        print("✅ SDE update completed.")
        
        # Verify regions were loaded
        region_count = db.query(func.count(SdeRegion.region_id)).scalar()
        print(f"✅ Loaded {region_count} regions.")
        
        # Trigger market order fetching
        print("\n📈 Step 2/3: Triggering market order fetch for all regions...")
        result = celery_app.send_task('fetch_all_regions_orders')
        print(f"✅ Task queued: {result.id}")
        
        # Trigger market history fetching
        print("\n📊 Step 3/3: Triggering market history fetch for all regions...")
        result = celery_app.send_task('fetch_all_regions_history')
        print(f"✅ Task queued: {result.id}")
        
        print("\n" + "=" * 60)
        print("✅ Database initialization completed!")
        print("=" * 60)
        print("\nMarket data fetching has been queued.")
        print("Check worker logs to monitor progress:")
        print("  docker compose logs worker --follow")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
