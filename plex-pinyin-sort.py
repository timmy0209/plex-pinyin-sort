## python 3
# pip install plexapi
# 更多中文插件请访问plexmedia.cn

import urllib
import http.client
import json
import sys
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from plexapi.myplex import MyPlexDevice


PLEX_TOKEN = ""

def fetchPlexApi(path='', method='GET', getFormPlextv=False, token=PLEX_TOKEN, params=None):
        """a helper function that fetches data from and put data to the plex server"""
        #print(path)
        headers = {'X-Plex-Token': token,
                'Accept': 'application/json'}
        if getFormPlextv:
            url = 'plex.tv'        
            connection = http.client.HTTPSConnection(url)
        else:
            url = PLEX_URL.rstrip('/').replace('http://','')     
            connection = http.client.HTTPConnection(url)
        try:
            if method.upper() == 'GET':
                pass
            elif method.upper() == 'POST':
                headers.update({'Content-type': 'application/x-www-form-urlencoded'})
                pass
            elif method.upper() == 'PUT':
                pass
            elif method.upper() == 'DELETE':
                pass
            else:
                print("Invalid request method provided: {method}".format(method=method))
                connection.close()
                return

            connection.request(method.upper(), path , params, headers)     
            response = connection.getresponse()         
            r = response.read()             
            contentType = response.getheader('Content-Type')      
            status = response.status    
            connection.close()

            if response and len(r):     
                if 'application/json' in contentType:         
                    return json.loads(r)
                elif 'application/xml' in contentType:
                    return xmltodict.parse(r)
                else:
                    return r
            else:
                return r

        except Exception as e:
            connection.close()
            print("Error fetching from Plex API: {err}".format(err=e))

def updateSortTitle(rating,item):
    sortQuery =urllib.parse.quote(item.encode('utf-8'))                                
    data = fetchPlexApi("/library/sections/"+sectionNum+"/all?type=1&id=%s&titleSort.value=%s&"%(rating,sortQuery), "PUT",token=PLEX_TOKEN) 

def uniqify(seq):
    # Not order preserving
    keys = {}
    for e in seq:
        keys[e] = 1
    return keys.keys()
def check_contain_chinese(check_str):                           #判断是否包含中文字符
     for ch in check_str:
         if '\u4e00' <= ch <= '\u9fff':
             return True
     return False
def changepinyin (title):
    a = pypinyin.pinyin(title, style=pypinyin.FIRST_LETTER)
    b = []
    for i in range(len(a)):
        b.append(str(a[i][0]).upper())
    c = ''.join(b)
    return c
def loopThroughAllMovies():
    toDo = True
    start = 0
    size = 100
    while toDo:
        if len(sectionNum):
            url = "/library/sections/" + sectionNum + "/all?type=1&X-Plex-Container-Start=%i&X-Plex-Container-Size=%i" % (start, size)
            metadata = fetchPlexApi(url,token=PLEX_TOKEN)
            container = metadata["MediaContainer"]
            elements = container["Metadata"]
            totalSize = container["totalSize"]
            offset = container["offset"]
            size = container["size"]      
            start = start + size        
            if totalSize-offset-size == 0:
                toDo = False
            #    print(toDo)
            # loop through all elements
            for movie in elements:
                mediaType = movie["type"]
                if mediaType != "movie":
                    continue
                if 'titleSort' in movie:                        #判断是否已经有标题
                    con = movie["titleSort"]
                    if (check_contain_chinese(con)):
                            continue
                    continue
                key = movie["ratingKey"]        
                title = movie["title"]
                SortTitle = changepinyin(title)
                print(title)
                updateSortTitle(key, SortTitle)
                
if __name__ == '__main__':

    #got token.url
    print("欢迎使用PLEX中文排序，使用方法请访问：")
    PLEX_URL = input('请输入你的plex服务器地址：')
    PLEX_TOKEN = input('请输入你的token：')
    # the plex server url
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    for section in plex.library.sections():
            if section.type == 'movie':
               print(section)

    #choose list
    sectionNum = input('请输入你要排序的电影库编号：')
    

    # run at startup
    loopThroughAllMovies()
    

