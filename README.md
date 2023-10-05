# PLEX 中文本地化

- 实现除照片外，所有类型媒体库按标题拼音首字母排序。
- 实现除照片外，所有类型媒体库类别标签更改中文。
- 实现保存配置文件简化下次运行流程。
- 支持多线程

plex 的中文电影默认排序是按照笔画数排的，对检索中文电影十分不友好，运行此脚本后可对指定电影库进行拼音排序，并可使用拼音首字母检索电影。

关于多线程的说明：
测试了数量为 170 的电影库，单线程用时 3.4943103790283203 秒，4线程用时 1.3947198390960693 秒

# 需要安装 pypinyin 模块

    pip install pypinyin
    
# Python 版本
- 仅在 3.11 版本完成测试
- 推测 3.9 版本可以支持，但未经测试。

# Todo

- [x] 移除 plexapi 库依赖
- [x] 更改排序为拼音后，锁定字段，避免刷新元数据时被更改
- [x] 支持存储配置文件以简化下次登录流程
- [x] 剧集类型库，解决部分标签无法翻译的问题
- [x] 增加音乐库艺术家类型支持
- [x] 增加音乐库专辑类型支持
- [x] 增加音乐库 风格(style)标签 支持
