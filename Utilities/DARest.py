from collections import defaultdict
from Utilities.DatabaseActions import DatabaseActions
from Utilities.DARSS import DARSS
import requests
import sqlalchemy
import json
import random
import os
import datetime
from dotenv import load_dotenv


AUTH_URL = "https://www.deviantart.com/oauth2/token?grant_type=client_credentials&"
API_URL = "https://www.deviantart.com/api/v1/oauth2/"


class DARest:
    def __init__(self):
        load_dotenv()
        self.secret = os.getenv("DA_SECRET")
        self.client = os.getenv("DA_CLIENT")
        self.db_actions = DatabaseActions()
        self.pg_secret = os.getenv("PG_SECRET")
        self.da_rss = DARSS()
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
        if self.db_actions.user_last_cache_update(username):
            response = self.fetch_entire_user_gallery(username, version)
        else:
            response = self._filter_api_image_results(
                self._gallery_fetch_helper(username, offset)['results'])
        return response[offset:display_num]

    @staticmethod
    def _filter_api_image_results(results):
        nl = '\n'
        return [{'deviationid': result['deviationid'], 'url': result['url'], 'src_image': result['content']['src'] if
                 'content' in result.keys() else result['preview']['src'] if 'preview' in result.keys() else "None",
                 'src_snippet': result['text_content']['excerpt'][:1024].replace("'", "''").replace("<br />", nl) if
                 'text_content' in result.keys() else "None", 'is_mature': result['is_mature'],
                 'stats': result['stats'], 'published_time': result['published_time'], 'title': result['title'],
                 'author': result['author']['username']} for
                result in results]

    def fetch_user_popular(self, username, version, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username, version)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
                order by favs desc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)

    def fetch_user_old(self, username, version, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username, version)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
                order by date_created asc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)

    def get_user_devs_by_tag(self, username, version, tags, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username, version)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' and
                        position('{tags}' in tags) > 0
                        order by date_created desc 
                        limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)

    def fetch_entire_user_gallery(self, username, version):
        if self.db_actions.user_last_cache_update(username):
            self._gallery_fetch_helper(username)
            deviant_row_id = self.db_actions.fetch_user_row_id(username)
            # use cache
            query = f""" SELECT * from deviations where deviant_user_row = {deviant_row_id} and {version} != 'None' 
            order by date_created desc """
            response = self.connection.execute(query)
            return self.db_actions.convert_cache_to_result(response)

        # initial fetch

        response = self._gallery_fetch_helper(username)
        results = response['results']

        # build the rest of the gallery
        while response['has_more']:
            next_offset = response['next_offset']
            response = self._gallery_fetch_helper(username, next_offset)
            results += response['results']
        in_store = self.db_actions.fetch_user_row_id(username)
        if in_store:
            self._add_user_gallery_to_cache(results, username)
        return self._filter_api_image_results(results)

    def fetch_daily_deviations(self):
        self._validate_token()
        response = requests.get(f"{API_URL}browse/dailydeviations?access_token={self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return self._filter_api_image_results(results)

    def _gallery_fetch_helper(self, username, offset=0):
        self._validate_token()
        # only do this to check if the cache has to be updated...
        response = requests.get(
            f"{API_URL}gallery/all?username={username}&limit=24&access_token="
            f"{self.access_token}&offset={offset}")
        decoded_content = json.loads(response.content.decode("UTF-8"))
        # check if existing cache should be updated, compare last updated to published_date
        last_updated = self.db_actions.user_last_cache_update(username)
        if last_updated:
            update_results = []
            needs_update = (datetime.date.today() - last_updated) >= datetime.timedelta(days=7)
            for date in decoded_content['results']:
                if datetime.date.fromtimestamp(int(date['published_time'])) >= last_updated or needs_update:
                    update_results.append(date)
                else:
                    break  # don't keep going if you don't have to
            if update_results:
                self._add_user_gallery_to_cache(update_results, username)
        return decoded_content

    def get_user_favs_by_collection(self, username, num, collection):
        return self.get_favorite_collection(username, "src_image", collection)

    def get_user_gallery(self, username, version, gallery):
        url = f"{API_URL}gallery/folders?access_token={self.access_token}&username={username}&calculate_size=true&" \
              f"ext_preload=true&filter_empty_folder=true&with_session=false"
        # add the gallery name to cache for quicker pulls next time
        response = requests.get(url)
        results = json.loads(response.content)['results']
        deviations = [result['deviations'] for result in results if result['name'] == gallery]
        if len(deviations):
            return [types for types in self._filter_api_image_results(deviations[0]) if types[version] != 'None']
        return deviations

    def get_favorite_collection(self, username, version, collection):
        url = f"{API_URL}collections/folders?access_token={self.access_token}&username={username}&calculate_size=" \
              f"true&ext_preload=true&filter_empty_folder=true&with_session=false"
        response = requests.get(url)
        results = json.loads(response.content)['results']
        favorites = [result['deviations'] for result in results if result['name'] == collection]
        if len(favorites):
            results = [types for types in self._filter_api_image_results(favorites[0]) if types[version] != 'None']
            usernames, _, links = self._generate_links(results)
            return results, usernames, links
        return None

    @staticmethod
    def _generate_links(results):
        filtered_users = list({image['author'] for image in results})
        filtered_links = list({f"[{image['title']}]({image['url']})" for image in results})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return string_users, filtered_users, filtered_links

    def _validate_token(self):
        response = requests.get(f"{API_URL}placebo?access_token={self.access_token}")
        if 'success' not in json.loads(response.content)["status"]:
            self.access_token = self._acquire_access_token()

    def _add_user_gallery_to_cache(self, results, username):
        # this only gets called if the user doesn't exist in the cache yet
        user_id = self.db_actions.fetch_user_row_id(username)
        results, ext_data = self._fetch_metadata(results)
        combined_data_dict = self._create_user_deviation_dict(results, ext_data)
        self.db_actions.initial_add_to_cache(combined_data_dict, user_id)

    def _fetch_metadata(self, results):
        uuid_list = [result['deviationid'] for result in results]
        # not ready to support lit yet.
        ext_data = self._filter_api_image_results(results)
        # gotta chunk it...
        response = []
        for chunk in range(0, len(uuid_list), 50):
            deviation_ids = "&".join([f"""deviationids%5B%5D='{dev_id}'""" for dev_id in uuid_list[chunk:chunk+49]])
            response += json.loads(requests.get(f"{API_URL}deviation/metadata?{deviation_ids}&"
                                                f"access_token={self.access_token}").content)['metadata']
        return response, ext_data

    @staticmethod
    def _create_user_deviation_dict(results, ext_data):
        combined_dict = defaultdict(dict)
        for item in results + ext_data:
            combined_dict[item['deviationid']].update(item)
        return list(combined_dict.values())
