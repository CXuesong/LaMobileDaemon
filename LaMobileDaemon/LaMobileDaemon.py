#! python3

import Confidential
from weibo import APIClient
from datetime import datetime
import webbrowser
import logging
from Config import GetConfig, SetConfig, SaveConfig
import WikiPagesProvider
from io import BytesIO
from urllib import request

logging.getLogger().level = logging.INFO

client = APIClient(app_key=Confidential.APP_KEY, app_secret=Confidential.APP_SECRET, redirect_uri=Confidential.CALLBACK_URL)

def Login() :
    token = GetConfig("Confidential", "Token")
    if not token :
        url = client.get_authorize_url()
        print(url)
        webbrowser.open_new(url)
        code = input("Code?")
        r = client.request_access_token(code)
        token = r.access_token
        expires = r.expires_in
        SetConfig("Confidential", "Token", token)
        SetConfig("Confidential", "Expires", str(r.expires_in))
        SaveConfig()
    else :
        expires = int(GetConfig("Confidential", "Expires"))
    logging.info("Token expires in %s .",datetime.fromtimestamp(expires))
    client.set_access_token(token, expires)

def TestPost() :
    print(client.statuses.update.post(status="测试状态。Test post."))

def PushWikiPage() :
    wp = WikiPagesProvider.RecommendRandomPage()
    #wp = WikiPagesProvider.RecommendPage("半月")
    image = wp.getImageResponse()
    # So that _encode_multipart in weibo.py will handle content-type correctly.
    image.name = wp.postImageName
    client.statuses.upload.post(status=request.quote(wp.getPostContent(postTextBytesLimit=(140-12)*2)), pic=image)
    logging.info("Pushed wiki page: %s .", wp.pageTitle)

Login()
PushWikiPage()
#print(client.statuses.user_timeline.get())
#TestPost()