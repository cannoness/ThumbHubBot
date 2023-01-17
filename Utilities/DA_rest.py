import requests
import sqlalchemy
import json
import random
import os
import datetime
from dotenv import load_dotenv
import feedparser


AUTH_URL = "https://www.deviantart.com/oauth2/token?grant_type=client_credentials&"
API_URL = "https://www.deviantart.com/api/v1/oauth2/"
RANDOM_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=by%3A"
FAV_RSS_URL = "http://backend.deviantart.com/rss.xml?type=deviation&q=favby%3A"

class DARest:
    def __init__(self):
        load_dotenv()
        self.secret = os.getenv("DA_SECRET")
        self.client = os.getenv("DA_CLIENT")
        self.pg_secret = os.getenv("PG_SECRET")
        seed = os.getpid()+int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        random.seed(seed)

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
            images += feedparser.parse(f"{RANDOM_RSS_URL}{user}+sort%3Atime+meta%3Aall").entries
        random.shuffle(images)
        return_images = images[:10]
        results = list(filter(lambda image: 'media_content' in image.keys() and image["rating"] == 'nonadult',
                              return_images))
        filtered_users = list({image['media_credit'][0]['content'] for image in results[:num]})
        filtered_links = list({f"[{image['title']}]({image['links'][-1]['href']})" for image in results[:num]})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return results, string_users, filtered_links, filtered_users

    def _fetch_user_faves_folder_id(self, username):
        self._validate_token()
        response = requests.get(
            f"{API_URL}collections/folders?username={username}&limit=24&mature_content=false&access_token="
            f"{self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)['results'][0]['folderid']

    @staticmethod
    def _fetch_all_user_faves_helper(username, offset=0):
        response = feedparser.parse(
            f"{FAV_RSS_URL}{username}&offset={offset}")
        return response

    def get_user_favs(self, username, num):
        # initial fetch
        response = self._fetch_all_user_faves_helper(username)
        images = response.entries
        # build the rest of the gallery
        while len(response['feed']['links']) > 1 and len(images) < 1000:
            url = response['feed']['links'][2]['href']
            response = feedparser.parse(url)
            images += response.entries

        random.shuffle(images)
        return_images = images[:10]
        results = list(filter(lambda image: 'media_content' in image.keys() and image["rating"] == 'nonadult',
                              return_images))
        filtered_users = list({image['media_credit'][0]['content'] for image in results[:num]})
        filtered_links = list({f"[{image['title']}]({image['links'][-1]['href']})" for image in results[:num]})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return results, string_users, filtered_links, filtered_users

    def _validate_token(self):
        response = requests.get(f"{API_URL}placebo?access_token={self.access_token}")
        if 'success' not in json.loads(response.content)["status"]:
            self.access_token = self._acquire_access_token()
