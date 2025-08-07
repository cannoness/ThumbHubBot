import feedparser

from dotenv import load_dotenv

from Utilities.utilities import helpers
from thumbhubbot import APIURL
from Utilities.DatabaseActions import DatabaseActions


class DARSS:
    def __init__(self):
        load_dotenv()
        self.db_actions = DatabaseActions()

    def get_random_images(self, num):
        random_users = self.db_actions.fetch_da_usernames(10)
        images = []
        for user in random_users:
            address = f"{APIURL.random_rss}{user}+sort%3Atime+meta%3Aall"
            image_feed = feedparser.parse(address)
            if image_feed.status != 200:
                print(image_feed.feed.summary, flush=True)
                raise Exception(f"URL currently not accessible.")
            results = helpers.format_rss_results_for_store(image_feed.entries)
            if len(results):
                if len(images) < num:
                    images.append(results[0])
                else:
                    return self._rss_image_helper(images, 24)
        return None

    @staticmethod
    def _fetch_all_user_faves_helper(username, offset=0, mature="false"):
        response = feedparser.parse(f"{APIURL.fav_rss}{username}&offset={offset}&include_mature={mature}")
        if response.status != 200:
            print(response.feed.summary, flush=True)
            raise Exception(f"Favs URL currently not accessible for this user.")
        return response.entries

    def get_user_favs(self, username, offset=0, num=24, mature="false"):
        images = self._fetch_all_user_faves_helper(username, offset, mature)
        results = helpers.format_rss_results_for_store(images)
        return self._rss_image_helper(results, num)

    def randomized_user_favs(self, username, offset=0, num=24, mature="false"):
        images = []
        response = feedparser.parse(f"{APIURL.fav_rss}{username}&offset={offset}&include_mature={mature}")
        while len(images) < 100:
            images += response.entries
            if len(response['feed']['links']) == 0:
                break
            url = response['feed']['links'][-1]['href']
            response = feedparser.parse(url)
        shuffed_images = helpers.shuffle_list_of_dicts(images)
        results = helpers.format_rss_results_for_store(shuffed_images)
        return self._rss_image_helper(results, num)

    def _rss_image_helper(self, results, num):
        string_links = self._generate_links(results, num)
        return results[:num], string_links

    @staticmethod
    def _generate_links(results, at_least):
        filtered_links = [f"[[{index}](<{image['url']}>)] {{{image['author']}}}"
                          for index, image in enumerate(results[:at_least], start=1)]
        return ", ".join(filtered_links)
