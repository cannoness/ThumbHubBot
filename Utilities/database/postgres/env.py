from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker

from thumbhubbot import APIURL


BotBase = declarative_base()


bot_engine = create_engine(
    APIURL.pg_db,
    pool_pre_ping=True
)

# # database exists so this can be skipped.
BotBase.metadata.create_all(bind=bot_engine)

BotSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=bot_engine)


# Dependency
def get_bot_db():
    db = BotSessionLocal
    try:
        yield db(future=True)
    finally:
        db().close()
