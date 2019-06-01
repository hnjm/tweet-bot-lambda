import json
import os
import random
import time
from app import endpoints
from app import consts
from requests_oauthlib import OAuth1Session
import boto3

# load config
config = {}
with open("config.json") as f:
    config = json.load(f)

# setup OAuth
CK = os.environ.get("CONSUMER_KEY")
CS = os.environ.get("CONSUMER_SECRET")
AT = os.environ.get("ACCESS_TOKEN")
ATS = os.environ.get("ACCESS_SECRET")
TWITTER = OAuth1Session(CK, CS, AT, ATS)

# setup boto3
s3 = boto3.resource(
    's3',
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_REGION")
)
bucket = s3.Bucket(os.environ.get("AWS_S3_BUCKET"))

# consts
MAX_COUNT_FAVORITE = 10
MAX_COUNT_RETWEET = 5

def _get_tweet_content(config: dict) -> str:
    return random.choice(config.get("TWEET_CONTENTS"))

def _tweet(status: str) -> None:
    params = {"status": status}
    response = TWITTER.post(endpoints.STATUS_UPDATE_URL, params=params)
    print("content:" + status)

def _search_tweets(query: str, count=100) -> list:
    params = {
        "q": query, 
        "count": count
    }
    response = TWITTER.get(endpoints.SEARCH_TWEET_URL, params=params)
    return json.loads(response.text)["statuses"]

def _retweet(ids: list) -> None:
    for id in ids:
        TWITTER.post(endpoints.RETWEET_URL.format(id))
        print("id:" + id)
        time.sleep(1)

def _favorite(ids: list) -> None:
    for id in ids:
        TWITTER.post(endpoints.FAVORITE_URL, data={"id": id})
        print("id:" + id)
        time.sleep(1)

def _filter(tweets: list, type: str, max_count: int) -> list:
    ids = []
    for tweet in tweets:
        if type == consts.TweetType.FAVORITE and not tweet["favorited"]:
            ids.append(tweet["id_str"])
        if type == consts.TweetType.RETWEET and not tweet["retweeted"]:
            ids.append(tweet["id_str"])
        if len(ids) > max_count:
            return ids
    return ids

def _get_followers(screen_name: str, count=100) -> list:
    print("Get followers ...")
    params = { 
        "screen_name": screen_name,
        "counts": count
    }
    response = TWITTER.get(endpoints.GET_FOLLOWER_URL.format(id), params=params)
    print("Get followers is completed!")
    return json.loads(response.text)["ids"]

def _download_from_s3(file_key: str) -> str:
    file_path = os.environ.get("ACCOUNT_NAME") + os.sep +  file_key
    bucket.download_file(file_path, file_key)
    return file_key

def _upload_to_s3(file_key: str) -> str:
    file_path = os.environ.get("ACCOUNT_NAME") + os.sep +  file_key
    bucket.upload_file(file_key, file_path)
    return file_path

def _follow(ids: list) -> None:
    print("Follow user ...")
    print("ids: " + json.dumps(ids))
    for id in ids:
        TWITTER.post(endpoints.FOLLOW_URL.format(id))
        time.sleep(1)
    print("Follow user is completed!")

def _get_new_followers(follower_ids: list) -> list:
    file_path = _download_from_s3(consts.Files.FOLLOWERS.value)
    with open(file_path) as f:
        current_follower_ids = json.loads(f.read())
    return list(set(follower_ids) - set(current_follower_ids))

def _update_followers(follower_ids: str) -> None:
    with open(consts.Files.FOLLOWERS.value, 'w') as f:
        json.dump(follower_ids, f, indent=4)
    _upload_to_s3(consts.Files.FOLLOWERS.value)


def _get_max_count(config:dict, type: str) -> int:
    if type == consts.TweetType.FAVORITE:
        if not config.get("MAX_COUNT_FAVORITE") or config.get("MAX_COUNT_FAVORITE") > MAX_COUNT_FAVORITE:
            return MAX_COUNT_FAVORITE
        else:
            return config.get("MAX_COUNT_FAVORITE")
    if type == consts.TweetType.RETWEET:
        if not config.get("MAX_COUNT_RETWEET") or config.get("MAX_COUNT_RETWEET") > MAX_COUNT_RETWEET:
            return MAX_COUNT_RETWEET
        else:
            return config.get("MAX_COUNT_RETWEET")
    return 0

def execute(config: dict) -> None:

    tweets = []
    if config.get("USE_FAVORITE") == "true" or config.get("USE_RETWEET") == "true":
        print("Search tweet ...")
        query = random.choice(config.get("QUERIES")) + " -RT" # remove retweet
        tweets = _search_tweets(query)
        print("Search tweet is completed!")

    if config.get("USE_FAVORITE") == "true":
        print("Favorite tweet ...")
        max_count = _get_max_count(config, consts.TweetType.FAVORITE)
        ids = _filter(tweets, consts.TweetType.FAVORITE, max_count)
        _favorite(ids)
        print("Favorite tweet is completed!")

    if config.get("USE_RETWEET") == "true":
        print("Retweet tweet ...")
        max_count = _get_max_count(config, consts.TweetType.RETWEET)
        ids = _filter(tweets, consts.TweetType.RETWEET, max_count)
        _retweet(ids)
        print("Retweet tweet is completed!")

    if config.get("USE_TWEET") == "true":
        print("Tweeting ...")
        tweet_content = _get_tweet_content(config)
        _tweet(tweet_content)
        print("Tweeting is completed!")

    if config.get("USE_FOLLOW_BACK") == "true" and os.environ.get("SCREEN_NAME"):
        print("Follow back ...")
        follower_ids = _get_followers(os.environ.get("SCREEN_NAME"))
        new_follower_ids = _get_new_followers(follower_ids)
        _follow(new_follower_ids)
        _update_followers(follower_ids)
        print("Follow back is completed!")