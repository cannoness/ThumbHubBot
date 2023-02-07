from pytwitter import Api
import os
from dotenv import load_dotenv

load_dotenv()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")


class TwitterRest:
    def __init__(self):
        self.api = Api(bearer_token=BEARER_TOKEN)

    def get_twitter_media(self, screen_name, num):
        user_id = self.api.get_user(username=screen_name).data.id
        tweets = self.api.get_timelines(user_id, tweet_fields='created_at', expansions='attachments.media_keys',
                                        media_fields='url', exclude=["retweets", "replies"], max_results=100)

        test_list = {text.url for text in tweets.includes.media}
        return_list = list(filter(lambda item: item is not None, test_list))
        return return_list[:num]
