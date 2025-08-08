from sqlalchemy import Boolean, Column, String, BIGINT, Integer, TEXT, ForeignKey
from sqlalchemy.orm import relationship, Mapped

from Utilities.database.postgres.env import BotBase


class Hubbers(BotBase):
    __tablename__ = "deviant_usernames"

    id: Mapped[int] = Column(BIGINT, primary_key=True)
    deviant_username: Mapped[str] = Column(String(128), unique=True, default=None)
    ping_me: Mapped[bool] = Column(Boolean)
    discord_id: Mapped[int] = Column(BIGINT, unique=True, default=None)


class SiteUser(BotBase):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    discord_id: Mapped[int] = Column(BIGINT, unique=True, default=None)
    discord_userdata: Mapped[str] = Column(TEXT)
    deviantart_username: Mapped[str] = Column(String(128), unique=True, index=True)
    username: Mapped[str] = Column(String(128), unique=True, index=True)
    hashed_password: Mapped[str] = Column(String(1024))
    is_active: Mapped[bool] = Column(Boolean, default=True)


class LinkedAccounts(BotBase):
    __tablename__ = "linked_accounts"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"))
    discord_id: Mapped[int] = Column(BIGINT, unique=True, default=None)
    discord_userdata: Mapped[str] = Column(String(128), unique=True, index=True)
    deviant_username: Mapped[str] = Column(String(128), unique=True, index=True)
    tumblr_user: Mapped[str] = Column(String(128), unique=True, index=True)
    owner: Mapped[SiteUser] = relationship("SiteUser")
