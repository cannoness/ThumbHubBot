from datetime import datetime

from sqlalchemy import ForeignKey, Column
from sqlalchemy.orm import mapped_column, Mapped

from Utilities.database.postgres.env import BotBase


class Cache(BotBase):
    __tablename__ = "cache_updated_date"

    id: Mapped[int] = mapped_column(primary_key=True)
    deviant_row_id: Mapped[int] = Column(ForeignKey("deviant_usernames.id"))
    last_updated: Mapped[datetime] = mapped_column()


class RoleColorAssignment(BotBase):
    __tablename__ = "role_assignment_date"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[int] = Column(ForeignKey("deviant_usernames.id"))
    last_added_timestamp: Mapped[datetime] = mapped_column()
    role_color: Mapped[str] = mapped_column()
