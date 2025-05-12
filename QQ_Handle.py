# 用于下载QQ群内放出的崩溃压缩文件，尝试解压并分析这个文件夹，一次只能分析一个，解压到一个缓存文件夹
# 压缩文件名的格式类似为“错误报告-2025-3-29_14.49.17.zip”、“minecraft-exported-crash-info-2024-08-22T16-48-05.zip”
# 有些时候也会只提供一个小文件，例如“crash.txt”，“latest.log”，处理办法是依旧将其放入缓存文件夹
import os
import shutil
import zipfile
from typing import List, Dict

import requests as rq
# ========= 导入必要模块 ==========
from ncatbot.core import BotClient, GroupMessage
from ncatbot.utils import get_log

import main
import config_reader

cf = config_reader.Config()
file = None
cache_file = os.path.join(os.path.dirname(__file__), "cache")
working_list:List[Dict[GroupMessage,str]] = []
qq_id = cf.QQ_number

# ========== 创建 BotClient ==========
bot = BotClient()
_log = get_log()


# ========== 处理消息 ==========
@bot.group_event()
async def on_group_msg(msg: GroupMessage):
    if msg.group_id in cf.group_whitelist:
        message_segs = msg.message
        for message_seg in message_segs:
            if message_seg['type'] == "file":
                print("收到带文件的群消息:", msg)
                file_id = message_seg["data"]["file_id"]
                file_respond = await bot.api.get_file(file_id)
                file_source = file_respond["data"]["url"]
                file_size = int(message_seg["data"]["file_size"])
                print("文件的获取url是:", file_source)
                if file_size < 40 * 1024 * 1024 and file_source.endswith(('.log', '.txt', '.zip')):
                    working_list.append({msg: file_source})
                    await handle_crash_file()
                else:
                    print("文件过大或格式不正确，无法处理", file_size,"and", file_source)

# 处理崩溃文件
async def handle_crash_file():
    global working_list
    for file in working_list:
        for msg, file_source in file.items():
            print("下载文件:", file_source)
            if await download_file(file_source):
                # 下载成功后，开始检查崩溃文件
                print("下载完成，开始检查崩溃文件")
                result = await start_check()
                print("检查完成，结果:", result)
                # 检查完成后，发送结果
                if result != "NULL":
                    await msg.reply(text=result, is_file=False)
    working_list = []

# 异步下载和解压文件
async def download_file(file_source) -> bool:
    try:
        # 清空缓存目录
        if os.path.exists(cache_file):
            shutil.rmtree(cache_file)
        os.makedirs(cache_file, exist_ok=True)
        if os.path.exists(file_source):
            # 复制文件到缓存文件夹
            shutil.copy(file_source, os.path.join(cache_file, os.path.basename(file_source)))
            return True
        else:
            # 下载文件
            response = rq.get(file_source)
            if response.status_code == 200:
                with open(os.path.join(cache_file, os.path.basename(file_source)), 'wb') as f:
                    f.write(response.content)
                print("文件下载成功")
                # 解压缩文件
                if file_source.endswith('.zip'):
                    return unzip_file(os.path.join(cache_file, os.path.basename(file_source)), cache_file)
                else:
                    print("文件下载成功，文件已保存到缓存文件夹")
                    return True
            else:
                print("文件下载失败")
                return False
    except Exception as e:
        print(f"下载文件时发生错误: {e}")
        return False

# 开始检查崩溃文件
async def start_check():
    return main.start_analyzer(cache_file)


def unzip_file(file, extract_to: str) -> bool:
    """解压缩文件到指定目录"""
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"解压缩完成，文件已保存到 {extract_to}")
        return True
    except Exception as e:
        print(f"解压缩失败: {e}")
        return False

if __name__ == "__main__":
    try:
        bot.run(bt_uin=qq_id,ws_uri=cf.ws_uri)  # 这里写 Bot 的 QQ 号
    except Exception as e:
        print(f"An error occurred: {e}")
