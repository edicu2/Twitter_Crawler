# -*- coding: utf-8 -*-

import json, re, datetime, sys, random, http.cookiejar
import urllib.request, urllib.parse, urllib.error
from pyquery import PyQuery
from .. import models

class TweetManager:
    """A class for accessing the Twitter's search engine"""
    def __init__(self):
        pass

    # 웹 브라우저
    user_agents = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:62.0) Gecko/20100101 Firefox/62.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:61.0) Gecko/20100101 Firefox/61.0',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15',
    ]


    """@staticmethod ( 정적 메소드 )
    class 객체 생성 없이 사용 가능 
    python의 경우 import 되어지는 패키지들은 @staticmethod로 구성되어진다.
    """
    @staticmethod
    def getTweets(tweetCriteria, receiveBuffer=None, bufferLength=100, proxy=None, debug=False):
        """Get tweets that match the tweetCriteria parameter
        A static method.

        Parameters
        ----------
        tweetCriteria : tweetCriteria, an object that specifies a match criteria
        receiveBuffer : callable, a function that will be called upon a getting next `bufferLength' tweets
        bufferLength: int, the number of tweets to pass to `receiveBuffer' function
        proxy: str, a proxy server to use
        debug: bool, output debug information
        """

        """ 

        variables
        ----------
        results 결과값 입력될 list 
        cookieJar 웹 브라우저의 쿠키 처리 객체 
        user_agen 웹브라우저 선택
        all_usernames 크롤링하고자하는 사용자ID
        usernames_per_batch = 20 (default) 한번 반복시 크롤링할 사용자 수 
        """

        results = []
        resultsAux = []
        cookieJar = http.cookiejar.CookieJar()
        user_agent = random.choice(TweetManager.user_agents)
        all_usernames = []
        usernames_per_batch = 20

        # step 0 username의 갯수를 확인 후 20개씩 분리  
        if hasattr(tweetCriteria, 'username'):
            if type(tweetCriteria.username) == str or not hasattr(tweetCriteria.username, '__iter__'):
                tweetCriteria.username = [tweetCriteria.username]

            usernames_ = [u.lstrip('@') for u in tweetCriteria.username if u] # 트위터 아이디 앞 '@'를 삭제 
            all_usernames = sorted({u.lower() for u in usernames_ if u}) # ID 소문자로 변환 후 알바벳순으로 정렬 
            n_usernames = len(all_usernames) 
            n_batches = n_usernames // usernames_per_batch + (n_usernames % usernames_per_batch > 0) # 20개씩 잘라서 반복 횟수 지정 
        else:
            n_batches = 1
        # step 1 n_batchs 갯수에 따라 20개씩 ID를 구분 
        for batch in range(n_batches):  # ex) n_batchs =1 경우 21개 이상의 사용자ID 입력 
            refreshCursor = ''
            batch_cnt_results = 0

            if all_usernames:  # a username in the criteria 
                tweetCriteria.username = all_usernames[batch*usernames_per_batch:batch*usernames_per_batch+usernames_per_batch]

            active = True
            # step 2 사용자 ID별로 웹페이지를 json 형식으로 받기 
            while active:
                json = TweetManager.getJsonResponse(tweetCriteria, refreshCursor, cookieJar, proxy, user_agent, debug=debug) # twitter웹페이지를 json파일로 가져오기 
                if len(json['items_html'].strip()) == 0:
                    break

                refreshCursor = json['min_position']
                scrapedTweets = PyQuery(json['items_html'])
                #Remove incomplete tweets withheld by Twitter Guidelines
                scrapedTweets.remove('div.withheld-tweet')
                tweets = scrapedTweets('div.js-stream-tweet')

                if len(tweets) == 0:
                    break
                # step 3  트위터를 게시글 단위로 구분하고 PyQuery를 이용해 각 정보 추출하여 tweet객체에 입력 
                for tweetHTML in tweets:
                    tweetPQ = PyQuery(tweetHTML)
                    
                    tweet = models.Tweet()
                    usernames = tweetPQ("span.username.u-dir b").text().split()
                    if not len(usernames):  # fix for issue #13
                        continue
                    # tweet 게시물 단위 정보들 tweet 객체에 입력 
                    tweet.username = usernames[0]
                    tweet.to = usernames[1] if len(usernames) >= 2 else None  # take the first recipient if many
                    rawtext = TweetManager.textify(tweetPQ("p.js-tweet-text").html(), tweetCriteria.emoji)
                    tweet.text = re.sub(r"\s+", " ", rawtext)\
                        .replace('# ', '#').replace('@ ', '@').replace('$ ', '$')
                    tweet.retweets = int(tweetPQ("span.ProfileTweet-action--retweet span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
                    tweet.favorites = int(tweetPQ("span.ProfileTweet-action--favorite span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
                    tweet.replies = int(tweetPQ("span.ProfileTweet-action--reply span.ProfileTweet-actionCount").attr("data-tweet-stat-count").replace(",", ""))
                    tweet.id = tweetPQ.attr("data-tweet-id")
                    tweet.permalink = 'https://twitter.com' + tweetPQ.attr("data-permalink-path")
                    tweet.author_id = int(tweetPQ("a.js-user-profile-link").attr("data-user-id"))

                    dateSec = int(tweetPQ("small.time span.js-short-timestamp").attr("data-time"))
                    tweet.date = datetime.datetime.fromtimestamp(dateSec, tz=datetime.timezone.utc)
                    tweet.formatted_date = datetime.datetime.fromtimestamp(dateSec, tz=datetime.timezone.utc)\
                                                            .strftime("%a %b %d %X +0000 %Y")
                    tweet.hashtags, tweet.mentions = TweetManager.getHashtagsAndMentions(tweetPQ)

                    geoSpan = tweetPQ('span.Tweet-geo')
                    if len(geoSpan) > 0:
                        tweet.geo = geoSpan.attr('title')
                    else:
                        tweet.geo = ''

                    urls = []
                    for link in tweetPQ("a"):
                        try:
                            urls.append((link.attrib["data-expanded-url"]))
                        except KeyError:
                            pass
                    tweet.urls = ",".join(urls)
                    
                    ## 추가된 부분
                    tweet.img = TweetManager.get_media_url(tweetPQ)
                    ## 추가된 부분
                    
                    # step 4 results,resultsAux list에 tweet 객체 담기 
                    results.append(tweet)
                    resultsAux.append(tweet)
                    
                    if receiveBuffer and len(resultsAux) >= bufferLength:
                        receiveBuffer(resultsAux)
                        resultsAux = []

                    batch_cnt_results += 1
                    if tweetCriteria.maxTweets > 0 and batch_cnt_results >= tweetCriteria.maxTweets:
                        active = False
                        break

            if receiveBuffer and len(resultsAux) > 0:
                receiveBuffer(resultsAux)
                resultsAux = []

        return results

    @staticmethod 
    def getHashtagsAndMentions(tweetPQ):
        """Given a PyQuery instance of a tweet (tweetPQ) getHashtagsAndMentions
        gets the hashtags and mentions from a tweet using the tweet's
        anchor tags rather than parsing a tweet's text for words begining
        with '#'s and '@'s. All hashtags are wrapped in anchor tags with an href
        attribute of the form '/hashtag/{hashtag name}?...' and all mentions are
        wrapped in anchor tags with an href attribute of the form '/{mentioned username}'.
        """
        anchorTags = tweetPQ("p.js-tweet-text")("a")
        hashtags = []
        mentions = []
        for tag in anchorTags:
            tagPQ = PyQuery(tag)
            url = tagPQ.attr("href")
            if url is None or len(url) == 0 or url[0] != "/":
                continue

            # Mention anchor tags have a data-mentioned-user-id
            # attribute. 
            if not tagPQ.attr("data-mentioned-user-id") is None:
                mentions.append("@" + url[1:])
                continue

            hashtagMatch = re.match('/hashtag/\w+', url)
            if hashtagMatch is None:
                continue

            hashtag = hashtagMatch.group().replace("/hashtag/", "#")
            hashtags.append(hashtag)

        return (" ".join(hashtags), " ".join(mentions))

    @staticmethod
    def textify(html, emoji):
        """Given a chunk of text with embedded Twitter HTML markup, replace
        emoji images with appropriate emoji markup, replace links with the original
        URIs, and discard all other markup.
        """
        # Step 0, compile some convenient regular expressions 
        imgre = re.compile("^(.*?)(<img.*?/>)(.*)$") # 정규표현식 
        charre = re.compile("^&#x([^;]+);(.*)$")     #  ==
        htmlre = re.compile("^(.*?)(<.*?>)(.*)$")    #  == 
        are = re.compile("^(.*?)(<a href=[^>]+>(.*?)</a>)(.*)$")

        # Step 1, prepare a single-line string for re convenience
        puc = chr(0xE001)
        html = html.replace("\n", puc)

        # Step 2, find images that represent emoji, replace them with the
        # Unicode codepoint of the emoji.
        text = ""
        match = imgre.match(html)
        while match:
            text += match.group(1)
            img = match.group(2)
            html = match.group(3)

            attr = TweetManager.parse_attributes(img)
            if emoji == "unicode":
                chars = attr["alt"]
                match = charre.match(chars)
                while match:
                    text += chr(int(match.group(1),16))
                    chars = match.group(2)
                    match = charre.match(chars)
            elif emoji == "named":
                text += "Emoji[" + attr['title'] + "]"
            else:
                text += " "

            match = imgre.match(html)
        text = text + html

        # Step 3, find links and replace them with the actual URL
        html = text
        text = ""
        match = are.match(html)
        while match:
            text += match.group(1)
            link = match.group(2)
            linktext = match.group(3)
            html = match.group(4)

            attr = TweetManager.parse_attributes(link)
            try:   
                if "u-hidden" in attr["class"]:
                    pass
                elif "data-expanded-url" in attr \
                and "twitter-timeline-link" in attr["class"]:
                    text += attr['data-expanded-url']
                else:
                    text += link
            except:
                pass

            match = are.match(html)
        text = text + html

        # Step 4, discard any other markup that happens to be in the tweet.
        # This makes textify() behave like tweetPQ.text()
        html = text
        text = ""
        match = htmlre.match(html)
        while match:
            text += match.group(1)
            html = match.group(3)
            match = htmlre.match(html)
        text = text + html

        # Step 5, make the string multi-line again.
        text = text.replace(puc, "\n")
        return text

    @staticmethod
    def parse_attributes(markup):
        """Given markup that begins with a start tag, parse out the tag name
        and the attributes. Return them in a dictionary.
        """
        gire = re.compile("^<([^\s]+?)(.*?)>.*")
        attre = re.compile("^.*?([^\s]+?)=\"(.*?)\"(.*)$")
        attr = {}

        match = gire.match(markup)
        if match:
            attr['*tag'] = match.group(1)
            markup = match.group(2)

            match = attre.match(markup)
            while match:
                attr[match.group(1)] = match.group(2)
                markup = match.group(3)
                match = attre.match(markup)

        return attr


    @staticmethod
    def getJsonResponse(tweetCriteria, refreshCursor, cookieJar, proxy, useragent=None, debug=False):
        """Invoke an HTTP query to Twitter.
        Should not be used as an API function. A static method.
        """
        url = "https://twitter.com/i/search/timeline?"

        if not tweetCriteria.topTweets:
            url += "f=tweets&"

        url += ("vertical=news&q=%s&src=typd&%s"
                "&include_available_features=1&include_entities=1&max_position=%s"
                "&reset_error_state=false")

        urlGetData = ''

        if hasattr(tweetCriteria, 'querySearch'):
            urlGetData += tweetCriteria.querySearch

        if hasattr(tweetCriteria, 'username'):
            if not hasattr(tweetCriteria.username, '__iter__'):
                tweetCriteria.username = [tweetCriteria.username]

            usernames_ = [u.lstrip('@') for u in tweetCriteria.username if u]
            tweetCriteria.username = {u.lower() for u in usernames_ if u}

            usernames = [' from:'+u for u in sorted(tweetCriteria.username)]
            if usernames:
                urlGetData += ' OR'.join(usernames)

        if hasattr(tweetCriteria, 'within'):
            if hasattr(tweetCriteria, 'near'):
                urlGetData += ' near:"%s" within:%s' % (tweetCriteria.near, tweetCriteria.within)
            elif hasattr(tweetCriteria, 'lat') and hasattr(tweetCriteria, 'lon'):
                urlGetData += ' geocode:%f,%f,%s' % (tweetCriteria.lat, tweetCriteria.lon, tweetCriteria.within)

        if hasattr(tweetCriteria, 'since'):
            urlGetData += ' since:' + tweetCriteria.since

        if hasattr(tweetCriteria, 'until'):
            urlGetData += ' until:' + tweetCriteria.until

        if hasattr(tweetCriteria, 'lang'):
            urlLang = 'l=' + tweetCriteria.lang + '&'
        else:
            urlLang = ''
        url = url % (urllib.parse.quote(urlGetData.strip()), urlLang, urllib.parse.quote(refreshCursor))
        useragent = useragent or TweetManager.user_agents[0]

        headers = [
            ('Host', "twitter.com"),
            ('User-Agent', useragent),
            ('Accept', "application/json, text/javascript, */*; q=0.01"),
            ('Accept-Language', "en-US,en;q=0.5"),
            ('X-Requested-With', "XMLHttpRequest"),
            ('Referer', url),
            ('Connection', "keep-alive")
        ]

        if proxy:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}), urllib.request.HTTPCookieProcessor(cookieJar))
        else:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookieJar))
        opener.addheaders = headers

        if debug:
            print(url)
            print('\n'.join(h[0]+': '+h[1] for h in headers))

        try:
            response = opener.open(url)
            jsonResponse = response.read()
        except Exception as e:
            print("An error occured during an HTTP request:", str(e))
            print("Try to open in browser: https://twitter.com/search?q=%s&src=typd" % urllib.parse.quote(urlGetData))
            sys.exit()

        try:
            s_json = jsonResponse.decode()
        except:
            print("Invalid response from Twitter")
            sys.exit()

        try:
            dataJson = json.loads(s_json)
        except:
            print("Error parsing JSON: %s" % s_json)
            sys.exit()

        if debug:
            print(s_json)
            print("---\n")

        return dataJson

    ## 추가된 부분
    @staticmethod
    def get_media_url(tweetPQ):
        """PyQuery를 이용한 media crawling Method.
        Twitter게시물 특징 :(1) video,gif 1개, image 1,2,4개 upload 한계 
                        (2) video,gif와 image 함께 upload 불가능
                        (3) video,gif 파일 접근 허용x -> thumbNail_image URL 제공
        Crawling 방식 : (1) image URL 2개 이상일 경우  ,로 구분하여 반환 
        """
        url = None
        # gif, video
        if tweetPQ('div.PlayableMedia-player') :
            # print('video')
            url = tweetPQ('div.PlayableMedia-player').attr('style').split('(')[1].rstrip(')').replace("'","")
        # img  
        else: 
            for n in range(0,len(tweetPQ('img'))) :
                if 'media' in tweetPQ('img').eq(n).attr('src') :
                    # print('img')
                    if url is not None: 
                        url = url + "," + tweetPQ('img').eq(n).attr('src')
                    else : url = tweetPQ('img').eq(n).attr('src')
        return url
    ## 추가된 부분
                