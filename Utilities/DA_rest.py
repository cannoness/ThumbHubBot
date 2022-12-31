import requests
import ast
import json
import os
from dotenv import load_dotenv

AUTH_URL = "https://www.deviantart.com/oauth2/token?grant_type=client_credentials&"
API_URL = "https://www.deviantart.com/api/v1/oauth2/"


class DARest:
    def __init__(self):
        load_dotenv()
        self.secret = os.getenv("DA_SECRET")
        self.client = os.getenv("DA_CLIENT")
        self.access_token = self.acquire_access_token()

    def acquire_access_token(self):
        response = requests.get(
            f"{AUTH_URL}client_id={self.client}&client_secret={self.secret}")

        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)['access_token']

    def fetch_user_gallery(self, username, offset=0):
        response = self._gallery_fetch_helper(username, offset)
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return results

    def fetch_entire_user_gallery(self, username):
        # initial fetch
        response = self._gallery_fetch_helper(username)
        results = response['results']

        # build the rest of the gallery
        while response['has_more']:
            next_offset = response['next_offset']
            response = self._gallery_fetch_helper(username, offset=next_offset)
            results += response['results']
        return results

    def fetch_daily_deviations(self):
        response = requests.get(f"{API_URL}browse/dailydeviations?access_token={self.access_token}")
        decoded_content = response.content.decode("UTF-8")
        results = json.loads(decoded_content)['results']
        return results

    def _gallery_fetch_helper(self, username, offset=0):
        response = requests.get(
            f"{API_URL}gallery/all?username={username}&limit=24&mature_content=false&access_token="
            f"{self.access_token}&offset={offset}")
        decoded_content = response.content.decode("UTF-8")
        return json.loads(decoded_content)
