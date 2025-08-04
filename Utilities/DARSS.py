import feedparser
import random

from dotenv import load_dotenv

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
            image_feed = feedparser.parse(f"{APIURL.random_rss}{user}+sort%3Atime+meta%3Aall")
            if image_feed.status != 200:
                print(image_feed.feed.summary, flush=True)
                raise Exception(f"URL currently not accessible.")
            results = self._shuffle_and_apply_filter(image_feed.entries)
            if len(results):
                if len(images) < num:
                    images.append(results[0])
                else:
                    return self._rss_image_helper(images, 24)
        return None

    @staticmethod
    def _fetch_all_user_faves_helper(username, offset=0, mature="false"):
        response = feedparser.parse(
            f"{APIURL.fav_rss}{username}&offset={offset}&include_mature={mature}")

        if response.status != 200:
            print(response.feed.summary, flush=True)
            raise Exception(f"URL currently not accessible.")
        return response

    def get_user_favs(self, username, offset=0, num=24, randomized=False, mature="false"):
        # initial fetch
        # revisit this...
        response = self._fetch_all_user_faves_helper(username, offset, mature)
        images = response.entries
        if randomized:
            while len(response['feed']['links']) >= 1 and len(images) < 100:
                url = response['feed']['links'][-1]['href']
                response = feedparser.parse(url)
                images += response.entries
        results = self._shuffle_and_apply_filter(images, randomized)
        return self._rss_image_helper(results, num)

    def _rss_image_helper(self, results, num):
        string_links = self._generate_links(results, num)
        return results[:num], string_links

    @staticmethod
    def _shuffle_and_apply_filter(images, randomized=False):
        # commenting for now, but will only use for rnd later.
        if randomized:
            random.shuffle(images)

        nl = '\n'
        return [{'deviationid': result['id'],
                 'url':
                     result['link'],
                 'src_image':
                     result['media_thumbnail'][-1]['url']
                     if 'medium' in result['media_content'][-1].keys() and 'image' in result['media_content'][-1][
                         'medium']
                     else "None",
                 'src_snippet':
                     result['summary'][:1024].replace("'", "''").replace("<br />", nl)
                     if 'medium' in result['media_content'][-1].keys() and 'image' not in result['media_content'][-1][
                         'medium']
                     else "None",
                 'is_mature':
                     False if 'nonadult' in result['rating'] else True,
                 'published_time':
                     result['published'],
                 'title':
                     f"{result['title']}",
                 'author':
                     result['media_credit'][0]['content']}
                for result in images if
                (True if result['summary'] != '' and 'media_content' in result.keys() else False)]

    @staticmethod
    def _generate_links(results, at_least):
        filtered_links = [f"[[{index}](<{image['url']}>)] {{{image['author']}}}"
                          for index, image in enumerate(results[:at_least], start=1)]
        return ", ".join(filtered_links)
