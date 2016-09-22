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

# Change PyWikiBot working directory
os.environ["PYWIKIBOT2_DIR"] = os.path.abspath("./Confidential")
logging.info("PYWIKIBOT2_DIR = %s", os.environ["PYWIKIBOT2_DIR"])

# Then import the module and user settings
import pywikibot
from pywikibot import pagegenerators

logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("pywiki").setLevel(logging.WARNING)

# Set up family
if Confidential.WIKI_FAMILY_FILE :
    pywikibot.config2.register_family_file(Confidential.WIKI_FAMILY, Confidential.WIKI_FAMILY_FILE)

class WikiPagePushInfo :
    '''Contains information for pushing a wiki page.'''
    def __init__(self, pageTitle : str, pageUrl : str) :
        self.pageTitle = pageTitle
        self.pageUrl = pageUrl
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

def ParsePage(page : pywikibot.Page) :
    '''
    EXTENDED
    Retrieve parsed text of the page using action=parse.
    '''
    # TODO choose variation
    req = page.site._simple_request(action='parse', page=page, disabletoc=1, disableeditsection=1)
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
    req = page.site._simple_request(action="query", titles=page.title(),
                                         prop="pageimages",
                                         piprop="thumbnail",
                                         pithumbsize=200)
    data = req.submit()
    assert "query" in data, "API request response lacks 'query' key"
    assert "pages" in data["query"], "API request response lacks 'pages' key"
    _, page = data["query"]["pages"].popitem()
    if "thumbnail" in page : info.postImageUrl = page["thumbnail"]["source"]
    return info

#### Page selectors

def SelectRandomPage() :
    # Pages in certain categories will not be pushed.
    EXCLUDED_CATEGORY_PARTS = [
        "翻译",
        "删除"
    ]
    # Only pages with more than x revisions will be pushed.
    pageMinRevisions = int(GetConfig("Wiki", "PageMinimumRevisions", 4))
    maxFetchedPages = int(GetConfig("Wiki", "MaxRandomPicks", 500))
    fetchedPages = 0
    for page in siteZh.preloadpages(pagegenerators.RandomPageGenerator(maxFetchedPages, siteZh, namespaces = (0, )), groupsize=20) :
        fetchedPages += 1
        if page.title() in pushedTerms :
            continue
        if page.revision_count() < pageMinRevisions :
            continue
        cats = [cat.title() for cat in page.categories()]
        if next((c for c in cats if next((ec for ec in EXCLUDED_CATEGORY_PARTS if c in ec), None)), None) :
            continue
        # The page might be suitable
        logging.info("After %s/%s pages, choose: %s .", fetchedPages, maxFetchedPages, page)
        return page
    # No page selected
    logging.warn("After %s pages, no page meets the requirements.", fetchedPages)
    return None

def PageRecommender(pageSelector) :
    '''Converts a page selector function into a pusher/recommender.'''
    def func() :
        page = pageSelector()
        if page == None : return None
        pushedTerms[page.title()] = datetime.utcnow()
        SavePushedTerms()
        return ParsePage(page)
    return func

#### Page pusher/recommenders
RecommendRandomPage = PageRecommender(SelectRandomPage)

LoadPushedTerms()

# Unit test
if __name__ == "__main__" :
    for i in range(0, 20) :
        print(RecommendRandomPage().getPostContent(postTextBytesLimit = 240-20))
        print()