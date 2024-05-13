import asyncio
from sqlalchemy import Column, Integer, BigInteger, Numeric, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql.functions import now
from utils import config


Base = declarative_base()


class TableMixin:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


class Channel(TableMixin, Base):
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=now(), nullable=False)
    title = Column(Text, nullable=False)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    worksheet_title = Column(Text)

    groups = relationship("Group", back_populates="channel")
    items = relationship("Item", back_populates="channel")


class Group(TableMixin, Base):
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=now(), nullable=False)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False)
    title = Column(Text, nullable=False)
    chat_id = Column(BigInteger, nullable=False)

    channel = relationship("Channel", back_populates="groups")


class Item(TableMixin, Base):
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=now(), nullable=False)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False)
    log_message_id = Column(Integer, nullable=False)
    isbn = Column(Text, nullable=False)

    channel = relationship("Channel", back_populates="items")
    orders = relationship("Order", back_populates="item")


class Order(TableMixin, Base):
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=now(), nullable=False)
    item_id = Column(Integer, ForeignKey("item.id"), nullable=False)
    user_chat_id = Column(BigInteger, nullable=False)
    user_full_name = Column(Text)
    user_handle = Column(Text)
    user_is_rf = Column(Boolean)

    item = relationship("Item", back_populates="orders")


engine = create_async_engine(f'postgresql+asyncpg://{config["pg_user"]}:{config["pg_password"]}@localhost/{config["pg_database"]}', future=True)#, poolclass=NullPool)


async def create_all():
    async with engine.begin() as session:
        await session.run_sync(Base.metadata.create_all)


open_db_session = async_sessionmaker(engine)
# import asyncio
# from sqlalchemy.ext.asyncio import async_sessionmaker

# async def drop_all_tables(engine, Base):
#     async with async_sessionmaker(engine) as session:
#         async with session() as conn:
#             await conn.run_sync(Base.metadata.drop_all)
# asyncio.run(drop_all_tables(engine, Base))

# async def drop_all():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)

# asyncio.run(drop_all())
# import asyncio
# from pprint import pprint
# from sqlalchemy import select 
# # ... (Your existing imports including Item model and open_db_session)

# async def display_all_items():
#     async with open_db_session() as session:
#         items: list[Item] = await session.scalars(select(Item))
#         for item in items:
#             print("-" * 20)
#             pprint(item.__dict__)  # You can customize how you display the data here
#             print("-" * 20)
# asyncio.run(display_all_items())

if __name__ == "__main__":
    asyncio.run(create_all())
