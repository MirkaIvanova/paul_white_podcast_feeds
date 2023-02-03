import requests
import json
from html_to_json import convert
from codecs import encode, decode
from datetime import datetime, timedelta
import time
from xml.dom import minidom
import html
import re
import csv



def timestampToDate(timestamp):
    dtObj = datetime.fromtimestamp(timestamp) - timedelta(hours=10, minutes=0)

    return dtObj.strftime('%a, %d %b %Y %H:%M:%S')

def secondsToHour(seconds):
    return time.strftime("%H:%M:%S", time.gmtime(seconds))  

def htmlToJson(htmlString):
    return convert(htmlString)    

def iterateJson(json, cbk):
    changes = cbk(json) 

    if type(json) == list:
        i=0
        while i < len(json):
            iterateJson(json[i], cbk)
            i += 1
    elif type(json) == dict:
        for k, v in json.items():
            iterateJson(v, cbk)
    elif type(json) == str:
        pass        
    else:
        print ("unknown type", type(json))
   
    if changes > 0:
        iterateJson(json, cbk)

def webGetHtmlPage(year, month, page):
    url = f"https://pwmmedia.podbean.com/{year}/{month}/page/{page}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    return r.text

def webGetAllPagesForMonthAsHtml(year, month):
    allPages = []
    page=1
    pageHtmlString = webGetHtmlPage(year, month, page)
    while (pageHtmlString != None):
        page += 1
        allPages.append(pageHtmlString)
        pageHtmlString = webGetHtmlPage(year, month, page)    

    return allPages

def pwEpisodesJsonToXmlFeed(episodesJson):
    document = minidom.Document()
    rssNode = xmlCreateNodeRss(document, episodesJson) 
    document.appendChild(rssNode)

    xmlStr = document.toprettyxml(indent = "", encoding="utf-8").decode("utf-8")
    xmlStr = xmlStr.replace('\n', '')
    xmlStr = xmlStr.replace('<item>', '\n<item>') #MII uncomment
    xmlStr = xmlStr.replace('</channel>', '\n</channel>')
    # xmlStr = xmlStr.replace('<itunes:summary>', '<itunes:summary>\n')

    return xmlStr

def pwEpisodesJsonToCsv_(episodesJson):
    episodesJson = [{"a": '"abc"  hello', "b": 21, "c": 31}, {"a": 12, "b": 22, "c": 32}, {"a": 13, "b": 23, "c": 33}]

    data_file = open('output/data_file.csv', 'w')
    csv_writer = csv.writer(data_file)
    count = 0
    
    for emp in episodesJson:
        if count == 0:
            header = emp.keys()
            csv_writer.writerow(header)
            count += 1
    
        csv_writer.writerow(emp.values())
    
    data_file.close()    

def pwCbkNormalizeJson(json):
    changes=0
    if type(json) == dict:
        for key in ["class", "style", "svg", "type", "id", "img", "_attributes"]:
            if key in json.keys():
                del json[key]
                changes += 1

        for k in list(json.keys()):
            v=json[k]
            #extract element if [el]
            if type(v) == list and len(v) == 1:
                json[k] = v[0] 
                changes += 1

            if type(v) == dict and len(v) == 1:
                json[k] = v[next(iter(v))] 
                changes += 1                

            # delete empty dict
            if type(v) == dict and len(v) == 0:
                del json[k]
                changes += 1
   
    if type(json) == list:
        i=0
        while i < len(json):
            if type(json[i]) == dict and len(json[i]) == 0:
                del json[i]
                
            i+=1            

    return changes

def pwNormalizeSummary(summary):
    normalizedSummary = html.unescape(summary) 
    normalizedSummary = normalizedSummary.replace('<p>', '')
    normalizedSummary = normalizedSummary.replace('</p>', '')
    normalizedSummary = normalizedSummary.replace('\u00c2\u00a0', '')
    normalizedSummary = normalizedSummary.replace(u'\xa0', '')
    normalizedSummary = normalizedSummary.replace('\n', '')
    normalizedSummary = normalizedSummary.replace('\r', '')
    normalizedSummary = normalizedSummary.replace('<span class="Apple-converted-space"></span>', '')
    normalizedSummary = normalizedSummary.replace('<span class="Apple-converted-space">', '')
    normalizedSummary = normalizedSummary.replace('</span>', '') 
    normalizedSummary = re.sub(r"(Accompanying scripture:)(.)", r"\1 \2", normalizedSummary)
    normalizedSummary = re.sub(r"(Accompanying scripture:)  (.)", r"\1 \2", normalizedSummary)       
    return normalizedSummary

def pwGetEpisodesFromPageAsJson(pageJson):
    resultStr = decode(encode(pageJson["html"]["body"]["script"], 'latin-1', 'backslashreplace'), 'unicode-escape')
    return json.loads(resultStr[26:-1])["store"]["listEpisodes"]

def pwGetEpisodesFromAllPagesAsJson(arrPagesHtmlString):
    allEpisodesJson = []
    for pageHtmlString in arrPagesHtmlString:
        pageJson = htmlToJson(pageHtmlString)
        iterateJson(pageJson, pwCbkNormalizeJson)
        episodesPerPageJson = pwGetEpisodesFromPageAsJson(pageJson)
        allEpisodesJson += episodesPerPageJson

    return allEpisodesJson   

def xmlCreateTag(xmlDocument, tag, text, attributes=None):
    node = xmlDocument.createElement(tag)
    if text:
        node.appendChild(xmlDocument.createTextNode(text))

    if attributes:
        for k, v in attributes.items():
            node.setAttribute(k, v)    
    return node

def xmlCreateNodeEpisode(xmlDocument, episode):
    #print(pwNormalizeSummary(episode["previewContent"]) + "|")  #MII remove ~~~~ 

    episodeNode = xmlDocument.createElement('item')
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'pubDate', timestampToDate(episode["publishTimestamp"])))
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'itunes:title', episode["title"]))
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'itunes:summary', pwNormalizeSummary(episode["previewContent"])))
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'enclosure', text=None, attributes={"url": episode["mediaUrl"], "length": "1048576", 'type': "audio/mpeg"}))          
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'itunes:duration', secondsToHour(episode["duration"])))
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'itunes:episode', "1"))
    episodeNode.appendChild(xmlCreateTag(xmlDocument,'itunes:image', text=None, attributes={'href': episode["largeLogo"]}))

    return episodeNode

def xmlCreateNodeChannel(document, episodesJson):
    channelNode = document.createElement('channel')
    channelNode.appendChild(xmlCreateTag(document, 'title', "Paul White Ministries1"))

    node = document.createElement('atom:link')
    node.setAttribute('href', "https://feed.podbean.com/pwmmedia/feed.xml")
    node.setAttribute('rel', "self")
    node.setAttribute('type', "application/rss+xml")
    channelNode.appendChild(node)

    channelNode.appendChild(xmlCreateTag(document, 'link', "http://www.paulwhiteministries.org"))
    channelNode.appendChild(xmlCreateTag(document, 'Description', "Description..."))            
    channelNode.appendChild(xmlCreateTag(document, 'pubDate', "Sat, 28 Jan 2023 02:02:00 -0800"))
    channelNode.appendChild(xmlCreateTag(document, 'copyright', "Copyright ..."))
    channelNode.appendChild(xmlCreateTag(document, 'category', "Religion"))
    channelNode.appendChild(xmlCreateTag(document, 'ttl', "1440"))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:type', "episodic"))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:subtitle', "Subtitle..."))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:summary', "Summary..."))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:author', "Paul White Ministries2"))

    nodeOwner = document.createElement('itunes:owner')
    nodeOwner.appendChild(xmlCreateTag(document, 'itunes:name', "Paul White Ministries3"))
    channelNode.appendChild(nodeOwner)

    channelNode.appendChild(xmlCreateTag(document, 'itunes:block', "No"))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:explicit', "no"))
    channelNode.appendChild(xmlCreateTag(document, 'itunes:image', text=None, attributes={'href': "https://deow9bq0xqvbj.cloudfront.net/image-logo/131712/PWM_Logo_iTunes_x89qaz.jpg"}))

    imageNode = document.createElement('image')
    imageNode.appendChild(xmlCreateTag(document, 'url', "https://deow9bq0xqvbj.cloudfront.net/image-logo/131712/PWM_Logo_iTunes_x89qaz.jpg"))
    imageNode.appendChild(xmlCreateTag(document, 'title', "Paul White Ministries4"))
    imageNode.appendChild(xmlCreateTag(document, 'link', "http://www.paulwhiteministries.org"))
    imageNode.appendChild(xmlCreateTag(document, 'width', "144"))
    imageNode.appendChild(xmlCreateTag(document, 'height', "144"))          
    channelNode.appendChild(imageNode)            

    for episode in episodesJson:
        episodeNode = xmlCreateNodeEpisode(document, episode)
        channelNode.appendChild(episodeNode)

    return channelNode

def xmlCreateNodeRss(document, episodesJson):
    rssNode = document.createElement('rss')
    rssNode.setAttribute('version', '2.0')
    rssNode.setAttribute('xmlns:content', "http://purl.org/rss/1.0/modules/content/")
    rssNode.setAttribute('xmlns:wfw', "http://wellformedweb.org/CommentAPI/")
    rssNode.setAttribute('xmlns:dc', "http://purl.org/dc/elements/1.1/")
    rssNode.setAttribute('xmlns:atom', "http://www.w3.org/2005/Atom")
    rssNode.setAttribute('xmlns:itunes', "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rssNode.setAttribute('xmlns:googleplay', "http://www.google.com/schemas/play-podcasts/1.0")
    rssNode.setAttribute('xmlns:spotify', "http://www.spotify.com/ns/rss")
    rssNode.setAttribute('xmlns:podcast', "https://podcastindex.org/namespace/1.0")
    rssNode.setAttribute('xmlns:media', "http://search.yahoo.com/mrss/")

    channelNode = xmlCreateNodeChannel(document, episodesJson)
    rssNode.appendChild(channelNode)

    return rssNode
  
def savePodcastsForMonth(year, month):
    print(f'Yesr: {year}, month: {month}')
    allPagesHtml = webGetAllPagesForMonthAsHtml(year, month)
    allEpisodesJson = pwGetEpisodesFromAllPagesAsJson(allPagesHtml)

    allEpisodesXml = pwEpisodesJsonToXmlFeed(allEpisodesJson)

    with open(f'output/paulwhite_{year}_{month}.xml', 'w', encoding='utf8') as f:
        f.write(allEpisodesXml)        
 
def main ():
    #aLREADY DONE
    # for month in ['05', '06', '07', '08', '09', '10', '11', '12']:
        # savePodcastsForMonth('2009', month)    

    #aLREADY DONE
    # for year in['2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022']:
        # for month in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
            # savePodcastsForMonth(year, month)

    savePodcastsForMonth('2023', '01')          


main() 

