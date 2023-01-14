import requests
import sqlalchemy
import json
import random
import os
from dotenv import load_dotenv

AUTH_URL = "https://www.deviantart.com/oauth2/token?grant_type=client_credentials&"
API_URL = "https://www.deviantart.com/api/v1/oauth2/"


class DARest:
    def __init__(self):
        load_dotenv()
        self.secret = os.getenv("DA_SECRET")
        self.client = os.getenv("DA_CLIENT")
        self.pg_secret = os.getenv("PG_SECRET")
        random.seed(42)

        engine = sqlalchemy.create_engine(
            f"postgresql://postgres:{self.pg_secret}@containers-us-west-85.railway.app:7965/railway")
        self.connection = engine.connect()
        self.access_token = self._acquire_access_token()

    def _acquire_access_token(self):
        response = requests.get(
            f"{AUTH_URL}client_id={self.client}&client_secret={self.secret}")

        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)['access_token']

    def fetch_user_gallery(self, username, offset=0):
        response = self._gallery_fetch_helper(username, offset)
        results = response['results']
        return results

    def fetch_entire_user_gallery(self, username):
        # initial fetch
        response = self._gallery_fetch_helper(username)
        results = response['results']

        # build the rest of the gallery
        while response['has_more']:
            next_offset = response['next_offset']
            response = self._gallery_fetch_helper(username, offset=next_offset)
            results += response['results']
        return results

    def fetch_daily_deviations(self):
        self._validate_token()
        response = requests.get(f"{API_URL}browse/dailydeviations?access_token={self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return results

    def _gallery_fetch_helper(self, username, offset=0):
        self._validate_token()
        response = requests.get(
            f"{API_URL}gallery/all?username={username}&limit=24&access_token="
            f"{self.access_token}&offset={offset}")
        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)

    def store_da_name(self, discord_id, username):
        query = f"INSERT INTO deviant_usernames (discord_id, deviant_username) VALUES ({discord_id}, '{username}') " \
                f"ON CONFLICT (discord_id) DO UPDATE SET deviant_username= excluded.deviant_username"
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

    def _fetch_da_usernames(self, num):
        query = f"Select deviant_username from deviant_usernames"
        query_results = ["".join(name_tuple) for name_tuple in self.connection.execute(query)]
        random.shuffle(query_results)
        return query_results[:num]

    def get_random_images(self, num):
        random_users = self._fetch_da_usernames(num)
        images = []
        for user in random_users:
            images += self.fetch_entire_user_gallery(user)
        random.shuffle(images)
        return_images = images[:10]
        filtered_users = list({image['author']['username'] for image in return_images})
        filtered_links = list({f"[{image['title']}]({image['url']})" for image in return_images})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return return_images, string_users, filtered_links

    def _fetch_user_faves_folder_id(self, username):
        self._validate_token()
        response = requests.get(
            f"{API_URL}collections/folders?username={username}&limit=24&mature_content=false&access_token="
            f"{self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)['results'][0]['folderid']

    def _fetch_all_user_faves_helper(self, username, folder_id, offset=0):
        self._validate_token()
        response = requests.get(
            f"{API_URL}collections/{folder_id}?username={username}&limit=24&mature_content=false&access_token="
            f"{self.access_token}&offset={offset}")
        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)

    def get_user_favs(self, username):
        # initial fetch
        folder_id = self._fetch_user_faves_folder_id(username)
        response = self._fetch_all_user_faves_helper(username, folder_id)
        results = response['results']

        # build the rest of the gallery
        while response['has_more'] and response['next_offset'] < 1000:
            next_offset = response['next_offset']
            response = self._fetch_all_user_faves_helper(username, folder_id, offset=next_offset)
            results += response['results']
        return results

    def _validate_token(self):
        response = requests.get(f"{API_URL}placebo?access_token={self.access_token}")
        if 'success' not in json.loads(response.content)["status"]:
            self.access_token = self._acquire_access_token()
