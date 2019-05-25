from enum import Enum

class TweetType(Enum):
    FAVORITE = "FAVORITE"
    RETWEET = "RETWEET"

class Files(Enum):
    FOLLOWERS = "followers.json"