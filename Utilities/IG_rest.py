import instaloader


class IGRest:
    def __init__(self):
        self.bot = instaloader.Instaloader()

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
