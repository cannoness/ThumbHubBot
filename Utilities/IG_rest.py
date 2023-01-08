import instaloader
import os

from dotenv import load_dotenv

load_dotenv()
SESSION_ID = os.getenv("SESSION_ID")
SESSION_USER = os.getenv("SESSION_USER")


class IGRest:
    def __init__(self):
        self.bot = instaloader.Instaloader()
        self.bot.load_session_from_file(username="ThumbHubBot", filename=SESSION_ID)
        username = self.bot.test_login()
        if not username:
            raise SystemExit("Not logged in. Are you logged in successfully in Firefox?")

    def get_recent(self, username, num):
        try:
            profile = instaloader.Profile.from_username(self.bot.context, username)
        except Exception as ex:
            return None
        posts = profile.get_posts()
        post_urls = []
        for index, post in enumerate(posts):
            if index == num:
                break
            post_urls.append(post.url)
        return post_urls
