功能说明：
    下载单个或批量视频；
    下载后视频存放目录在当前项目 output 目录下，每个视频默认以视频名称命名;
    如果没有登录过 B 站，程序会先弹出二维码扫码登录 B站，保存cookie到 cookies目录下，后续不用重复登录.(还不确定cookie多久有效)；
    要下载的视频url 配置在 download_list.json中, 示例如下：
            示例中"13-15"是下载这个视频url的第13到第15集；视频链接中已经有"p="指示第几集时，这个参数写空串；
            {
                "download_list": [

                    [
                      "https://www.bilibili.com/video/BV1t2x5zBEUH/?spm_id_from=333.788.videopod.episodes&vd_source=5790f8639591db2f08b72721a5b723b3",
                      "13-15"
                    ]

              ]
            }
环境配置：
    除了安装 python 依赖库，运行缺啥装啥，记得装ffmpeg: brew install ffmpeg

运行操作：
    配置视频url到 download_list.json 中；
    运行 main_dowload_video.py，进行下载；


优点：（对比世面上已有的视频下载软件，如 https://snapany.com/zh/bilibili ）
    1. 可以成功下载“哆啦 A梦”这种m3u8格式的视频； https://www.bilibili.com/bangumi/play/ep315112?spm_id_from=333.337.0.0
    2. 可以批量下载，而且可以自动命名；而不是手动一个个复制链接点击下载跳转后再选择下载按钮、下载后再重命名；
    3. 可以视频和音频分开下载；应用场景如：将音频单独下载下来，再用whisper模型，语音转文字识别出音频的原字幕；


已测情况：
    1. 可以成功批量下载 B 站视频
    2. 需要大会员才能完整观看的视频，就只能下载免费的那几分钟，没有会员，没法下只有会员才能看的部分；