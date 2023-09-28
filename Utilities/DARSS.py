from Utilities.DatabaseActions import DatabaseActions
import random
import os
import datetime
from dotenv import load_dotenv
import feedparser


RANDOM_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=by%3A"
FAV_RSS_URL = "https://backend.deviantart.com/rss.xml?type=deviation&q=favby%3A"


class DARSS:
    def __init__(self):
        load_dotenv()
        self.db_actions = DatabaseActions()
        seed = os.getpid()+int(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        random.seed(seed)

    def get_random_images(self, num):
        random_users = self.db_actions.fetch_da_usernames(10)
        images = []
        for user in random_users:
            image_feed = feedparser.parse(f"{RANDOM_RSS_URL}{user}+sort%3Atime+meta%3Aall")
            if image_feed.status != 200:
                raise Exception(f"URL currently not accessible. 403 errors are an issue with our host, not the bot: "
                                f"{image_feed.feed.summary}. User selected: {user}")
            results = self._shuffle_and_apply_filter(image_feed.entries)
            if len(results):
                if len(images) < num:
                    images.append(results[0])
                else:
                    return self._rss_image_helper(images, num)
        return None

    @staticmethod
    def _fetch_all_user_faves_helper(username, offset=0):
        response = feedparser.parse(
            f"{FAV_RSS_URL}{username}&offset={offset}")

        if response.status != 200:
            raise Exception(f"URL currently not accessible. 403 errors are an issue with our host, not the bot: "
                            f"{response.feed.summary}. User RSS attempted: {username}. Defaulting to use cache.")
        return response

    def get_user_favs(self, username, num):
        # initial fetch
        response = self._fetch_all_user_faves_helper(username)
        images = response.entries
        # fetch more, if they want more than 100 they can specify collections
        while len(response['feed']['links']) >= 1 and len(images) < 100:
            url = response['feed']['links'][-1]['href']
            response = feedparser.parse(url)
            images += response.entries

        return self._rss_image_helper(images, num)

    def _rss_image_helper(self, images, num):
        results = self._shuffle_and_apply_filter(images)
        string_users, filtered_users, filtered_links = self._generate_links(results, num)
        return results[:num], string_users, filtered_links, filtered_users

    @staticmethod
    def _shuffle_and_apply_filter(images):
        random.shuffle(images)
        results = list(filter(lambda image: 'media_content' in image.keys() and 'medium' in
                                            image['media_content'][-1].keys() and
                                            image['media_content'][-1]['medium'] == 'image' and
                                            image["rating"] == 'nonadult',
                              images))
        print(results, " filter", flush=True)
        return results

    @staticmethod
    def _generate_links(results, num):
        filtered_users = list({image['media_credit'][0]['content'] for image in results[:num]})
        filtered_links = list({f"[{image['title']}]({image['link']})" for image in results[:num]})
        if len(filtered_users) == 1:
            string_users = filtered_users[0]
        else:
            string_users = ", ".join(filtered_users[1:]) + f" and {filtered_users[0]}"
        return string_users, filtered_users, filtered_links
