from database import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(BigInteger, unique=True, index=True)
    character_name = Column(String)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="user")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "ChatMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class SdeType(Base):
    __tablename__ = "sde_types"

    type_id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    group_id = Column(Integer)
    volume = Column(Float)
    mass = Column(Float)
    capacity = Column(Float)
    description = Column(Text)
    market_group_id = Column(Integer, index=True)


class SdeMarketGroup(Base):
    __tablename__ = "sde_market_groups"

    market_group_id = Column(Integer, primary_key=True)
    parent_group_id = Column(Integer, index=True, nullable=True)
    name = Column(String)
    description = Column(Text)
    has_types = Column(Boolean)


class SdeRegion(Base):
    __tablename__ = "sde_regions"

    region_id = Column(Integer, primary_key=True)
    name = Column(String, index=True)


class SdeSolarSystem(Base):
    __tablename__ = "sde_solar_systems"

    system_id = Column(Integer, primary_key=True)
    region_id = Column(Integer, index=True)
    name = Column(String, index=True)
    security = Column(Float)


class SdeSolarSystemJump(Base):
    __tablename__ = "sde_solar_system_jumps"

    from_solar_system_id = Column(Integer, primary_key=True)
    to_solar_system_id = Column(Integer, primary_key=True)


class SdeStation(Base):
    __tablename__ = "sde_stations"

    station_id = Column(BigInteger, primary_key=True)
    solar_system_id = Column(Integer, index=True)
    name = Column(String, index=True)


class MarketOrder(Base):
    __tablename__ = "market_orders"

    order_id = Column(BigInteger, primary_key=True)
    type_id = Column(Integer, index=True)
    region_id = Column(Integer, index=True)
    price = Column(Text)  # Using Text for high precision or Float/Numeric
    volume_remain = Column(Integer)
    is_buy_order = Column(Integer)  # Boolean stored as 0/1 or Boolean type
    issued = Column(DateTime(timezone=True))
    duration = Column(Integer)
    min_volume = Column(Integer)
    range = Column(String)
    location_id = Column(BigInteger)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    __table_args__ = (
        # Optimize common filters and ordering:
        # WHERE type_id=?, region_id=?, is_buy_order=? ORDER BY issued DESC
        # Also benefits queries filtering subsets of these columns.
        # Database-agnostic composite index via SQLAlchemy.
        Index(
            "ix_market_orders_type_region_buy_issued",
            type_id,
            region_id,
            is_buy_order,
            issued,
        ),
    )


class MarketHistory(Base):
    __tablename__ = "market_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    region_id = Column(Integer, index=True)
    type_id = Column(Integer, index=True)
    date = Column(Date)
    average = Column(Float)
    highest = Column(Float)
    lowest = Column(Float)
    order_count = Column(BigInteger)
    volume = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint(
            "region_id", "type_id", "date", name="uq_market_history_region_type_date"
        ),
    )


class RegionEtag(Base):
    __tablename__ = "region_etags"

    region_id = Column(Integer, primary_key=True)
    page = Column(Integer, primary_key=True)
    etag = Column(String)
    last_updated = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RegionFetchStatus(Base):
    __tablename__ = "region_fetch_status"

    region_id = Column(Integer, primary_key=True)
    last_fetch_started = Column(DateTime(timezone=True))
    last_fetch_completed = Column(DateTime(timezone=True))
    last_fetch_success = Column(Boolean, default=True)
    orders_fetched = Column(Integer, default=0)


class TaskLock(Base):
    __tablename__ = "task_locks"

    task_id = Column(String, primary_key=True)
    locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True))
