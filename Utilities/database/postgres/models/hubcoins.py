
from sqlalchemy import  Column, ForeignKey, Integer,  BIGINT

from Utilities.database.postgres.env import BotBase


class Hubcoins(BotBase):
    __tablename__ = "hubcoins"

    id = Column(Integer, primary_key=True)
    discord_id = Column(BIGINT, ForeignKey("deviant_usernames.id"))
    hubcoins = Column(Integer, default=0)
    spent_coins = Column(Integer, default=0)