# python 3.11
import sys
import time
import pypinyin
import requests
import concurrent.futures
from configparser import ConfigParser
from pathlib import Path


TAGS = {
    "Anime": "动画", "Action": "动作", "Mystery": "悬疑", "Tv Movie": "电视", "Animation": "动画",
    "Crime": "犯罪", "Family": "家庭", "Fantasy": "奇幻", "Disaster": "灾难", "Adventure": "冒险",
    "Short": "短片", "Horror": "恐怖", "History": "历史", "Suspense": "悬疑", "Biography": "传记",
    "Sport": "体育", "Comedy": "喜剧", "Romance": "爱情", "Thriller": "惊悚", "Documentary": "纪录",
    "Music": "音乐", "Sci-Fi": "科幻", "Western": "西部", "Children": "儿童", "Martial Arts": "功夫",
    "Drama": "剧情", "War": "战争", "Musical": "音乐", "Film-noir": "黑色", "Science Fiction": "科幻",
    "Food": "食物", "War & Politics": "战争与政治", "Sci-Fi & Fantasy": "科幻", "Mini-Series": "迷你剧",
    "Rap": "说唱"
}

TYPE = {"movie": 1, "show": 2, "artist": 8}

config_file: Path = Path(__file__).parent / 'config.ini'

SELECT = (None, None)

def threads(datalist, func, thread_count):
    """
    多线程处理模块
    :param datalist: 待处理数据列表
    :param func: 处理函数
    :param thread_count: 运行线程数
    :return:
    """

    def chunks(lst, n):
        """列表切片工具"""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    chunk_size = (len(datalist) + thread_count - 1) // thread_count  # 计算每个线程需要处理的元素数量
    list_chunks = list(chunks(datalist, chunk_size))  # 将 datalist 切分成 n 段
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        result_items = list(executor.map(func, [item for chunk in list_chunks for item in chunk]))
        
    return result_items


def has_chinese(string):
    """判断是否有中文"""
    for char in string:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False


def convert_to_pinyin(text):
    """将字符串转换为拼音首字母形式。"""
    str_a = pypinyin.pinyin(text, style=pypinyin.FIRST_LETTER)
    str_b = [str(str_a[i][0]).upper() for i in range(len(str_a))]
    return ''.join(str_b).replace("：", ":").replace("（", "(").replace("）", ")").replace("，", ",")


class PlexServer:

    def __init__(self, host=None, token=None):
        cfg = ConfigParser()
        self.s = requests.session()

        if host and token:
            self.host = host
            self.token = token
            print(f"已成功连接到服务器{self.login()}")
        else:
            try:
                cfg.read(config_file)
                self.host = dict(cfg.items("server"))["host"]
                self.token = dict(cfg.items("server"))["token"]
                print(f"已成功连接到服务器{self.login()}")
            except Exception as error:
                print(error)
                print("\n[WARNING] 配置文件读取失败，开始创建配置文件：\n")
                self.host = input('请输入你的 PLEX 服务器地址 ( 例如 http://127.0.0.1:32400 )：') or "http://127.0.0.1:32400"
                if self.host[-1] == "/":
                    self.host = self.host[:-1]
                self.token = input(
                    '请输入你的 TOKEN'
                    r'（如果是windows服务器，可查看注册表\"计算机\HKEY_CURRENT_USER\Software\Plex, Inc.\Plex Media Server\"）\n'
                    '请输入：'
                )
                try:
                    cfg.add_section("server")
                    cfg.set("server", "host", self.host)
                    cfg.set("server", "token", self.token)
                    with open(config_file, 'w') as f:
                        cfg.write(f)
                    print(f"\n[INFO] 配置文件已写入 {config_file} ，请重新运行脚本。\n")
                except Exception as error:
                    print(error)
                    print("\n[WARNING] 配置文件写入失败\n")

    def login(self):
        try:
            self.s.headers = {'X-Plex-Token': self.token, 'Accept': 'application/json'}
            friendly_name = self.s.get(url=self.host, ).json()['MediaContainer']['friendlyName']
            return friendly_name
        except Exception as e:
            print(e)
            print("\n[WARNING] 服务器连接不成功，请检查配置文件是否正确。\n")
            time.sleep(10)
            return sys.exit()

    def select_library(self):
        """列出并选择库"""
        data = self.s.get(
            url=f"{self.host}/library/sections/"
        ).json().get("MediaContainer", {}).get("Directory", [])

        library = [
            "{}> {}".format(i, data[i]["title"])
            for i in range(len(data))
        ]

        index = int(input("\n".join(library) + "\n请选择库："))
        action_key = data[index]['key']
        action_type = int(input("\n1> 电影\n2> 节目\n8> 艺术家\n9> 专辑\n10> 单曲\n请选择要操作的类型："))

        return action_key, action_type

    def list_media_keys(self, select):
        datas = \
            self.s.get(url=f'{self.host}/library/sections/{select[0]}/all?type={select[1]}').json()["MediaContainer"][
                "Metadata"]
        media_keys = [data["ratingKey"] for data in datas]
        print(F"共计{len(media_keys)}个媒体")
        return media_keys

    def get_metadata(self, rating_key):
        metadata = self.s.get(url=f'{self.host}/library/metadata/{rating_key}').json()["MediaContainer"]["Metadata"][0]
        return metadata

    def put_title_sort(self, select, rating_key, sort_title, lock):
        self.s.put(
            url=f"{self.host}/library/sections/{select[0]}/all",
            params={
                "type": select[1],
                "id": rating_key,
                "includeExternalMedia": 1,
                "titleSort.value": sort_title,
                "titleSort.locked": lock
            }
        )

    def put_genres(self, select, rating_key, tag, addtag):
        """变更分类标签。"""
        res = self.s.put(url=f"{self.host}/library/sections/{select[0]}/all",
                         params={
                             "type": select[1],
                             "id": rating_key,
                             "genre.locked": 1,
                             "genre[0].tag.tag": addtag,
                             "genre[].tag.tag-": tag
                         }).text
        return res

    def put_styles(self, select, rating_key, tag, addtag):
        """变更风格标签。"""
        res = self.s.put(url=f"{self.host}/library/sections/{select[0]}/all",
                         params={
                             "type": select[1],
                             "id": rating_key,
                             "style.locked": 1,
                             "style[0].tag.tag": addtag,
                             "style[].tag.tag-": tag
                         }).text
        return res

    def put_mood(self, select, rating_key, tag, addtag):
        """变更情绪标签。"""
        res = self.s.put(url=f"{self.host}/library/sections/{select[0]}/all",
                         params={
                             "type": select[1],
                             "id": rating_key,
                             "mood.locked": 1,
                             "mood[0].tag.tag": addtag,
                             "mood[].tag.tag-": tag
                         }).text
        return res

    def do_item(self, rating_key):

        metadata = self.get_metadata(rating_key)
        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        genres = [genre.get("tag") for genre in metadata.get('Genre', {})]
        styles = [style.get("tag") for style in metadata.get('Style', {})]
        moods = [mood.get("tag") for mood in metadata.get('Mood', {})]

        global SELECT
        select = SELECT

        if select[1] != 10:
            if has_chinese(title_sort) or title_sort == "":
                title_sort = convert_to_pinyin(title)
                self.put_title_sort(select, rating_key, title_sort, 1)
                print(f"{title} < {title_sort} >")

        if select[1] != 10:
            for genre in genres:
                if new_genre := TAGS.get(genre):
                    self.put_genres(select, rating_key, genre, new_genre)
                    print(f"{title} : {genre} → {new_genre}")

        if select[1] in [8, 9]:
            for style in styles:
                if new_style := TAGS.get(style):
                    self.put_styles(select, rating_key, style, new_style)
                    print(f"{title} : {style} → {new_style}")

        if select[1] in [8, 9, 10]:
            for mood in moods:
                if new_mood := TAGS.get(mood):
                    self.put_styles(select, rating_key, mood, new_mood)
                    print(f"{title} : {mood} → {new_mood}")

    def loop_all(self):
        """选择一个媒体库并遍历其中的每一个媒体。"""

        global SELECT
        SELECT = self.select_library()
        media_keys = self.list_media_keys(SELECT)

        thread_count = input("\n请输入运行的线程数（输入整数数字，默认为2）：")
        thread_count = int(thread_count if thread_count else 2)

        t = time.time()
        threads(media_keys, self.do_item, thread_count)

        # for rating_key in media_keys:
        #     metadata = self.get_metadata(rating_key)
        #     title = metadata["title"]
        #     title_sort = metadata.get("titleSort", "")
        #     genres = [genre.get("tag") for genre in metadata.get('Genre', {})]
        #     styles = [style.get("tag") for style in metadata.get('Style', {})]
        #     moods = [mood.get("tag") for mood in metadata.get('Mood', {})]
        #
        #     if select[1] != 10:
        #         if has_chinese(title_sort) or title_sort == "":
        #             title_sort = convert_to_pinyin(title)
        #             self.put_title_sort(select, rating_key, title_sort, 1)
        #             print(f"{title} < {title_sort} >")
        #
        #     if select[1] != 10:
        #         for genre in genres:
        #             if new_genre := TAGS.get(genre):
        #                 self.put_genres(select, rating_key, genre, new_genre)
        #                 print(f"{title} : {genre} → {new_genre}")
        #
        #     if select[1] in [8, 9]:
        #         for style in styles:
        #             if new_style := TAGS.get(style):
        #                 self.put_styles(select, rating_key, style, new_style)
        #                 print(f"{title} : {style} → {new_style}")
        #
        #     if select[1] in [8, 9, 10]:
        #         for mood in moods:
        #             if new_mood := TAGS.get(mood):
        #                 self.put_styles(select, rating_key, mood, new_mood)
        #                 print(f"{title} : {mood} → {new_mood}")

        print(F'运行完毕，用时 {time.time() - t} 秒')


if __name__ == '__main__':
    if arg := sys.argv:
        # 示例 python plex_localization_zhcn.py http://192.168.3.2:32400 cRBnx9eQDgGy9zs4G-7F 1 1 1
        PlexServer(arg[1], arg[2]).loop_all(int(arg[3]), int(arg[4]), int(arg[5]))
    else:
        PlexServer().loop_all()
