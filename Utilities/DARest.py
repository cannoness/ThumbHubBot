import requests
import json
import os

from collections import defaultdict
from dotenv import load_dotenv

from Utilities.DatabaseActions import DatabaseActions
from Utilities.utilities import helpers
from thumbhubbot import APIURL, CONFIG


class DARest:
    def __init__(self):
        load_dotenv()
        self.secret = os.getenv("DA_SECRET")  # TODO: move into secrets manager
        self.client = os.getenv("DA_CLIENT")  # TODO: move into secrets manager
        self.db_actions = DatabaseActions
        self.db_inst = self.db_actions()
        self.access_token = self._acquire_access_token()
        self.topics = None

    def _acquire_access_token(self):
        response = requests.get(
            f"{APIURL.auth}client_id={self.client}&client_secret={self.secret}",
            timeout=CONFIG.global_timeout
        )
        if response.status_code != 200:
            print(response.content)
            raise Exception(f"CANNOT CONNECT: {response.content}")
        decoded_content = response.json()
        return decoded_content['access_token']

    def check_and_update_gallery(self, username):
        in_store = self.db_actions.fetch_hubber_row_id(username)
        one_result = self._gallery_fetch_helper(username, 0, 1)['results']
        should_update = self.db_actions.hubber_has_new_creations(username, one_result)
        if in_store and should_update:
            self.fetch_entire_user_gallery(username)

    def fetch_user_gallery(self, username, offset=0, display_num=10):
        self._validate_token()
        self.check_and_update_gallery(username)

        response = helpers.format_api_image_results(
            self._gallery_fetch_helper(username, offset, display_num)['results']
        )
        return response[offset:display_num + offset]

    def _list_topics(self):
        response = requests.get(f"{APIURL.api}browse/topics?access_token={self.access_token}",
                                timeout=CONFIG.global_timeout)
        next_set = json.loads(response.content.decode("UTF-8"))
        topic_dict = defaultdict(str)
        has_more = next_set['has_more']
        cursor = next_set["next_cursor"]
        # there are only 30 offsets, so we only need to do this once and record the result.
        while has_more:
            for result in next_set['results']:
                topic_dict[result['name'].lower()] = result['canonical_name']
            has_more = next_set['has_more']
            new_response = requests.get(f"{APIURL.api}browse/topics?access_token={self.access_token}&cursor={cursor}",
                                        timeout=CONFIG.global_timeout)
            next_set = json.loads(new_response.content.decode("UTF-8"))
            cursor = next_set['next_cursor'] if 'next_cursor' in next_set.keys() else None
        self.topics = topic_dict

    def fetch_user_popular(self, username, offset=0, display_num=24):
        deviant_row_id = self.db_actions.fetch_hubber_row_id(username)
        if not deviant_row_id:
            return None
        self.check_and_update_gallery(username)
        response = self.db_actions.fetch_pop_from_cache(deviant_row_id, display_num)
        return self.db_actions.convert_cache_to_result(response)[offset:display_num + offset]

    def fetch_user_old(self, username, offset=0, display_num=24):
        deviant_row_id = self.db_actions.fetch_hubber_row_id(username)
        if not deviant_row_id:
            return None
        self.check_and_update_gallery(username)
        return self.db_inst.fetch_old_from_cache(deviant_row_id, display_num, offset)

    def fetch_user_random(self, username):
        self.check_and_update_gallery(username)
        return self.db_inst.get_random_creations_by_hubber(username)

    def get_user_devs_by_tag(self, username, tags, offset=0, display_num=24):
        self.check_and_update_gallery(username)
        return self.db_inst.fetch_user_devs_by_tag(username, display_num, offset, tags)

    def fetch_entire_user_gallery(self, username):
        response = self._gallery_fetch_helper(username)
        results = response['results']

        # build the rest of the gallery
        while response['has_more']:
            next_offset = response['next_offset']
            response = self._gallery_fetch_helper(username, next_offset)
            results += response['results']

        self._add_user_gallery_to_cache(results, username)
        return helpers.format_api_image_results(results)

    def fetch_daily_deviations(self):
        self._validate_token()
        response = requests.get(
            f"{APIURL.api}browse/dailydeviations?access_token={self.access_token}", timeout=CONFIG.global_timeout
        )
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return helpers.format_api_image_results(results)

    def _remove_ai_from_topic_results(self, topic, offset=0, use_tag=None):
        response = requests.get(f"{APIURL.api}browse/topic?access_token={self.access_token}&"
                                f"topic={topic}&offset={offset}", timeout=CONFIG.global_timeout) if not use_tag else \
            requests.get(f"{APIURL.api}browse/tags?access_token={self.access_token}&tag={use_tag}",
                         timeout=CONFIG.global_timeout)

        decoded_content = response.content.decode("UTF-8")
        content = json.loads(decoded_content)
        results = content['results']
        if not response.ok or not len(results):
            return None, None, False
        return results, content['next_offset'], content['has_more']

    def get_topic(self, topic, offset=0):
        self._validate_token()
        if not self.topics:
            self._list_topics()

        not_ai = []
        canonical_name = self.topics[topic.lower()] if topic.lower() in self.topics.keys() else \
            topic.lower().replace(" ", "-")

        has_more = True
        tag = None
        results = None
        while len(not_ai) <= 6 and has_more:
            results, out_offset, has_more = self._remove_ai_from_topic_results(canonical_name, offset)
            if not results:
                tag = topic.replace(" ", "")
                results, offset, has_more = self._remove_ai_from_topic_results(canonical_name, offset, tag)
                if not results:
                    raise Exception(f"No results for topic {topic}")
            # check to see if what the API spat out is AI or not.
            for result in results:
                if result['author']['type'] == "premium":
                    continue
                not_ai.append(result)
            if not has_more:
                break
            offset = out_offset

        if canonical_name not in self.topics.values():
            self.topics[topic.lower()] = canonical_name
        return [None, helpers.format_api_image_results(results)] if tag else helpers.format_api_image_results(results)

    def _gallery_fetch_helper(self, username, offset=0, display_num=24):
        self._validate_token()
        response = requests.get(
            f"{APIURL.api}gallery/all?username={username}&limit=24&access_token="
            f"{self.access_token}&offset={offset}&display_num={display_num}", timeout=CONFIG.global_timeout)
        decoded_content = json.loads(response.content.decode("UTF-8"))
        return decoded_content

    def get_user_favs_by_collection(self, username, collection, offset=0, limit=24, mature="false"):
        return self.get_favorite_collection(username, collection, offset, limit, mature)

    def get_user_gallery(self, username, gallery_name, offset=0, limit=24):
        # TODO: get more than the preview images. check for subfolders
        self._validate_token()
        self.check_and_update_gallery(username)

        url_params = "&calculate_size=true&ext_preload=false&filter_empty_folder=true&limit=25&with_session=false"
        url = f"{APIURL.api}gallery/folders?access_token={self.access_token}&username={username}{url_params}"

        # add the gallery name to cache for quicker pulls next time
        response = requests.get(url, timeout=CONFIG.global_timeout)
        results = json.loads(response.content)['results']
        folder_id = [result['folderid'] for result in results if result['name'].lower() == gallery_name.lower()][0]
        gallery_url = f"{APIURL.api}gallery/{folder_id}?access_token={self.access_token}&username={username}&" \
                      f"limit={limit}&offset={offset}&with_session=false&mature_content=true"
        response = requests.get(gallery_url, timeout=CONFIG.global_timeout)
        deviations = json.loads(response.content)['results']
        if len(deviations):
            return helpers.format_api_image_results(deviations)
        return deviations

    def get_favorite_collection(self, username, collection_name, offset=0, limit=24, mature="false"):
        # TODO: get more than the preview images. check for subfolders
        self._validate_token()
        self.check_and_update_gallery(username)

        query_string = "calculate_size=true&ext_preload=true&limit=25&filter_empty_folder=true&with_session=false"
        url = f"{APIURL.api}collections/folders?access_token={self.access_token}&username={username}&{query_string}"

        response = requests.get(url, timeout=CONFIG.global_timeout)
        results = json.loads(response.content)['results']
        folder_id = [result['folderid'] for result in results if result['name'].lower() == collection_name.lower()][0]
        collection_url = f"{APIURL.api}collections/{folder_id}?access_token={self.access_token}&username={username}&" \
                         f"limit={limit}&offset={offset}&with_session=false&mature_content={mature}"
        response = requests.get(collection_url, timeout=CONFIG.global_timeout)
        if not response.ok:
            return None
        favorites = json.loads(response.content)['results']
        if len(favorites):
            results = helpers.format_api_image_results(favorites)
            links = self._generate_links(results)
            return results, links
        return None

    @staticmethod
    def _generate_links(results):
        filtered_links = [f"[[{index + 1}]({image['url']})] {{{image['author']}}}"
                          for index, image in enumerate(results)]
        return ", ".join(filtered_links)

    def _validate_token(self):
        response = requests.get(
            f"{APIURL.api}placebo?access_token={self.access_token}", timeout=CONFIG.global_timeout
        )
        if 'success' not in json.loads(response.content)["status"]:
            self.access_token = self._acquire_access_token()

    def _add_user_gallery_to_cache(self, results, row_id):
        # this only gets called if the user doesn't exist in the cache yet
        user_id = self.db_actions.fetch_hubber_row_id(row_id)
        results, ext_data = self._fetch_metadata(results)
        combined_data_dict = self._create_user_deviation_dict(results, ext_data)
        self.db_actions.initial_add_to_cache(combined_data_dict, user_id)

    def _fetch_metadata(self, results):
        uuid_list = [result['deviationid'] for result in results]
        ext_data = helpers.format_api_image_results(results)
        response = []
        for chunk in range(0, len(uuid_list), 50):
            deviation_ids = "&".join([f"""deviationids%5B%5D='{dev_id}'""" for dev_id in uuid_list[chunk:chunk + 49]])
            response += json.loads(requests.get(f"{APIURL.api}deviation/metadata?{deviation_ids}&"
                                                f"access_token={self.access_token}",
                                                timeout=CONFIG.global_timeout).content)['metadata']
        return response, ext_data

    @staticmethod
    def _create_user_deviation_dict(results, ext_data):
        combined_dict = defaultdict(dict)
        for item in results + ext_data:
            combined_dict[item['deviationid']].update(item)
        return list(combined_dict.values())
