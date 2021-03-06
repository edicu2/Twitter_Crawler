from bs4 import BeautifulSoup
import GetOldTweets3 as got
from datetime import datetime, timedelta
import time

# GetOldTweet3 library 사용 
# TweetCriteria 객체안에 Username 과 Emoji를 "unicode","ignore","name" 3가지 중 선택
tweetCriteria = got.manager.TweetCriteria().setUsername("r5hyacftbPcFWXm")\
                                           .setEmoji("unicode")\
                                           .setMaxTweets(10)
# Tweet 값을 list 형태로 받아온다.
tweets = got.manager.TweetManager.getTweets(tweetCriteria)

for n in range(0,len(tweets)):
    print("username :",tweets[n].username)
    print("text :",tweets[n].text)
    print("retweets :",tweets[n].retweets)
    print("favorites :",tweets[n].favorites)
    print("replies :",tweets[n].replies)
    print("id :",tweets[n].id)
    print("permalink :",tweets[n].permalink)
    print("author_id :",tweets[n].author_id)
    print("date :",tweets[n].date)
    print("formatted_date :",tweets[n].formatted_date)
    print("hashtags :",tweets[n].hashtags)
    print("mentions :",tweets[n].mentions)
    print("img :",tweets[n].img)
    print(n)
    print(" ")
