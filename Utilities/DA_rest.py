from collections import defaultdict

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

    def fetch_user_gallery(self, username, version, offset=0, display_num=24):
        response = self.fetch_entire_user_gallery(username, version, display_num)
        return response[offset:display_num]

    @staticmethod
    def _filter_api_image_results(results):
        nl = '\n'
        return [{'deviationid': result['deviationid'], 'url': result['url'], 'src_image': result['content']['src'] if
                'content' in result.keys() else "None", 'src_snippet': result['text_content']['excerpt'][:1024]
                 .replace("'", "''").replace("<br />", nl) if 'text_content' in result.keys() else "None", 'is_mature':
                 result['is_mature'],
                 'stats': result['stats'], 'published_time': result['published_time'], 'title': result['title']} for
                result in results]

    @staticmethod
    def _convert_cache_to_result(response):
        results = []
        for row in response.fetchall():
            results.append(row._mapping)
        return results

    def fetch_user_popular(self, username, version, display_num=24):
        deviant_row_id = self._fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self._user_last_cache_update(username):
            self.fetch_entire_user_gallery(username, version)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
                order by favs desc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self._convert_cache_to_result(response)

    def fetch_user_old(self, username, version, display_num=24):
        deviant_row_id = self._fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self._user_last_cache_update(username):
            self.fetch_entire_user_gallery(username, version)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
                order by date_created asc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self._convert_cache_to_result(response)

    def fetch_entire_user_gallery(self, username, version, display_num=24):
        if self._user_last_cache_update(username):
            self._gallery_fetch_helper(username)
            deviant_row_id = self._fetch_user_row_id(username)
            # use cache
            query = f""" SELECT * from deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
            order by date_created desc """
            response = self.connection.execute(query)
            return self._convert_cache_to_result(response)

        # initial fetch

        response = self._gallery_fetch_helper(username)
        results = response['results']

        # build the rest of the gallery
        while response['has_more']:
            next_offset = response['next_offset']
            response = self._gallery_fetch_helper(username, next_offset, display_num)
            results += response['results']
        in_store = self._fetch_user_row_id(username)
        if in_store:
            self._add_user_gallery_to_cache(results, username)
        return self._filter_api_image_results(results)

    def fetch_daily_deviations(self):
        self._validate_token()
        response = requests.get(f"{API_URL}browse/dailydeviations?access_token={self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return self._filter_api_image_results(results)

    def _gallery_fetch_helper(self, username, offset=0, display_num=24):
        self._validate_token()
        # only do this to check if the cache has to be updated...
        response = requests.get(
            f"{API_URL}gallery/all?username={username}&limit=24&access_token="
            f"{self.access_token}&offset={offset}")
        decoded_content = json.loads(response.content.decode("UTF-8"))
        # check if existing cache should be updated, compare last updated to published_date
        if self._user_last_cache_update(username):
            update_results = []
            for date in decoded_content['results']:
                if datetime.date.fromtimestamp(int(date['published_time'])) >= self._user_last_cache_update(username):
                    update_results.append(date)
                else:
                    break  # don't keep going if you don't have to
            if update_results:
                self._add_user_gallery_to_cache(update_results, username)
        return decoded_content

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
        return self._rss_image_helper(images, num)

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

        return self._rss_image_helper(images, num)

    def _validate_token(self):
        response = requests.get(f"{API_URL}placebo?access_token={self.access_token}")
        if 'success' not in json.loads(response.content)["status"]:
            self.access_token = self._acquire_access_token()

    def _user_last_cache_update(self, username):
        user_id_row = self._fetch_user_row_id(username)
        if not user_id_row:
            return None
        query = f"""SELECT last_updated from cache_updated_date where deviant_row_id = {user_id_row}"""
        result = self.connection.execute(query)
        return result.fetchone()[0]

    def _add_user_gallery_to_cache(self, results, username):
        # this only gets called if the user doesn't exist in the cache yet
        user_id = self._fetch_user_row_id(username)
        results, ext_data = self._fetch_metadata(results)
        combined_data_dict = self._create_user_deviation_dict(results, ext_data)
        self._initial_add_to_cache(combined_data_dict, user_id)

    def _fetch_user_row_id(self, username):
        query = f"Select id from deviant_usernames where lower(deviant_username) = '{username.lower()}' "
        result = self.connection.execute(query).fetchone()
        if result:
            return result[0]
        return None

    def _fetch_metadata(self, results):
        uuid_list = [result['deviationid'] for result in results]
        # not ready to support lit yet.
        ext_data = self._filter_api_image_results(results)
        # gotta chunk it...
        response = []
        for chunk in range(0, len(uuid_list), 50):
            deviation_ids = "&".join([f"""deviationids%5B%5D='{id}'""" for id in uuid_list[chunk:chunk+49]])
            response += json.loads(requests.get(f"{API_URL}deviation/metadata?{deviation_ids}&"
                                                f"access_token={self.access_token}").content)['metadata']
        return response, ext_data

    @staticmethod
    def _create_user_deviation_dict(results, ext_data):
        combined_dict = defaultdict(dict)
        for item in results + ext_data:
            combined_dict[item['deviationid']].update(item)
        return list(combined_dict.values())

    def _initial_add_to_cache(self, results, row_id):
        nl = '\n'
        values_list = ", ".join([f""" ({row_id}, '{result['url']}','{result['src_image']}','{result['src_snippet']
                                .replace("<br />", nl)}', '{result['title'].replace("'", "")}', 
                                {result['stats']['favourites']}, '{', '.join([tag['tag_name'] for tag in 
                                                                              result['tags']]) if 'tags' in 
                                                                                                  result.keys() else 
                                None}', to_date('{datetime.datetime.fromtimestamp(int(result['published_time']))
                                .strftime('%Y%m%d')}', 'YYYYMMDD'), '{result['is_mature']}') """ for result in results])
        query = f"INSERT INTO deviations (deviant_user_row, url, src_image, src_snippet, title, favs, tags, " \
                f"date_created, is_mature) VALUES {values_list} ON CONFLICT (url) DO NOTHING"
        self.connection.execute(query)
        query = f"INSERT INTO cache_updated_date (deviant_row_id) VALUES ({row_id}) ON CONFLICT " \
                f"(deviant_row_id) DO UPDATE SET last_updated = now()"
        self.connection.execute(query)

    def _rss_image_helper(self, images, num):
        random.shuffle(images)
        return_images = images[:10]
        results = list(filter(lambda image: 'media_content' in image.keys() and image['media_content'][-1]['medium']
                                            == 'image' and image["rating"] == 'nonadult',
                              return_images))
        string_users, filtered_users, filtered_links = self._generate_links(results, num)
        return results, string_users, filtered_links, filtered_users

    @staticmethod
    def _generate_links(results, num):
        filtered_users = list({image['media_credit'][0]['content'] for image in results[:num]})
        filtered_links = list({f"[{image['title']}]({image['links'][-1]['href']})" for image in results[:num]})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return string_users, filtered_users, filtered_links
