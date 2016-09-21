import Confidential
import csv
from datetime import datetime
import logging
from pprint import pprint
import os
import WikiPageDistiller

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
    def __init__(self, pageTitle : str, pageUrl : str, previewText : str, previewImageUrl : str) :
        self.pageTitle = pageTitle
        self.pageUrl = pageUrl
        self.previewText = previewText
        self.previewImageUrl = previewImageUrl
        self.postText = previewText      # preset

    def getPostContent(bytesLimit : int = None) :
        content = postText + "\n" + pageUrl
        if (not bytesLimit or len(postText.encode(content)) > bytesLimit) :
            #TODO Truncate
            raise ValueError("Bytes limit exceeded.")
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

def ParsePage(page : pywikibot.Page) :
    request = site._simple_request(action="query", titles=page.title(),
                                         prop="pageimages",
                                         piprop="thumbnail",
                                         pithumbsize=200)
    data = request.submit()
    assert "query" in data, "API request response lacks 'query' key"
    assert "pages" in data["query"], "API request response lacks 'pages' key"
    _, page = data["query"]["pages"].popitem()
    imageUrl = None
    if "thumbnail" in page : imageUrl = page["thumbnail"]["source"]
    print(imageUrl)
    return WikiPagePushInfo(page.title(withNamespace=False), page.full_url(), None, imageUrl)

#def PickRandom() :
#ParsePage(pywikibot.Page(site, "火星"))
WikiPageDistiller.DistillHtml(pywikibot.Page(site, "火星")._get_parsed_page())