# python 3.9
import sys
import time
import urllib
from urllib import parse
import pypinyin
import requests

tags = {
    "Anime": "动画",     "Action": "动作",     "Mystery": "悬疑",     "Tv Movie":  "电视",     "Animation":       "动画",
    "Crime": "犯罪",     "Family": "家庭",     "Fantasy": "奇幻",     "Disaster":  "灾难",     "Adventure":       "冒险",
    "Short": "短片",     "Horror": "恐怖",     "History": "历史",     "Suspense":  "悬疑",     "Biography":       "传记",
    "Sport": "体育",     "Comedy": "喜剧",     "Romance": "爱情",     "Thriller":  "惊悚",     "Documentary":     "纪录",
    "Music": "音乐",     "Sci-Fi": "科幻",     "Western": "西部",     "Children":  "儿童",     "Martial Arts":    "功夫",
    "Drama": "剧情",     "War":    "战争",     "Musical": "音乐",     "Film-noir": "黑色",     "Science Fiction": "科幻",
    "Food":  "食物",     "War & Politics": "战争与政治"
}


def hasChinese(text):
    """判断标题是否需要修改"""
    if text:
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                return True
            else:
                return False
    else:
        return True


def convertToPinyin(text):
    """将字符串转换为拼音首字母形式。"""
    str_a = pypinyin.pinyin(text, style=pypinyin.FIRST_LETTER)
    str_b = [str(str_a[i][0]).upper() for i in range(len(str_a))]
    return ''.join(str_b)


class PLEX:

    def __init__(self, host: str, token: str):
        """
        :param host: 可访问的 plex 服务器地址。例如 http://127.0.0.1:32400/
        :param token: 服务器的 token
        """
        self.host = host
        self.token = token
        self.actionType = None

    def listLibrary(self):
        """列出库"""
        data = requests.get(
            url=f"{self.host}/library/sections/",
            headers={'X-Plex-Token': self.token, 'Accept': 'application/json'},
        ).json().get("MediaContainer", {}).get("Directory", [])
        library = ["{}> {}: {}".format(i, data[i]["type"], data[i]["title"]) for i in range(len(data))]
        index = int(input("\n".join(library) + "\n请选择要操作的库："))
        if data[index]['type'] == "movie":
            self.actionType = 1
        elif data[index]['type'] == "show":
            self.actionType = 2
        else:
            print("暂不支持" + data[index]['type'] + "类型, 5 秒后关闭")
            time.sleep(5)
            sys.exit()
        return data[index]['key']

    def __convertSortTitle(self, libraryid, ratingkey, title):
        """如果标题排序为中文或为空，则将标题排序转换为中文首字母。"""
        sorttitle = convertToPinyin(title)
        print(f"{title} < {sorttitle} >")
        sorttitle = urllib.parse.quote(sorttitle.encode('utf-8'))
        requests.put(
            url=f"{self.host}/library/sections/{libraryid}/all",
            headers={'X-Plex-Token': self.token, 'Accept': 'application/json'},
            params={
                "type":{self.actionType},
                "id":{ratingkey},
                "includeExternalMedia":1,
                "titleSort.value":{sorttitle},
                "titleSort.locked": 1
            }
        )

    def __updataGenre(self, libraryid, ratingkey, title, genre):
        """变更分类标签。"""
        for tag in genre:
            enggenre = tag["tag"]
            if hasChinese(enggenre):
                continue
            zh_query = tags.get(tag["tag"])
            if zh_query:
                print(f"{title} : {enggenre} → {zh_query}")
                zh_query = urllib.parse.quote(zh_query.encode('utf-8'))
                enggenre = urllib.parse.quote(enggenre.encode('utf-8'))
                path = f"{self.host}/library/sections/{libraryid}/all?" \
                       f"type=1&id={ratingkey}&" \
                       f"genre%5B2%5D.tag.tag={zh_query}&genre%5B%5D.tag.tag-={enggenre}&"
                requests.put(
                    url=path,
                    headers={'X-Plex-Token': self.token, 'Accept': 'application/json'}
                )
            else:
                print(f"请在 TAGS 字典中，为 {enggenre} 标签添加对应的中文。")

    def LoopAll(self):
        """
        遍历指定媒体库中的每一个媒体。
        """
        key = self.listLibrary()
        todo, start, size = 1, 0, 100
        while todo != 0:
            path = f'{self.host}/library/sections/{key}/all?' \
                   f'type={self.actionType}&X-Plex-Container-Start={start}&X-Plex-Container-Size={size}'
            metadata: dict = requests.get(
                url=path,
                headers={'X-Plex-Token': self.token, 'Accept': 'application/json'}
            ).json()

            total_size = metadata["MediaContainer"]["totalSize"]
            offset = metadata["MediaContainer"]["offset"]
            size = metadata["MediaContainer"]["size"]

            start = start + size
            todo = total_size - offset - size

            # print(metadata["MediaContainer"])

            for media in metadata["MediaContainer"]["Metadata"]:
                ratingkey = media["ratingKey"]
                title = media["title"]
                titlesort = media.get("titleSort", "")
                genre = media.get('Genre')
                if hasChinese(titlesort):
                    self.__convertSortTitle(key, ratingkey, title)
                if genre:
                    self.__updataGenre(key, ratingkey, title, genre)


if __name__ == '__main__':
    URL = input('请输入你的 PLEX 服务器地址 ( 例如 http://127.0.0.1:32400 )：') or "http://127.0.0.1:32400"
    TOKEN = input('请输入你的 TOKEN：\n可查看windows注册表\"计算机\HKEY_CURRENT_USER\Software\Plex, Inc.\Plex Media Server\"')
    server = PLEX(URL, TOKEN)
    server.LoopAll()
