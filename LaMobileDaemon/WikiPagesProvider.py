import Confidential
import csv
from datetime import datetime
import logging
from pprint import pprint
import os
import WikiPageDistiller
import re
from Utility import byteLength, truncateByBytes

# Change PyWikiBot working directory
os.environ["PYWIKIBOT2_DIR"] = os.path.abspath("./Confidential")
logging.info("PYWIKIBOT2_DIR = %s", os.environ["PYWIKIBOT2_DIR"])

# Then import the module and user settings
import pywikibot
from pywikibot import pagegenerators

logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pywiki").setLevel(logging.INFO)

# Set up family
if Confidential.WIKI_FAMILY_FILE :
    pywikibot.config2.register_family_file(Confidential.WIKI_FAMILY, Confidential.WIKI_FAMILY_FILE)

# Contains information for pushing a wiki page
class WikiPagePushInfo :
    def __init__(self, pageTitle : str, pageUrl : str) :
        self.pageTitle = pageTitle
        self.pageUrl = pageUrl
        self.postImageUrl = None
        self.postText = None            # preset

    def getPostContent(self, postTextBytesLimit : int = None, contentBytesLimit : int = None) :
        content = self.postText + "\n" + self.pageUrl
        if postTextBytesLimit == None and contentBytesLimit != None:
            # -1 for \n
            postTextBytesLimit = bytesLimit - byteLength(self.pageUrl) - 1
        if postTextBytesLimit != None :
            if postTextBytesLimit <= 0 :
                raise ValueError("Bytes limit exceeded. Expected: {0}. Actual: {1}." \
                    .format(bytesLimit, byteLength(content)))
            postText = self.postText
            if postTextBytesLimit and byteLength(postText) > postTextBytesLimit :
                # Leave some space for ellipsis
                if postTextBytesLimit >= 3 :
                    content = truncateByBytes(self.postText, postTextBytesLimit - 3) + "…"
                else :
                    content = truncateByBytes(self.postText, postTextBytesLimit)
                content += "\n" + self.pageUrl
        return content

site = pywikibot.getSite("zh")

## zh Warriors Wiki Specific

# entry: (time, term)
pushedTerms = []

try :
    with open("Confidential/PushedTerms.txt", "r") as tsvfile :
        reader = csv.reader(tsvfile, delimiter="\t")
        for entry in reader :
            time = datetime.strptime(entry[0], '%Y-%m-%dT%H:%M:%S.%fZ')
            pushedTerms.append((time, str(entry[1]).strip()))

    logging.info("Loaded %i shared terms.", len(pushedTerms))
except FileNotFoundError :
    logging.info("No shared terms recorded yet.")

def BareDisambigTitle(title : str) :
    return re.sub(r"\w+\(.+?\)", "", title, 1)

def ParsePage(page : pywikibot.Page) :
    # EXTENDED
    # Retrieve parsed text of the page using action=parse.
    # TODO choose variation
    req = site._simple_request(action='parse', page=page, disabletoc=1, disableeditsection=1)
    data = req.submit()
    assert 'parse' in data, "API parse response lacks 'parse' key"
    assert 'text' in data['parse'], "API parse response lacks 'text' key"
    parsed_text = data['parse']['text']['*']
    # Distill text
    bareTitle = BareDisambigTitle(page.title())
    distilled = WikiPageDistiller.DistillHtml(parsed_text)
    info = WikiPagePushInfo(page.title(), page.full_url())
    if distilled.triviaScore > 0 :
        info.postText = distilled.trivia
        if not bareTitle in info.postText : 
            info.postText = distilled.introduction + info.postText
    else :
        info.postText = distilled.introduction
    #elif len(distilled.introduction) < 50 :
        #info.post
    # Choose cover image
    req = site._simple_request(action="query", titles=page.title(),
                                         prop="pageimages",
                                         piprop="thumbnail",
                                         pithumbsize=200)
    data = req.submit()
    assert "query" in data, "API request response lacks 'query' key"
    assert "pages" in data["query"], "API request response lacks 'pages' key"
    _, page = data["query"]["pages"].popitem()
    if "thumbnail" in page : info.postImageUrl = page["thumbnail"]["source"]
    return info

#def PickRandom() :

print(ParsePage(pywikibot.Page(site, "呼唤野性")).getPostContent(postTextBytesLimit=280-24))