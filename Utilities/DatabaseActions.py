import sqlalchemy
import os
import datetime
from dotenv import load_dotenv
import random


class DatabaseActions:
    def __init__(self):
        load_dotenv()
        self.database_url = os.getenv("DATABASE_URL")
        seed = os.getpid()+int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        random.seed(seed)

        engine = sqlalchemy.create_engine(self.database_url)
        self.connection = engine.connect()

    def store_da_name(self, discord_id, username):
        query = f"INSERT INTO deviant_usernames (discord_id, deviant_username) VALUES ({discord_id}, '{username}') " \
                f"ON CONFLICT (discord_id) DO UPDATE SET deviant_username= excluded.deviant_username"
        self.connection.execute(query)

    def store_random_da_name(self, username):
        query = f"INSERT INTO deviant_usernames (ping_me, deviant_username) VALUES (false, '{username}') "
        self.connection.execute(query)

    def do_not_ping_me(self, discord_id):
        query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, false) " \
                f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        self.connection.execute(query)

    def ping_me(self, discord_id):
        query = f"INSERT INTO deviant_usernames (discord_id, ping_me) VALUES ({discord_id}, true) " \
                f"ON CONFLICT (discord_id) DO UPDATE SET ping_me=excluded.ping_me"
        self.connection.execute(query)

    def fetch_da_username(self, discord_id):
        query = f"Select deviant_username from deviant_usernames where discord_id = {discord_id}"
        result = self.connection.execute(query).fetchone()
        if result:
            query_results = "".join(result)
            return query_results
        return None

    def fetch_discord_id(self, username):
        query = f"Select discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' " \
                f"and ping_me = true"
        result = self.connection.execute(query).fetchone()
        if result:
            return result[0]
        return None

    @staticmethod
    def convert_cache_to_result(response):
        results = []
        for row in response.fetchall():
            results.append(row._mapping)
        return results

    def add_coins(self, discord_id, username):
        # get discord_id for username, if exists, make sure no cheaters
        if username:
            query = f""" SELECT discord_id from deviant_usernames where lower(deviant_username) = '{username.lower()}' 
                    """
            result = self.connection.execute(query)
            possible_id = result.fetchone()
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
        result = self.connection.execute(query)
        coins = result.fetchone()
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
        result = self.connection.execute(query).fetchone()
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
