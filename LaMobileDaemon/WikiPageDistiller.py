import mwparserfromhell
from bs4 import BeautifulSoup
import re
from pprint import pprint
import logging

# Distilled page profile
class PageProfile :
    def __init__(self) :
        self.mainQuote = None
        self.introduction = None
        self.trivia = None
        self.triviaScore = 0    # > 0 means trivia is more notable than introduction

# Makes a title cannonical
def NormalizeWikiTitle(title) :
    title = str(title).replace("_", " ")
    title = title.strip()
    if len(title) == 0 : return title
    title = title[0].upper() + title[1:]
    return title

def isNoneOrWhitespace(x) :
    if x :
        x = str(x).strip()
        return len(x) == 0
    return True

# Refines distilled text
def refineText(text : str) :
    #text = re.sub("（英文：(.*?)）", r"（\1）", text)
    return text

def ParseMainQuote(soup : BeautifulSoup) :
    # Text before H1 or H2 or end of document
    node = soup.h1 or soup.h2
    if node == None :
        for node in soup : pass
    while node != None :
        if node.name == "blockquote" :
            return node.p.get_text(strip=True)
        node = node.previous_sibling
    return None

def ParseLeadingText(soup : BeautifulSoup) :
    # Filter 1st root paragraph, as leading text
    text = None
    for node in soup("p", recursive=False) :
        text = node.get_text(strip=True)
        if not isNoneOrWhitespace(text) : break
    if text :
        return refineText(text)
    return None

def ParseIntroductionSection(soup : BeautifulSoup) :
    # Filter 1st paragraph in Introduction section
    node = None
    for n in soup("h2") :
        if "简介" in n.get_text() :
            node = n
            break
    if node :
        for node in IterateContentNodes(node) :
            if node.name == "h2" :
                break
            text = None
            try :
                text = node.get_text(strip=True)
            except AttributeError :
                text = str(node)
            if not isNoneOrWhitespace(text) :
                return refineText(text)
    return None

# Iterates through nodes next to the specific node,
# recursively until certian types of nodes are met.
def IterateContentNodes(node) :
    def IterateNodes(nodes) :
        for n in nodes :
            if n.name in ("p", "li", "dt", "dd", None) or n.name[0] == "h" :
                yield n
            elif n.name == "blockquote" :
                pass
            else :
                for c in IterateNodes(n.children) :
                    yield c
    return IterateNodes(node.next_siblings)

def ParseATrivia(soup : BeautifulSoup) :
    # Find a non-trivial trivia (score > 0)
    keywords = {
        "误" : -1,
        ("描写为", "描述为") : -0.5,
        "确认" : 0.3,
        "凯特" : 0.5,
        ("维琪", "维多利亚") : 0.5,
        "基立" : 0.7,
        "访谈" : 0.5,
        ("揭露", "透露") : 0.5,
        "爱" : 1,
        "争议" : 1,
        ("读者", "粉丝") : 0.7,
        }
    node = None
    for n in soup("h2") :
        if "细节" in n.get_text() :
            node = n
            break
    trivia = []
    if node :
        for node in IterateContentNodes(node) :
            if node.name == "h2" :
                break
            text = None
            try :
                text = node.get_text(strip=True)
            except AttributeError :
                text = str(node)
            if isNoneOrWhitespace(text) :
                continue
            # Score it!
            score = 0
            for ks in keywords :
                deltaScore = keywords[ks]
                if type(ks) == str : ks = (ks, )
                for k in ks :
                    if k in text :
                        score += deltaScore
                        break
            if score > 0 :
                trivia.append((score, text))
    if len(trivia) == 0 : return 0, None
    score, text = max(trivia, key=lambda t : t[0])
    logging.info("Selected trivia %s with score = %f .", text[:10], score)
    return score, refineText(text)

# zh Warriors Wiki specific
def DistillHtml(html : str) :
    profile = PageProfile()
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(("abbr", "table")) : node.decompose()
    for node in soup(class_=("toc", "reference")) : node.decompose()
    profile.mainQuote = ParseMainQuote(soup)
    profile.introduction = (ParseLeadingText(soup) or "") + (ParseIntroductionSection(soup) or "")
    profile.triviaScore, profile.trivia = ParseATrivia(soup)
    return profile

# Unit test
if __name__ == "__main__" :
    import WikiPagesProvider
    import pywikibot
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger("pywiki").setLevel(logging.WARNING)
    page = pywikibot.Page(WikiPagesProvider.siteZh, "火星")
    distilled = DistillHtml(WikiPagesProvider.ParsePage(page))
    parsed = WikiPagesProvider.ParseWikiPagePushInfo(page)
    pprint(distilled.__dict__)
    pprint(parsed.__dict__)
