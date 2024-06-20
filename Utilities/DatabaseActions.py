import math
import time

import sqlalchemy
import os
import datetime

from discord.ext import commands
from dotenv import load_dotenv
import random


class DatabaseActions:
    def __init__(self):
        load_dotenv()

        engine = sqlalchemy.create_engine(
            os.getenv("DATABASE_URL"),
            pool_pre_ping=True
        )
        self.connection = engine.connect()

    def store_da_name(self, discord_id, username):
        query = f"INSERT INTO deviant_usernames (discord_id, deviant_username) VALUES ({discord_id}, '{username}') " \
                f"ON CONFLICT (discord_id) DO UPDATE SET deviant_username=excluded.deviant_username"
        try:
            self.connection.execute(query)
        except Exception as ex:
            print(ex, flush=True)
            raise commands.errors.ObjectNotFound(f"{ex}")

    def store_random_da_name(self, username):
        query = f"INSERT INTO deviant_usernames (ping_me, deviant_username) VALUES (false, '{username}') "
        try:
            self.connection.execute(query)
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")

    def do_not_ping_me(self, discord_id):
        query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, false) " \
                f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        try:
            self.connection.execute(query).fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")

    def ping_me(self, discord_id):
        query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, true) " \
                f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        try:
            self.connection.execute(query).fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")

    def fetch_da_username(self, discord_id):
        query = f"Select deviant_username from deviant_usernames where discord_id = {discord_id}"
        try:
            result = self.connection.execute(query).fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")
        if result:
            query_results = "".join(result)
            return query_results
        return None

    def fetch_discord_id(self, username):
        query = f"Select discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " \
                f"and ping_me = true"
        try:
            result = self.connection.execute(query).fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")
        if result:
            return result[0]
        return None

    @staticmethod
    def convert_cache_to_result(response):
        results = []
        for row in response.fetchall():
            results.append(dict(row._mapping))
        return results

    def add_coins(self, discord_id, username):
        # get discord_id for username, if exists, make sure no cheaters
        if username:
            query = f""" SELECT discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' 
                    """
            try:
                result = self.connection.execute(query)
                possible_id = result.fetchone()
            except Exception as ex:
                raise commands.errors.ObjectNotFound(f"{ex}")
            if possible_id:
                user_discord_id = possible_id[0]
                if user_discord_id == discord_id:
                    # dirty cheater
                    pass
                else:
                    # do both
                    self.update_coins(discord_id, 2)
                    if user_discord_id:
                        # could be none
                        self.update_coins(user_discord_id, 1)
            else:
                # username wasn't in store
                self.update_coins(discord_id, 2)
        else:
            # username wasn't in store
            self.update_coins(discord_id, 2)

    def spend_coins(self, discord_id, amount):
        self.update_coins(discord_id, -amount)

    def get_hubcoins(self, discord_id, column):
        # get current coins and return the count
        query = f""" SELECT {column} from hubcoins where discord_id = {discord_id} """
        try:
            result = self.connection.execute(query)
            coins = result.fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")
        if coins:
            return coins[0]
        else:
            query = f""" INSERT into hubcoins (discord_id) values ({discord_id}) """
            self.connection.execute(query)
            return 0

    def update_coins(self, discord_id, amount):
        coins = self.get_hubcoins(discord_id, "hubcoins")
        add_query = f""" UPDATE hubcoins set hubcoins = {coins + amount} where discord_id = {discord_id} """
        self.connection.execute(add_query)
        if amount < 0:
            spent_query = f""" UPDATE hubcoins set spent_coins = spent_coins - {amount} where discord_id = {
            discord_id}  """
            self.connection.execute(spent_query)

    def get_role_added(self, discord_id, column):
        # get current coins and return the count
        query = f""" SELECT {column} from role_assignment_date where discord_id = {discord_id} """
        result = self.connection.execute(query)
        row = result.fetchone()
        if row:
            return row[0]
        else:
            return 0

    def add_role_timer(self, discord_id, role_color):
        date = self.get_role_added(discord_id, "last_added_timestamp")
        # change to upsert
        if not date:
            query = f""" INSERT into role_assignment_date (discord_id, role_color) values ({discord_id}, 
                    '{role_color}') """
            self.connection.execute(query)
        else:
            add_query = f""" UPDATE role_assignment_date set last_added_timestamp = NOW(), 
                        role_color = '{role_color}' where discord_id = {discord_id}"""
            self.connection.execute(add_query)

    def delete_role(self, discord_ids):
        query = f""" DELETE from role_assignment_date where discord_id in ({", ".join(discord_ids)}) """
        self.connection.execute(query)

    def get_all_expiring_roles(self):
        query = f""" SELECT * from role_assignment_date"""
        rows = self._execute_query_with_return(query)
        current_time = datetime.datetime.now()
        compare_against = time.mktime(current_time.timetuple())
        roles_expiring = []
        for row in rows:
            timestamp = row.last_added_timestamp
            comparison = time.mktime(timestamp.timetuple())
            if abs(comparison - compare_against) > 604800:
                roles_expiring.append([row.discord_id, row.role_color])
        return roles_expiring

    def refresh_message_counts(self):
        query = "TRUNCATE TABLE diminishing_returns_table"
        self.connection.execute(query)

    def diminish_coins_added(self, deviant_id):
        query = f"""INSERT INTO diminishing_returns_table (deviant_id)
                    VALUES({deviant_id}) 
                    ON CONFLICT (deviant_id) 
                    DO UPDATE set message_count = diminishing_returns_table.message_count + 1 
                    RETURNING message_count """
        result = self.connection.execute(query)
        diminish_by = result.fetchone()
        max_percent_reduction = 0.95
        k = 0.043
        return round(max_percent_reduction*(1 - math.exp(-k*diminish_by[0])), 6)

    def _execute_query_with_return(self, query):
        cursor = self.connection.execute(query)
        return cursor.fetchall()

    def fetch_da_usernames(self, num):
        query = f"Select deviant_username from deviant_usernames"
        query_results = ["".join(name_tuple) for name_tuple in self.connection.execute(query)]
        random.shuffle(query_results)
        return query_results[:num]

    def user_last_cache_update(self, username):
        user_id_row = self.fetch_user_row_id(username)
        if not user_id_row:
            return None
        query = f"""SELECT last_updated from cache_updated_date where deviant_row_id = {user_id_row}"""
        result = self.connection.execute(query)
        last_updated = result.fetchone()
        if last_updated:
            return last_updated[0]
        return None

    def fetch_user_row_id(self, username):
        query = f"Select id from deviant_usernames where lower(deviant_username) = '{username.lower()}' "
        try:
            result = self.connection.execute(query).fetchone()
        except Exception as ex:
            raise commands.errors.ObjectNotFound(f"{ex}")
        if result:
            return result[0]
        return None

    def initial_add_to_cache(self, results, row_id):
        nl = '\n'
        values_list = ", ".join([f""" ({row_id}, '{result['url']}','{result['src_image']}','{result['src_snippet']
                                .replace("<br />", nl).replace("%","%%")}', '{result['title'].replace("'", "")
                                .replace("%","%%")}', {result['stats']['favourites']}, '{', '.join([tag['tag_name'] 
                                                                                                    for tag in 
                                                                              result['tags']]) if 'tags' in 
                                                                                                  result.keys() else 
                                None}', to_date('{datetime.datetime.fromtimestamp(int(result['published_time']))
                                .strftime('%Y%m%d')}', 'YYYYMMDD'), '{result['is_mature']}') """ for result in results])
        query = f"INSERT INTO deviations (deviant_user_row, url, src_image, src_snippet, title, favs, tags, " \
                f"date_created, is_mature) VALUES {values_list} ON CONFLICT (url) DO UPDATE set favs=excluded.favs, " \
                f"title=excluded.title, tags=excluded.tags, is_mature=excluded.is_mature, src_image=excluded.src_image, " \
                f"src_snippet=excluded.src_snippet"
        self.connection.execute(query)
        query = f"INSERT INTO cache_updated_date (deviant_row_id) VALUES ({row_id}) ON CONFLICT " \
                f"(deviant_row_id) DO UPDATE SET last_updated = now()"
        self.connection.execute(query)
