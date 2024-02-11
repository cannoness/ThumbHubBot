from Utilities.DatabaseActions import DatabaseActions
import random
from dotenv import load_dotenv
import feedparser


RANDOM_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=by%3A"
FAV_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=favby%3A"


class DARSS:
    def __init__(self):
        load_dotenv()
        self.db_actions = DatabaseActions()

    def get_random_images(self, num):
        random_users = self.db_actions.fetch_da_usernames(10)
        images = []
        for user in random_users:
            image_feed = feedparser.parse(f"{RANDOM_RSS_URL}{user}+sort%3Atime+meta%3Aall")
            if image_feed.status != 200:
                print(image_feed.feed.summary, flush=True)
                raise Exception(f"URL currently not accessible.")
            results = image_feed.entries  # self._shuffle_and_apply_filter(image_feed.entries)
            if len(results):
                if len(images) < num:
                    images.append(results[0])
                else:
                    return self._rss_image_helper(images, num+8)
        return None

    @staticmethod
    def _fetch_all_user_faves_helper(username, offset=0):
        response = feedparser.parse(
            f"{FAV_RSS_URL}{username}&offset={offset}")

        if response.status != 200:
            print(response.feed.summary, flush=True)
            raise Exception(f"URL currently not accessible.")
        return response

    def get_user_favs(self, username, offset=0, num=24, randomized=False):
        # initial fetch
        # revisit this...
        response = self._fetch_all_user_faves_helper(username, offset)
        images = response.entries
        if randomized:
            while len(response['feed']['links']) >= 1 and len(images) < 100:
                url = response['feed']['links'][-1]['href']
                response = feedparser.parse(url)
                images += response.entries

        return self._rss_image_helper(images, num, randomized)

    def _rss_image_helper(self, images, num, randomized=False):
        results = self._shuffle_and_apply_filter(images, randomized)
        string_links = self._generate_links(results, num)
        return results[:num], string_links

    @staticmethod
    def _shuffle_and_apply_filter(images, randomized=False):
        # commenting for now, but will only use for rnd later.
        if randomized:
            random.shuffle(images)
        results = list(filter(lambda image: 'media_content' in image.keys() and 'medium' in
                                            image['media_content'][-1].keys() and
                                            image['media_content'][-1]['medium'] == 'image' and
                                            image["rating"] == 'nonadult', images))

        nl = '\n'
        return [{'deviationid': result['id'],
                 'url':
                     result['link'],
                 'src_image':
                     result['media_thumbnail'][-1]['url']
                     if 'image' in result['media_content'][-1]['medium']
                     else "None",
                 'src_snippet':
                     result['summary'][:1024].replace("'", "''").replace("<br />", nl)
                     if 'image' not in result['media_content'][-1]['medium']
                     else "None",
                 'is_mature':
                     False if 'nonadult' in result['rating'] else True,
                 'published_time':
                     result['published'],
                 'title':
                     result['title'],
                 'author':
                     result['media_credit'][0]['content']}
                for result in results if (True if result['summary'] != '' else False)]

    @staticmethod
    def _generate_links(results, at_least):
        filtered_links = [f"[[{index}]({image['url']})] {{{image['author']}}}"
                          for index, image in enumerate(results[:at_least], start=1)]
        return ", ".join(filtered_links)
