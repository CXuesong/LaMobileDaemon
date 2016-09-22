import Confidential
from weibo import APIClient
from datetime import datetime
import webbrowser
import logging
from Config import GetConfig, SetConfig, SaveConfig

logging.getLogger().level = logging.INFO

config = ConfigParser()
config.read("Confidential/LaMobile.ini")

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

Login()
#print(client.statuses.user_timeline.get())
#TestPost()