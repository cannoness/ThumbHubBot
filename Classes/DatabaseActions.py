from typing import List

from discord.ext import commands

from Classes.database.postgres import env
from Classes.database.postgres.models.utils import crud
from thumbhubbot import LOGGER


class DatabaseActions:
    def __init__(self):
        self.engine = env.bot_engine

    @classmethod
    def fetch_pop_from_cache(cls, deviant_row_id, display_num):
        # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id}
        #         order by favs desc
        #         limit {display_num} """

        return crud.fetch_pop_from_cache(deviant_row_id, display_num)

    def fetch_entire_user_gallery(self, deviant_row_id):
        response = crud.fetch_entire_user_gallery(deviant_row_id)
        return self.convert_cache_to_result(response)

    def fetch_user_devs_by_tag(self, username, display_num, offset, tags):
        # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and
        #                 position('{tags}' in tags) > 0
        #                 order by date_created desc
        #                 limit {display_num} """
        deviant_row_id = self.fetch_hubber_row_id(username)
        response = crud.fetch_user_devs_by_tag(deviant_row_id, display_num, tags)
        return self.convert_cache_to_result(response)[offset:display_num + offset]

    def fetch_old_from_cache(self, deviant_row_id, display_num, offset):
        # query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id}
        #         order by date_created asc
        #         limit {display_num} """
        response = crud.fetch_old_from_cache(deviant_row_id, display_num)
        return self.convert_cache_to_result(response)[offset:display_num + offset]

    @classmethod
    def store_da_name(cls, discord_id: int, username: str):
        # query = f"INSERT INTO deviant_usernames (discord_id, deviant_username) VALUES ({discord_id}, '{username}') " \
        #         f"ON CONFLICT (discord_id) DO UPDATE SET deviant_username=excluded.deviant_username"
        try:
            return crud.store_da_name(discord_id, username)
        except Exception as ex:
            LOGGER.error(ex, stack_info=True)
            raise commands.errors.ObjectNotFound(f"Error while attempting to add user to the store {ex}")

    @classmethod
    def store_random_da_name(cls, username: str):
        # query = f"INSERT INTO deviant_usernames (ping_me, deviant_username) VALUES (false, '{username}') "
        try:
            return crud.store_random_da_name(username)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"Error while adding external user to the store {ex}")

    @classmethod
    def do_not_ping_me(cls, discord_id: int):
        # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, false) " \
        #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        try:
            return crud.do_not_ping_me(discord_id)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f" Error while disabling pings for user {ex}")

    @classmethod
    def ping_me(cls, discord_id: int):
        # query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, true) " \
        #         f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        try:
            return crud.ping_me(discord_id)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"Error while allowing pings for user {ex}")

    @classmethod
    def fetch_username(cls, discord_id: int):
        # query = f"Select id, deviant_username from deviant_usernames where discord_id = {discord_id}"
        try:
            return crud.fetch_username(discord_id)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"No DA user or user entry identified: {ex}")

    @classmethod
    def fetch_discord_id(cls, username: str):
        # query = f"Select discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " \
        #         f"and ping_me = true" if isinstance(username, str) else \
        #     f"Select discord_id from deviant_usernames where id = {username} " \
        #         f"and ping_me = true"
        try:
            return crud.fetch_discord_id(username)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"Error when attemping to fetch discord id {ex}")

    def get_tormund(self):
        tormunds = crud.get_tormund()
        return self.convert_cache_to_result(tormunds)

    @staticmethod
    def convert_cache_to_result(response):
        results = []
        for row in response:
            results.append(row.todict)
        return results

    @classmethod
    def add_coins(cls, discord_id: int, username: str):
        # get discord_id for username, if exists, make sure no cheaters
        #     query = f""" SELECT discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}'
        #             """ if isinstance(username, str) else \
        #         f""" SELECT discord_id from deviant_usernames where id = {username} """
        try:
            return crud.add_coins(discord_id, username)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"Error while adding hubcoins {ex}")

    def spend_coins(self, discord_id: int, amount: int):
        self.update_coins(discord_id, -amount)

    @classmethod
    def get_hubcoins(cls, discord_id: int, column: str):
        # get current coins and return the count
        # query = f""" SELECT {column} from hubcoins where discord_id = {discord_id} """
        try:
            return crud.get_hubcoins(discord_id, column)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"Error while finding hubcoin id for discord user {ex}")

    @classmethod
    def update_coins(cls, discord_id: int, amount: int):
        # coins = self.get_hubcoins(discord_id, "hubcoins")
        # add_query = f""" UPDATE hubcoins set hubcoins = {coins + amount} where discord_id = {discord_id} """
        # self.connection.execute(add_query)
        # if amount < 0:
        #     spent_query = f""" UPDATE hubcoins set spent_coins = spent_coins - {amount} where discord_id = {
        #     discord_id}  """
        #     self.connection.execute(spent_query)
        return crud.update_coins(discord_id, amount)

    @classmethod
    def get_role_added(cls, discord_id: int, column: str):
        # # get current coins and return the count
        # query = f""" SELECT {column} from role_assignment_date where discord_id = {discord_id} """
        # result = self.connection.execute(query)
        # row = result.fetchone()
        # if row:
        #     return row[0]
        # else:
        #     return 0
        return crud.get_role_added(discord_id, column)

    @classmethod
    def add_role_timer(cls, discord_id: int, role_color: str):
        # date = self.get_role_added(discord_id, "last_added_timestamp")
        # # change to upsert
        # if not date:
        #     query = f""" INSERT into role_assignment_date (discord_id, role_color) values ({discord_id},
        #             '{role_color}') """
        #     self.connection.execute(query)
        # else:
        #     add_query = f""" UPDATE role_assignment_date set last_added_timestamp = NOW(),
        #                 role_color = '{role_color}' where discord_id = {discord_id}"""
        #     self.connection.execute(add_query)
        return crud.add_role_timer(discord_id, role_color)

    @classmethod
    def delete_role(cls, discord_ids: list[int]):
        # query = f""" DELETE from role_assignment_date where discord_id in ({", ".join(discord_ids)}) """
        # self.connection.execute(query)
        return crud.delete_role(discord_ids)

    @classmethod
    def get_all_expiring_roles(cls):
        # query = f""" SELECT * from role_assignment_date"""
        # rows = self._execute_query_with_return(query)
        # current_time = datetime.datetime.now()
        # compare_against = time.mktime(current_time.timetuple())
        # roles_expiring = []
        # for row in rows:
        #     timestamp = row.last_added_timestamp
        #     comparison = time.mktime(timestamp.timetuple())
        #     if abs(comparison - compare_against) > 604800:
        #         roles_expiring.append([row.discord_id, row.role_color])
        # return roles_expiring
        return crud.get_all_expiring_roles()

    @classmethod
    def refresh_message_counts(cls):
        # query = "TRUNCATE TABLE diminishing_returns_table"
        # self.connection.execute(query)
        return crud.refresh_message_counts()

    @classmethod
    def diminish_coins_added(cls, deviant_id: int):
        # query = f"""INSERT INTO diminishing_returns_table (deviant_id)
        #             VALUES({deviant_id})
        #             ON CONFLICT (deviant_id)
        #             DO UPDATE set message_count = diminishing_returns_table.message_count + 1
        #             RETURNING message_count """
        # result = self.connection.execute(query)
        # diminish_by = result.fetchone()
        # max_percent_reduction = 0.95
        # k = 0.043
        # return round(max_percent_reduction*(1 - math.exp(-k*diminish_by[0])), 6)
        return crud.diminish_coins_added(deviant_id)

    @classmethod
    def fetch_n_random_usernames(cls, num: int):
        # query = f"Select deviant_username from deviant_usernames where deviant_username is not null"
        # query_results = ["".join(name_tuple) for name_tuple in self.connection.execute(query)]
        # return query_results[:num]
        return crud.fetch_da_usernames(num)

    @classmethod
    def fetch_n_random_hubber_ids(cls, num: int):
        # query = f"Select deviant_username from deviant_usernames where deviant_username is not null"
        # query_results = ["".join(name_tuple) for name_tuple in self.connection.execute(query)]
        # return query_results[:num]
        return crud.fetch_n_random_hubber_ids(num)

    def get_n_random_creations(self, num: int):
        # query = f"""SELECT title, is_mature, url, src_image, src_snippet , deviant_username as author
        #             FROM deviant_usernames INNER JOIN deviations
        #             ON deviations.deviant_user_row = deviant_usernames.id order by random() limit {num} """
        # results = self.connection.execute(query).fetchall()
        # return results, self._generate_links(results, num)
        creations, links = crud.get_n_random_creation_by_many_hubbers(num + 5)  # buffer in case the user has none
        return self.convert_cache_to_result(creations), links

    def get_random_creations_by_hubber(self, username, limit=24):
        deviant_user_row = crud.fetch_hubber_row_id(username)
        random_images = crud.get_random_creations_by_hubber(deviant_user_row, limit)
        return self.convert_cache_to_result(random_images)

    @classmethod
    def user_last_cache_update(cls, username: str):
        # user_id_row = self.fetch_user_row_id(username)
        # if not user_id_row:
        #     return None
        # query = f"""SELECT last_updated from cache_updated_date where deviant_row_id = {user_id_row}"""
        # result = self.connection.execute(query)
        # last_updated = result.fetchone()
        # if last_updated:
        #     return last_updated[0]
        # return None
        return crud.user_last_cache_update(username)

    @classmethod
    def fetch_hubber_row_id(cls, username: str):
        return crud.fetch_hubber_row_id(username)

    @classmethod
    def initial_add_to_cache(cls, results: List[dict], row_id: int):
        # values_list = ", ".join([f""" ({row_id}, '{result['url']}','{result['src_image']}','{result['src_snippet']
        #                         .replace("<br />", nl).replace("%","%%")}', '{result['title'].replace("'", "")
        #                         .replace("%","%%")}', {result['stats']['favourites']}, '{', '.join([tag['tag_name']
        #                                                                                             for tag in
        #                                                                       result['tags']]) if 'tags' in
        #                                                                                           result.keys() else
        #                        None}', to_date('{datetime.datetime.fromtimestamp(int(result['published_time']))
        #                        strftime('%Y%m%d')}', 'YYYYMMDD'), '{result['is_mature']}') """ for result in results])
        # query = f"INSERT INTO deviations (deviant_user_row, url, src_image, src_snippet, title, favs, tags, "
        #       f"date_created, is_mature) VALUES {values_list} ON CONFLICT (url) DO UPDATE set favs=excluded.favs, "
        #       f"title=excluded.title, tags=excluded.tags, is_mature=excluded.is_mature, src_image=excluded.src_image,"
        #       f" src_snippet=excluded.src_snippet"
        # self.connection.execute(query)
        # query = f"INSERT INTO cache_updated_date (deviant_row_id) VALUES ({row_id}) ON CONFLICT " \
        #         f"(deviant_row_id) DO UPDATE SET last_updated = now()"
        # self.connection.execute(query)
        crud.initial_add_to_cache(results, row_id)

    @classmethod
    def hubber_has_new_creations(cls, username, decoded_results):
        return crud.hubber_has_new_creations(username, decoded_results)
