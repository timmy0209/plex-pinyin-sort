# python 3.9
import sys
import time
from configparser import ConfigParser
import pypinyin
import requests
from pathlib import Path

cfgflie: Path = Path(__file__).parent / 'config.ini'


TAGS = {
    "Anime": "动画",     "Action": "动作",     "Mystery": "悬疑",     "Tv Movie":  "电视",     "Animation":       "动画",
    "Crime": "犯罪",     "Family": "家庭",     "Fantasy": "奇幻",     "Disaster":  "灾难",     "Adventure":       "冒险",
    "Short": "短片",     "Horror": "恐怖",     "History": "历史",     "Suspense":  "悬疑",     "Biography":       "传记",
    "Sport": "体育",     "Comedy": "喜剧",     "Romance": "爱情",     "Thriller":  "惊悚",     "Documentary":     "纪录",
    "Music": "音乐",     "Sci-Fi": "科幻",     "Western": "西部",     "Children":  "儿童",     "Martial Arts":    "功夫",
    "Drama": "剧情",     "War":    "战争",     "Musical": "音乐",     "Film-noir": "黑色",     "Science Fiction": "科幻",
    "Food":  "食物",     "War & Politics": "战争与政治",     "Sci-Fi & Fantasy": "科幻",        "Mini-Series": "迷你剧",
    "Rap": "说唱"
}


def hasChinese(string):
    """判断是否有中文"""
    for char in string:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


def convertToPinyin(text):
    """将字符串转换为拼音首字母形式。"""
    str_a = pypinyin.pinyin(text, style=pypinyin.FIRST_LETTER)
    str_b = [str(str_a[i][0]).upper() for i in range(len(str_a))]
    return ''.join(str_b).replace("：",":").replace("（","(").replace("）",")").replace("，",",")


class plexserver:

    def __init__(self):
        cfg = ConfigParser()
        self.s = requests.session()

        try:
            cfg.read(cfgflie)
            config = dict(cfg.items("server"))
            self.host = config["host"]
            self.token = config["token"]
            print(f"已成功连接到服务器{self.login()}")
        except:
            print("\n[WARNING] 未找到配置文件，请手动输入。\n")
            self.host = input('请输入你的 PLEX 服务器地址 ( 例如 http://127.0.0.1:32400 )：') or "http://127.0.0.1:32400"
            if self.host[-1] == "/":
                self.host = self.host[:-1]
            self.token = input(
                '请输入你的 TOKEN'
                '（如果是windows服务器，可查看注册表\"计算机\HKEY_CURRENT_USER\Software\Plex, Inc.\Plex Media Server\"）\n'
                '请输入：'
            )
            yesno = input(f"已成功连接到服务器{self.login()}，是否将配置写入文件保存？（y/n）")
            try:
                if yesno == "y":
                    cfg.add_section("server")
                    cfg.set("server", "host", self.host)
                    cfg.set("server", "token", self.token)
                    with open(cfgflie, 'w') as f:
                        cfg.write(f)
                    print(f"\n[INFO] 配置文件已写入{cfgflie}\n")
            except:
                print("\n[WARNING] 配置文件写入失败\n")


    def login(self):
        try:
            self.s.headers = {'X-Plex-Token': self.token, 'Accept': 'application/json'}
            friendlyName = self.s.get(url=self.host,).json()['MediaContainer']['friendlyName']
            return friendlyName
        except:
            print("\n[WARNING] 服务器连接不成功，请检查配置文件是否正确。\n")
            time.sleep(10)
            return sys.exit()


    def selectLibrary(self):
        """列出并选择库"""
        data = self.s.get(
            url=f"{self.host}/library/sections/"
        ).json().get("MediaContainer", {}).get("Directory", [])

        library = [
            "{}> {}: {}".format(i, data[i]["type"], data[i]["title"])
            for i in range(len(data))
        ]

        index = int(input("\n".join(library) + "\n请选择要操作的库："))
        actionKey = data[index]['key']
        if data[index]['type'] == "movie":
            actionType = 1
        elif data[index]['type'] == "show":
            actionType = 2
        elif data[index]['type'] == "artist":
            actionType = 8
        else:
            print("暂不支持" + data[index]['type'] + "类型, 5 秒后关闭")
            time.sleep(5)
            sys.exit()
        return actionKey,actionType


    def listMediaKeys(self, key):
        datas = self.s.get(url=f'{self.host}/library/sections/{key}/all').json()["MediaContainer"]["Metadata"]
        mediaKeys = [data["ratingKey"] for data in datas]
        print(F"共计{len(mediaKeys)}个媒体")
        return mediaKeys


    def getMetadata(self, ratingkey):
        metadata = self.s.get(url=f'{self.host}/library/metadata/{ratingkey}').json()["MediaContainer"]["Metadata"][0]
        return metadata


    def putTitleSort(self, select, ratingkey, sorttitle, lock):
        self.s.put(
            url=f"{self.host}/library/sections/{select[0]}/all",
            params={
                "type":select[1],
                "id":ratingkey,
                "includeExternalMedia":1,
                "titleSort.value":sorttitle,
                "titleSort.locked": lock
            }
        )


    def putGenres(self, select, ratingkey, tag, addtag):
        """变更分类标签。"""
        res = self.s.put(url=f"{self.host}/library/sections/{select[0]}/all",
            params={
                "type":select[1],
                "id":ratingkey,
                "genre[0].tag.tag":addtag,
                "genre[].tag.tag-":tag
            }).text
        print(res)

    def LoopAll(self):
        """选择一个媒体库并遍历其中的每一个媒体。"""

        select = self.selectLibrary()
        mediaKeys = self.listMediaKeys(select[0])

        for ratingkey in mediaKeys:
            metadata = self.getMetadata(ratingkey)
            title = metadata["title"]
            titlesort = metadata.get("titleSort", "")
            taglist = [genre.get("tag") for genre in metadata.get('Genre',{})]

            if hasChinese(titlesort) or titlesort == "":
            # if True:
                titlesort = convertToPinyin(title)
                self.putTitleSort(select, ratingkey, titlesort, 1)
                print(f"{title} < {titlesort} >")

            for tag in taglist:
                if newtag:=TAGS.get(tag):
                    self.putGenres(select, ratingkey, tag, newtag)
                    print(f"{title} : {tag} → {newtag}")


if __name__ == '__main__':
    plexserver().LoopAll()
