# python 3.9
import sys
import time
from configparser import ConfigParser
import pypinyin
import requests
from pathlib import Path
import concurrent.futures

TAGS = {
    "Anime": "动画", "Action": "动作", "Mystery": "悬疑", "Tv Movie": "电视", "Animation": "动画",
    "Crime": "犯罪", "Family": "家庭", "Fantasy": "奇幻", "Disaster": "灾难", "Adventure": "冒险",
    "Short": "短片", "Horror": "恐怖", "History": "历史", "Suspense": "悬疑", "Biography": "传记",
    "Sport": "体育", "Comedy": "喜剧", "Romance": "爱情", "Thriller": "惊悚", "Documentary": "纪录",
    "Music": "音乐", "Sci-Fi": "科幻", "Western": "西部", "Children": "儿童", "Martial Arts": "功夫",
    "Drama": "剧情", "War": "战争", "Musical": "音乐", "Film-noir": "黑色", "Science Fiction": "科幻",
    "Food": "食物", "War & Politics": "战争与政治", "Sci-Fi & Fantasy": "科幻", "Mini-Series": "迷你剧",
    "Rap": "说唱", "Adult": "成人"
}

config_file: Path = Path(__file__).parent / 'config.ini'

types = {"movie": 1, "show": 2, "artist": 8, "album": 9, 'track': 10}
TYPES = {"movie": [1], "show": [2], "artist": [8, 9, 10]}


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
                self.host = input(
                    '请输入你的 PLEX 服务器地址 ( 例如 http://127.0.0.1:32400 )：') or "http://127.0.0.1:32400"
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

    def list_libraries(self):
        data = self.s.get(url=f"{self.host}/library/sections/").json().get("MediaContainer", {}).get("Directory", [])

        return {
            int(x['key']): (int(x['key']), TYPES[x['type']], x['title'], x['type'])
            for x in data
            if x['type'] != 'photo'  # 排除照片库
        }

    def select_library(self, index=None):
        """列出并选择库"""
        libraries = self.list_libraries()

        echo = [f"{library[0]}> {library[2]} <{library[3]}>" for library in libraries.values()]

        index = index if index else int(input("\n" + "\n".join(echo) + "\n请选择库："))

        action_key, action_type = index, libraries[index][1]

        return action_key, action_type

    def list_keys(self, select, is_coll: bool):
        types_index = {value: key for key, value in types.items()}

        endpoint = f'sections/{select[0]}/collections' if is_coll else f'sections/{select[0]}/all?type={select[1]}'
        datas = self.s.get(f'{self.host}/library/{endpoint}').json().get("MediaContainer", {}).get("Metadata", [])
        keys = [data.get("ratingKey") for data in datas]

        if len(keys):
            if is_coll:
                print(F"\n<{types_index[select[1]]}> 类型共计{len(keys)}个合集")
            else:
                print(F"\n<{types_index[select[1]]}> 类型共计{len(keys)}个媒体")

        return keys

    def get_metadata(self, rating_key):
        return self.s.get(url=f'{self.host}/library/metadata/{rating_key}').json()["MediaContainer"]["Metadata"][0]

    def put_title_sort(self, select, rating_key, sort_title, lock, is_coll: bool):
        endpoint = f'library/metadata/{rating_key}' if is_coll else f'library/sections/{select[0]}/all'
        self.s.put(
            url=f"{self.host}/{endpoint}",
            params={
                "type": select[1],
                "id": rating_key,
                "includeExternalMedia": 1,
                "titleSort.value": sort_title,
                "titleSort.locked": lock
            }
        )

    def put_tag(self, select, rating_key, tag, addtag, tag_type, title):
        self.s.put(
            url=f"{self.host}/library/sections/{select[0]}/all",
            params={
                "type": select[1],
                "id": rating_key,
                f"{tag_type}.locked": 1,
                f"{tag_type}[0].tag.tag": addtag,
                f"{tag_type}[].tag.tag-": tag
            }
        )
        print(f"{title} : {tag} → {addtag}")

    def operate_item(self, rating_key):

        metadata = self.get_metadata(rating_key)

        library_id = metadata['librarySectionID']

        is_coll, type_id = (False, types[metadata['type']]) \
            if metadata['type'] != 'collection' \
            else (True, types[metadata['subtype']])

        title = metadata["title"]
        title_sort = metadata.get("titleSort", "")
        tags: dict[str:list] = {
            'genre': [genre.get("tag") for genre in metadata.get('Genre', {})],  # 流派
            'style': [style.get("tag") for style in metadata.get('Style', {})],  # 风格
            'mood': [mood.get("tag") for mood in metadata.get('Mood', {})]  # 情绪
        }

        select = library_id, type_id

        # 更新标题排序
        if has_chinese(title_sort) or title_sort == "":
            title_sort = convert_to_pinyin(title)
            self.put_title_sort(select, rating_key, title_sort, 1, is_coll)
            print(f"{title} < {title_sort} >")

        # 汉化标签
        for tagtpye, tag_list in tags.items():
            if tag_list:
                for tag in tag_list:
                    self.put_tag(select, rating_key, tag, newtag, tagtpye, title) if (newtag := TAGS.get(tag)) else None

    def loop_all(self, library_id: int = None, thread_count: int = None):
        """选择媒体库并遍历其中的每一个媒体。"""
        if not thread_count:
            thread_count = input("\n请输入运行的线程数（输入整数数字，默认为2）：")
            thread_count = int(thread_count if thread_count else 2)

        if library_id == 999:
            libraries = self.list_libraries()

            t = time.time()

            for library in libraries:
                for type_id in library[1]:
                    for is_coll in [False, True]:
                        if keys := self.list_keys((library[0], type_id), is_coll):
                            threads(keys, self.operate_item, thread_count)

            print(F'\n运行完毕，用时 {time.time() - t} 秒')

        else:
            library_id, type_ids = self.select_library(library_id) if library_id else self.select_library()

            t = time.time()

            for type_id in type_ids:
                for is_coll in [False, True]:
                    if keys := self.list_keys((library_id, type_id), is_coll):
                        threads(keys, self.operate_item, thread_count)

            print(F'\n运行完毕，用时 {time.time() - t} 秒')


if __name__ == '__main__':

    if len(arg := sys.argv) == 5:
        # 指定配置、库索引、线程数
        PlexServer(arg[1], arg[2]).loop_all(int(arg[3]), int(arg[4]))
    elif 1 < len(arg := sys.argv) < 5:
        print('传入参数不完整。')
    else:
        PlexServer().loop_all()
