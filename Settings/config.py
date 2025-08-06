import enum
import os
from dotenv import load_dotenv

load_dotenv()


class RoleEnum(enum.Enum):
    MODERATORS = "Moderators"
    THE_HUB = "The Hub"
    BOT_SLEUTH = "Bot Sleuth"
    THE_PEEPS = "the peeps"
    FREQUENT_THUMBERS = "Frequent Thumbers"
    VETERAN_THUMBERS = "Veteran Thumbers"
    VIP = "The Hub VIP"
    DEVIANTS = "Deviants"


class Role:
    _moderators = RoleEnum.MODERATORS.value
    _the_hub = RoleEnum.THE_HUB.value
    _bot_sleuth = RoleEnum.BOT_SLEUTH.value
    _the_peeps = RoleEnum.THE_PEEPS.value
    _frequent_thumbers = RoleEnum.FREQUENT_THUMBERS.value
    _veteran_thumbers = RoleEnum.VETERAN_THUMBERS.value
    _vip = RoleEnum.VIP.value
    _deviants = RoleEnum.DEVIANTS.value

    @property
    def moderators(self) -> str:
        return type(self)._moderators

    @property
    def the_hub(self) -> str:
        return self._the_hub

    @property
    def bot_sleuth(self) -> str:
        return self._bot_sleuth

    @property
    def the_peeps(self) -> str:
        return self._the_peeps

    @property
    def frequent_thumbers(self) -> str:
        return self._frequent_thumbers

    @property
    def veteran_thumbers(self) -> str:
        return self._veteran_thumbers

    @property
    def vip(self) -> str:
        return self._vip

    @property
    def deviants(self) -> str:
        return self._deviants


class CooldownEnum(enum.Enum):
    DEFAULT_COOLDOWN = 1800
    PRIV_COOLDOWN = 900
    VIP_COOLDOWN = 600
    VT_COOLDOWN = 360
    POST_RATE = 1


class Cooldown:
    _default = CooldownEnum.DEFAULT_COOLDOWN.value
    _priv = CooldownEnum.PRIV_COOLDOWN.value
    _vip = CooldownEnum.VIP_COOLDOWN.value
    _vt = CooldownEnum.VT_COOLDOWN.value
    _post_rate = CooldownEnum.POST_RATE.value

    @property
    def default(self) -> int:
        return self._default

    @property
    def priv(self) -> int:
        return self._priv

    @property
    def vip(self) -> int:
        return self._vip

    @property
    def vt(self) -> int:
        return self._vt

    @property
    def post_rate(self) -> int:
        return self._post_rate


class RoleSet:
    _administrative =  {RoleEnum.MODERATORS.value, RoleEnum.THE_HUB.value, RoleEnum.THE_PEEPS.value}
    _privileged = {RoleEnum.VETERAN_THUMBERS.value, RoleEnum.THE_PEEPS.value}
    _whitelist = {RoleEnum.MODERATORS.value, RoleEnum.THE_HUB.value, RoleEnum.THE_PEEPS.value,
                          RoleEnum.BOT_SLEUTH.value}

    @property
    def admins(self) -> set:
        return self._administrative

    @property
    def privileged(self) -> set:
        return self._privileged

    @property
    def whitelist(self) -> set:
        return self._whitelist


class MaxImageCountEnum(enum.Enum):
    MOD_COUNT = 6
    PRIV_COUNT = 6
    DEV_COUNT = 4


class MaxImageCount:
    _mod = MaxImageCountEnum.MOD_COUNT.value
    _privileged = MaxImageCountEnum.PRIV_COUNT.value
    _deviants = MaxImageCountEnum.DEV_COUNT.value

    @property
    def mod(self) -> int:
        return self._mod

    @property
    def privileged(self) -> int:
        return self._privileged

    @property
    def deviants(self) -> int:
        return self._deviants


class ConfigEnum(enum.Enum):
    MOD_CHANNEL = int(os.getenv("MOD_CHANNEL"))
    NSFW_CHANNEL = int(os.getenv("NSFW_CHANNEL"))
    BOT_TESTING_CHANNEL = int(os.getenv("BOT_TESTING_CHANNEL"))
    BOT_TESTING_RANGE_CHANNEL = int(os.getenv("BOT_TESTING_RANGE_CHANNEL"))
    THE_PEEPS = int(os.getenv("STREAMS_N_THINGS"))
    THUMBHUB_CHANNEL = int(os.getenv("THUMBHUB_CHANNEL"))
    ANNOUNCEMENTS_CHANNEL = int(os.getenv("BOT_TESTING_CHANNEL"))
    GUILD_ID: int = int(os.getenv("GUILD_ID"))
    GUILD_ADMIN: int = int(os.getenv("GUILD_ADMIN_ID"))
    LOCAL: int = os.getenv("LOCAL") or False
    JSON_FILE = os.getenv("JSON_FILE")
    FONT = os.getenv("FONT")


class Config:
    _admin: int = ConfigEnum.GUILD_ADMIN.value
    _bot_channel: int = ConfigEnum.BOT_TESTING_CHANNEL.value
    _mod_channel: int = ConfigEnum.MOD_CHANNEL.value
    _nsfw_channel: int = ConfigEnum.NSFW_CHANNEL.value
    _bot_testing_range_channel: int = ConfigEnum.BOT_TESTING_RANGE_CHANNEL.value
    _the_peeps: int = ConfigEnum.THE_PEEPS.value
    _thumbhub_channel: int = ConfigEnum.THUMBHUB_CHANNEL.value
    _announcements_channel: int = ConfigEnum.ANNOUNCEMENTS_CHANNEL.value
    _guild_id: int = ConfigEnum.GUILD_ID.value
    _json_file: str = ConfigEnum.JSON_FILE.value
    _font: str = ConfigEnum.FONT.value
    _local: bool = bool(ConfigEnum.LOCAL.value) if ConfigEnum.LOCAL.value is not None else False

    @property
    def bot_channel(self) -> int:
        return self._bot_channel

    @property
    def bot_testing_range_channel(self) -> int:
        return self._bot_testing_range_channel

    @property
    def mod_channel(self) -> int:
        return self._mod_channel

    @property
    def nsfw_channel(self) -> int:
        return self._nsfw_channel

    @property
    def the_peeps(self) -> int:
        return self._the_peeps

    @property
    def thumbhub_channel(self) -> int:
        return self._thumbhub_channel

    @property
    def announcements_channel(self) -> int:
        return self._announcements_channel

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def guild_admin(self) -> int:
        return self._admin

    @property
    def local(self) -> bool:
        return self._local

    @property
    def json_file(self) -> str:
        return self._json_file

    @property
    def font(self) -> str:
        return type(self)._font


class ApiUrlEnum(enum.Enum):
    AUTH_URL = "https://www.deviantart.com/oauth2/token?grant_type=client_credentials&"
    API_URL = "https://www.deviantart.com/api/v1/oauth2/"
    RANDOM_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=by%3A"
    FAV_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=favby%3A"
    DA_URL = "http://www.deviantart.com/"
    PG_DB_URL = os.getenv("DATABASE_URL")


class ApiUrl:
    _auth = ApiUrlEnum.AUTH_URL.value
    _api = ApiUrlEnum.API_URL.value
    _da_url = ApiUrlEnum.DA_URL.value
    _random_rss = ApiUrlEnum.RANDOM_RSS_URL.value
    _fav_rss = ApiUrlEnum.FAV_RSS_URL.value
    _pg_db = ApiUrlEnum.PG_DB_URL.value

    @property
    def auth(self) -> str:
        return self._auth

    @property
    def api(self) -> str:
        return self._api

    @property
    def da_url(self) -> str:
        return self._da_url

    @property
    def random_rss(self) -> str:
        return self._random_rss

    @property
    def fav_rss(self) -> str:
        return self._fav_rss

    @property
    def pg_db(self) -> str:
        return self._pg_db
