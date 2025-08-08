import datetime

from pydantic import BaseModel, ConfigDict

from Classes.database.postgres.models.utils import enums


class Hubber(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deviant_username: str
    discord_id: int
    ping_me: bool


class SiteUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discord_id: int
    discord_userdata: str
    deviantart_username: str
    username: str
    is_active: bool


class UserPrivate(SiteUser):
    hashed_password: str


class Creations(BaseModel):  # TODO: Migrate to merge with uploads.
    model_config = ConfigDict(from_attributes=True)

    id: int
    deviant_user_row: int
    title: str
    favs: int
    tags: str
    gallery: str
    url: str
    src_image: str
    src_snippet: str
    is_mature: bool
    date_created: datetime.datetime
    category: enums.Category
