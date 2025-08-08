
from sqlalchemy import Column, ForeignKey, Integer, BIGINT

from Utilities.database.postgres.env import BotBase


class DiminishingReturns(BotBase):
    __tablename__ = "diminishing_returns_table"

    id = Column(Integer, primary_key=True)
    deviant_id = Column(BIGINT, ForeignKey("deviant_usernames.id"))
    message_count = Column(Integer, default=0)

