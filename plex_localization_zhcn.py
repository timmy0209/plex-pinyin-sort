# python 3.9
import sys
import time
from urllib import parse
from configparser import ConfigParser
import pypinyin
import requests
from pathlib import Path

iniflie: Path = Path(__file__).parent / 'config.ini'

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


class plexserver:

    def __init__(self):

        cfg = ConfigParser()
        try:
            with open(iniflie, 'r') as f:
                cfg.read(f)
            config = dict(cfg.items("server"))
            self.host = config["host"]
            self.token = config["token"]
        except:
            print("\n[WARNING] 未找到配置文件，请手动输入。\n")
            self.host = input('请输入你的 PLEX 服务器地址 ( 例如 http://127.0.0.1:32400 )：') or "http://127.0.0.1:32400"
            self.token = input(
                '请输入你的 TOKEN'
                '（如果是windows服务器，可查看注册表\"计算机\HKEY_CURRENT_USER\Software\Plex, Inc.\Plex Media Server\"）\n'
                '请输入：'
            )

        if self.host[-1] == "/":
            self.host = self.host[:-1]
        print(self.host)

        try:
            friendlyName = requests.get(
                url=self.host,
                headers={'X-Plex-Token': self.token, 'Accept': 'application/json'}
            ).json()['MediaContainer']['friendlyName']
            yesno = input(f"已成功连接到服务器{friendlyName}，是否将配置写入文件保存？（y/n）")
        except:
            print("\n[WARNING] 服务器连接不成功，请检查配置文件是否正确。\n")
            time.sleep(15)
            sys.exit()

        try:
            if yesno == "y":
                cfg.add_section("server")
                cfg.set("server", "host", self.host)
                cfg.set("server", "token", self.token)
                with open(iniflie, 'w') as f:
                    cfg.write(f)
                print(f"\n[INFO] 配置文件已写入{iniflie}\n")
        except:
            print("\n[WARNING] 配置文件写入失败\n")

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
        sorttitle = parse.quote(sorttitle.encode('utf-8'))
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
                zh_query = parse.quote(zh_query.encode('utf-8'))
                enggenre = parse.quote(enggenre.encode('utf-8'))
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
    plexserver().LoopAll()
