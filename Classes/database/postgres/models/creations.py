from typing import List
from datetime import datetime, UTC

from sqlalchemy import Boolean, Column, ForeignKey, Integer, BIGINT, TEXT, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column


from Classes.database.postgres.env import BotBase
from Classes.database.postgres.models.utils import enums
from Classes.database.postgres.models.users import Hubbers


class Creations(BotBase):  # TODO: Migrate to merge with uploads.
    __tablename__ = "deviations"

    id: Mapped[int] = Column(Integer, primary_key=True)
    title: Mapped[str] = Column(TEXT, unique=True, default=None)
    favs: Mapped[int] = Column(Integer, default=0)
    tags: Mapped[str] = Column(TEXT)
    gallery: Mapped[str] = Column(TEXT)
    is_mature: Mapped[bool] = Column(Boolean)
    date_created: Mapped[DateTime] = Column(DateTime, default=datetime.now(UTC))
    deviant_user_row: Mapped[int] = Column(BIGINT, ForeignKey("deviant_usernames.id"))
    category: Mapped[enums.Category] = mapped_column(default=enums.Category.UNCATEGORIZED)
    url: Mapped[str] = Column(TEXT)
    src_image: Mapped[str] = Column(TEXT)
    src_snippet: Mapped[str] = Column(TEXT)
    user: Mapped[List[Hubbers]] = relationship()

    @property
    def todict(self):
        return {c.name: str(getattr(self, c.name)) for c in self.__table__.columns}
