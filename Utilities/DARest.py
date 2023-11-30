from collections import defaultdict

from regex import regex

from Utilities.DatabaseActions import DatabaseActions
from Utilities.DARSS import DARSS
import requests
import sqlalchemy
import json
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
        self.da_rss = DARSS()

        self.pg_password = os.getenv("PGPASSWORD")
        self.pg_url = os.getenv("PGHOST")
        self.pg_user = os.getenv("PGUSER")
        self.pg_db = os.getenv("PGDATABASE")
        self.pg_port = os.getenv("PGPORT")

        engine = sqlalchemy.create_engine(
            f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_url}:{self.pg_port}/{self.pg_db}",
            pool_pre_ping=True)
        self.connection = engine.connect()
        self.access_token = self._acquire_access_token()
        self.topics = None

    def _acquire_access_token(self):
        response = requests.get(
            f"{AUTH_URL}client_id={self.client}&client_secret={self.secret}")

        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)['access_token']

    def fetch_user_gallery(self, username, offset=0, display_num=10):
        self._validate_token()
        if self.db_actions.user_last_cache_update(username):
            response = self.fetch_entire_user_gallery(username)
        else:
            display_num = 10
            response = self._filter_api_image_results(
                self._gallery_fetch_helper(username, offset, display_num)['results'])
        return response[offset:display_num + offset]

    def _list_topics(self):
        response = requests.get(f"{API_URL}browse/topics?access_token={self.access_token}")
        next_set = json.loads(response.content.decode("UTF-8"))
        topic_dict = defaultdict(str)
        has_more = next_set['has_more']
        cursor = next_set["next_cursor"]
        # there are only 30 offsets, so we only need to do this once and record the result.
        while has_more:
            for result in next_set['results']:
                topic_dict[result['name'].lower()] = result['canonical_name']
            has_more = next_set['has_more']
            new_response = requests.get(f"{API_URL}browse/topics?access_token={self.access_token}&cursor={cursor}")
            next_set = json.loads(new_response.content.decode("UTF-8"))
            cursor = next_set['next_cursor'] if 'next_cursor' in next_set.keys() else None
        self.topics = topic_dict

    @staticmethod
    def _filter_api_image_results(results):
        nl = '\n'
        return [{'deviationid': result['deviationid'],
                 'url':
                     result['url'],
                 'src_image':
                     result['preview']['src'] if 'preview' in result.keys()
                     else result['thumbs'][-1]['src'] if len(result['thumbs'])  # prefer thumb over content
                     else result['content']['src'] if 'content' in result.keys()
                     else "None",
                 'src_snippet':
                     result['text_content']['excerpt'][:1024].replace("'", "''").replace("<br />", nl)
                     if 'text_content' in result.keys()
                     else "None",
                 'is_mature':
                     result['is_mature'],
                 'stats':
                     result['stats'],
                 'published_time':
                     result['published_time'],
                 'title':
                     result['title'],
                 'author':
                     result['author']['username']}
                for result in results]

    def fetch_user_popular(self, username, offset=0, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id}  
                order by favs desc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)[offset:display_num + offset]

    def fetch_user_old(self, username, offset=0, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} 
                order by date_created asc 
                limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)[offset:display_num + offset]

    def get_user_devs_by_tag(self, username, tags, offset=0, display_num=24):
        deviant_row_id = self.db_actions.fetch_user_row_id(username)
        if not deviant_row_id:
            return None
        if not self.db_actions.user_last_cache_update(username):
            self.fetch_entire_user_gallery(username)
        # use cache
        query = f""" SELECT * FROM deviations where deviant_user_row = {deviant_row_id} and
                        position('{tags}' in tags) > 0
                        order by date_created desc 
                        limit {display_num} """
        response = self.connection.execute(query)
        return self.db_actions.convert_cache_to_result(response)[offset:display_num + offset]

    def fetch_entire_user_gallery(self, username):
        if self.db_actions.user_last_cache_update(username):
            self._gallery_fetch_helper(username)
            deviant_row_id = self.db_actions.fetch_user_row_id(username)
            # use cache
            query = f""" SELECT * from deviations where deviant_user_row = {deviant_row_id}  
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

    def get_topic(self, topic):
        self._validate_token()
        if not self.topics:
            self._list_topics()

        canonical_name = self.topics[topic.lower()] if topic.lower() in self.topics.keys() else None
        if not canonical_name:
            pattern = "(?b)(<" + topic + ">\w+){e<=5}"
            closest_topic = regex.search(pattern, ";".join(self.topics.keys()))[1]
            print("no topic with this name", self.topics, closest_topic)
            return None, closest_topic
        response = requests.get(f"{API_URL}browse/topic?access_token={self.access_token}&"
                                f"topic={self.topics[topic.lower()]}")
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return self._filter_api_image_results(results)

    def _gallery_fetch_helper(self, username, offset=0, display_num=24):
        self._validate_token()
        # only do this to check if the cache has to be updated...
        response = requests.get(
            f"{API_URL}gallery/all?username={username}&limit=24&access_token="
            f"{self.access_token}&offset={offset}&display_num={display_num}")
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

    def get_user_favs_by_collection(self, username, collection, offset=0, limit=24):
        return self.get_favorite_collection(username, collection, offset, limit)

    def get_user_gallery(self, username, gallery_name, offset=0, limit=24):
        self._validate_token()
        url = f"{API_URL}gallery/folders?access_token={self.access_token}&username={username}&calculate_size=true&" \
              f"ext_preload=false&filter_empty_folder=true&limit=25&with_session=false"
        # add the gallery name to cache for quicker pulls next time
        response = requests.get(url)
        results = json.loads(response.content)['results']
        folder_id = [result['folderid'] for result in results if result['name'].lower() == gallery_name.lower()][0]
        gallery_url = f"{API_URL}gallery/{folder_id}?access_token={self.access_token}&username={username}&" \
                      f"limit={limit}&offset={offset}&with_session=false&mature_content=true"
        response = requests.get(gallery_url)
        deviations = json.loads(response.content)['results']
        if len(deviations):
            return self._filter_api_image_results(deviations)
        return deviations

    def get_favorite_collection(self, username, collection_name, offset=0, limit=24):
        self._validate_token()
        url = f"{API_URL}collections/folders?access_token={self.access_token}&username={username}&calculate_size=" \
              f"true&ext_preload=true&limit=25&filter_empty_folder=true&with_session=false"
        response = requests.get(url)
        results = json.loads(response.content)['results']
        folder_id = [result['folderid'] for result in results if result['name'].lower() == collection_name.lower()][0]
        collection_url = f"{API_URL}collections/{folder_id}?access_token={self.access_token}&username={username}&" \
                         f"limit={limit}&offset={offset}&with_session=false"
        response = requests.get(collection_url)
        if not response.ok:
            print(response)
        favorites = json.loads(response.content)['results']
        if len(favorites):
            results = self._filter_api_image_results(favorites)
            links = self._generate_links(results)
            return results, links
        return None

    @staticmethod
    def _generate_links(results):
        filtered_links = [f"[[{index + 1}]({image['url']})] {{{image['author']}}}"
                          for index, image in enumerate(results)]
        return ", ".join(filtered_links)

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
            deviation_ids = "&".join([f"""deviationids%5B%5D='{dev_id}'""" for dev_id in uuid_list[chunk:chunk + 49]])
            response += json.loads(requests.get(f"{API_URL}deviation/metadata?{deviation_ids}&"
                                                f"access_token={self.access_token}").content)['metadata']
        return response, ext_data

    @staticmethod
    def _create_user_deviation_dict(results, ext_data):
        combined_dict = defaultdict(dict)
        for item in results + ext_data:
            combined_dict[item['deviationid']].update(item)
        return list(combined_dict.values())
