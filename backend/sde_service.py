import requests
import bz2
import sqlite3
import os
import asyncio
from sqlalchemy.future import select
from database import AsyncSessionLocal, engine, Base
from models import SdeType, SdeRegion, SdeSolarSystem, SdeSolarSystemJump, SdeStation, SdeMarketGroup

SDE_URL = "https://www.fuzzwork.co.uk/dump/latest/eve.db.bz2"
DB_FILENAME = "eve.db"

def download_and_extract_sde():
    if os.path.exists(DB_FILENAME):
        print(f"{DB_FILENAME} already exists. Skipping download.")
        return

    print(f"Downloading SDE from {SDE_URL}...")
    response = requests.get(SDE_URL, stream=True)
    
    with open(f"{DB_FILENAME}.bz2", "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    
    print("Extracting SDE...")
    with bz2.open(f"{DB_FILENAME}.bz2", "rb") as source, open(DB_FILENAME, "wb") as dest:
        dest.write(source.read())
    
    os.remove(f"{DB_FILENAME}.bz2")
    print("SDE ready.")

async def import_data():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    BATCH_SIZE = 1000
    
    async with AsyncSessionLocal() as session:
        # Import Regions
        print("Importing Regions...")
        cursor.execute("SELECT regionID, regionName FROM mapRegions")
        regions = cursor.fetchall()
        for i, r in enumerate(regions):
            region = SdeRegion(region_id=r[0], name=r[1])
            await session.merge(region)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()
        
        # Import Market Groups
        print("Importing Market Groups...")
        cursor.execute("SELECT marketGroupID, parentGroupID, marketGroupName, description, hasTypes FROM invMarketGroups")
        market_groups = cursor.fetchall()
        for i, mg in enumerate(market_groups):
            market_group = SdeMarketGroup(
                market_group_id=mg[0],
                parent_group_id=mg[1],
                name=mg[2],
                description=mg[3],
                has_types=bool(mg[4]) if mg[4] is not None else False
            )
            await session.merge(market_group)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()
        
        # Import Types (Limit to market items for now to save time)
        print("Importing Types...")
        cursor.execute("SELECT typeID, typeName, groupID, volume, marketGroupID FROM invTypes WHERE marketGroupID IS NOT NULL")
        types = cursor.fetchall()
        for i, t in enumerate(types):
            item = SdeType(
                type_id=t[0],
                name=t[1],
                group_id=t[2],
                volume=t[3],
                market_group_id=t[4]
            )
            await session.merge(item)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()

        # Import Solar Systems
        print("Importing Solar Systems...")
        cursor.execute("SELECT solarSystemID, regionID, solarSystemName, security FROM mapSolarSystems")
        systems = cursor.fetchall()
        for i, s in enumerate(systems):
            system = SdeSolarSystem(
                system_id=s[0],
                region_id=s[1],
                name=s[2],
                security=s[3]
            )
            await session.merge(system)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()

        # Import Jumps
        print("Importing Jumps...")
        cursor.execute("SELECT fromSolarSystemID, toSolarSystemID FROM mapSolarSystemJumps")
        jumps = cursor.fetchall()
        for i, j in enumerate(jumps):
            jump = SdeSolarSystemJump(
                from_solar_system_id=j[0],
                to_solar_system_id=j[1]
            )
            await session.merge(jump)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()

        # Import Stations
        print("Importing Stations...")
        cursor.execute("SELECT stationID, solarSystemID, stationName FROM staStations")
        stations = cursor.fetchall()
        for i, st in enumerate(stations):
            station = SdeStation(
                station_id=st[0],
                solar_system_id=st[1],
                name=st[2]
            )
            await session.merge(station)
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()
        
        print("Import complete.")

def run_sde_update():
    download_and_extract_sde()
    asyncio.run(import_data())
