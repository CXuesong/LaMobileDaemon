import Confidential
import csv
from datetime import datetime, timedelta
import logging
from pprint import pprint
import os
import WikiPageDistiller
import re
from Utility import byteLength, truncateByBytes
from Config import GetConfig
import urllib.request

# Change PyWikiBot working directory
os.environ["PYWIKIBOT2_DIR"] = os.path.abspath("./Confidential")
logging.info("PYWIKIBOT2_DIR = %s", os.environ["PYWIKIBOT2_DIR"])

# Then import the module and user settings
import pywikibot
from pywikibot import pagegenerators

# Set up family
if Confidential.WIKI_FAMILY_FILE :
    pywikibot.config2.register_family_file(Confidential.WIKI_FAMILY, Confidential.WIKI_FAMILY_FILE)

class WikiPagePushInfo :
    '''Contains information for pushing a wiki page.'''
    def __init__(self, pageTitle : str, pageUrl : str) :
        self.pageTitle = pageTitle
        self.pageUrl = pageUrl
        self.postImageName = None       # Recommended file name of the image
        self.postImageUrl = None
        self.postText = None            # preset

    def getPostContent(self, postTextBytesLimit : int = None, contentBytesLimit : int = None) :
        '''Generates the whole post content.'''
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

    def getImageResponse(self) :
        '''
        Get image content, in HttpResponse, indicated by postImageUrl.
        Returns None if no postImageUrl specified.
        '''
        if not self.postImageUrl : return None
        return urllib.request.urlopen(self.postImageUrl)

    def getImageContent(self) :
        '''
        Get image content, in bytes, indicated by postImageUrl.
        Returns None if no postImageUrl specified.
        '''
        response = self.getImageResponse()
        return response.read()


siteZh = pywikibot.getSite("zh")

## zh Warriors Wiki Specific

# Load terms that has been pushed to Weibo, etc.
# entry: {term : time}
pushedTerms = {}

def LoadPushedTerms() :
    # The terms pushed {ttl} days before may be pushed again.
    ttl = float(GetConfig("Wiki", "PushedTermsTTL", 180))
    ttl = timedelta(days = ttl)
    now = datetime.utcnow()
    try :
        with open("Confidential/PushedTerms.txt", "r") as tsvfile :
            reader = csv.reader(tsvfile, delimiter="\t")
            for entry in reader :
                # Ignore trailing blank lines
                if len(entry) < 2 : continue
                time = datetime.strptime(entry[1], '%Y-%m-%dT%H:%M:%S.%f')
                if (time - now) < ttl :
                    pushedTerms[str(entry[0]).strip()] = time

        logging.info("Loaded %i shared terms.", len(pushedTerms))
    except FileNotFoundError :
        logging.info("No shared terms recorded yet.")

def SavePushedTerms() :
    with open("Confidential/PushedTerms.txt", "w") as tsvfile :
        writer = csv.writer(tsvfile, delimiter="\t")
        for term in pushedTerms :
            writer.writerow((term, pushedTerms[term].isoformat()))

def BareDisambigTitle(title : str) :
    return re.sub(r"\w+\(.+?\)", "", title, 1)

def ParsePage(page : pywikibot.Page, variation : str = "zh-cn") :
    '''
    EXTENDED
    Retrieve parsed text of the page using action=parse.
    '''
    req = page.site._simple_request(action='parse', page=page, uselang=variation, disabletoc=1, disableeditsection=1)
    data = req.submit()
    assert 'parse' in data, "API parse response lacks 'parse' key"
    assert 'text' in data['parse'], "API parse response lacks 'text' key"
    return data['parse']['text']['*']

def GetCoverImage(page : pywikibot.Page) :
    '''
    Gets the cover image name and url for a specific Page.
    Returns (None, None) if no cover image is found.
    '''
    try :
        return page.__lmd_cover_image
    except :
        pass
    req = page.site._simple_request(action="query", titles=page.title(),
                                    prop="pageimages",
                                    piprop="thumbnail|name",
                                    pithumbsize=200)
    data = req.submit()
    assert "query" in data, "API request response lacks 'query' key"
    assert "pages" in data["query"], "API request response lacks 'pages' key"
    _, jpage = data["query"]["pages"].popitem()
    if "thumbnail" in jpage :
        page.__lmd_cover_image = (jpage["pageimage"], jpage["thumbnail"]["source"])
    else :
        page.__lmd_cover_image = (None, None)
    return page.__lmd_cover_image

def ParseWikiPagePushInfo(page : pywikibot.Page) :
    parsed_text = ParsePage(page)
    # If the score of a trivia is higher than this,
    # we'll try to show it only, without leading text.
    triviaSignificance = float(GetConfig("Wiki", "PushedTermsTTL", 180))
    # Distill text
    bareTitle = BareDisambigTitle(page.title())
    distilled = WikiPageDistiller.DistillHtml(parsed_text)
    info = WikiPagePushInfo(page.title(), page.full_url())
    if distilled.trivia != None :
        # Trivia only
        info.postText = distilled.trivia
        # Leading + trivia
        if distilled.triviaScore < triviaSignificance or not bareTitle in info.postText : 
            info.postText = distilled.introduction + info.postText
    else :
        # Leading
        info.postText = distilled.introduction
    #elif len(distilled.introduction) < 50 :
        #info.post
    # Choose cover image
    info.postImageName, info.postImageUrl = GetCoverImage(page)
    return info

#### Page selectors

def SelectRandomPage() :
    # Pages in certain categories will not be pushed.
    EXCLUDED_CATEGORY_PARTS = [
        "翻译",
        "删除"
    ]
    # Only pages with more than x revisions will be pushed.
    pageMinRevisions = int(GetConfig("Wiki", "PageMinimumRevisions", 5))
    maxFetchedPages = int(GetConfig("Wiki", "MaxRandomPicks", 500))
    ignorePushedTerms = bool(GetConfig("Wiki", "IgnorePushedTermsList", False))
    forceWithImage = bool(GetConfig("Wiki", "ForceWithImage", True))
    fetchedPages = 0
    for page in pagegenerators.RandomPageGenerator(maxFetchedPages, siteZh, namespaces = (0, )) :
        fetchedPages += 1
        if page.title() in pushedTerms :
            logging.debug("Skipped: %s . Page has been pushed.", page)
            continue
        if page.revision_count() < pageMinRevisions :
            logging.debug("Skipped: %s . Insufficient revisions.", page)
            continue
        # Check categories
        cats = [cat.title() for cat in page.categories()]
        if next((c for c in cats if next((ec for ec in EXCLUDED_CATEGORY_PARTS if c in ec), None)), None) :
            logging.debug("Skipped: %s . Excluded by category.", page)
            continue
        # Check cover image
        if forceWithImage and not GetCoverImage(page)[1] :
            logging.debug("Skipped: %s . No cover image found.", page)
            continue
        # The page might be suitable
        logging.info("After %s/%s pages, choose: %s .", fetchedPages, maxFetchedPages, page)
        return page
    # No page selected
    logging.warn("After %s pages, no page meets the requirements.", fetchedPages)
    return None

def SelectPage(title : str) :
    return pywikibot.Page(siteZh, title)

def PageRecommender(pageSelector) :
    '''Converts a page selector function into a pusher/recommender.'''
    def func(*args, **kw) :
        page = pageSelector(*args, **kw)
        if page == None : return None
        pushedTerms[page.title()] = datetime.utcnow()
        SavePushedTerms()
        return ParseWikiPagePushInfo(page)
    return func

#### Page pusher/recommenders
RecommendRandomPage = PageRecommender(SelectRandomPage)
RecommendPage = PageRecommender(SelectPage)

LoadPushedTerms()

# Unit test
if __name__ == "__main__" :
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger("pywiki").setLevel(logging.WARNING)
    for i in range(0, 20) :
        page = RecommendRandomPage()
        print(page.getPostContent(postTextBytesLimit = 240-20))
        image = page.getImageContent()
        if image != None :
            print("Image size:", len(image), " B. ", image[:10])