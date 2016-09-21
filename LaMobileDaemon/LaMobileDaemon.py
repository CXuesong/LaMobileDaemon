import Confidential
from configparser import ConfigParser
from weibo import APIClient
from datetime import datetime
import webbrowser
import logging

logging.getLogger().level = logging.INFO

config = ConfigParser()
config.read("LaMobile.ini")

client = APIClient(app_key=Confidential.APP_KEY, app_secret=Confidential.APP_SECRET, redirect_uri=Confidential.CALLBACK_URL)

def GetConfig(section, key, defaultValue=None) :
    return config.get(section, key, fallback=defaultValue)

def SetConfig(section, key, value) :
    if not config.has_section(section) : config.add_section(section)
    config.set(section, key, str(value))

def SaveConfig() :
    with open('LaMobile.ini', 'w') as configfile:
        config.write(configfile)

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