from asyncio import Lock
from os.path import dirname, join, exists
from urllib import response
from hoshino import Service,priv,aiorequests
from hoshino.util import FreqLimiter, DailyNumberLimiter
from hoshino.config import NICKNAME
from hoshino.typing import CQEvent
from aiocqhttp.exceptions import ActionFailed
from PIL import Image, ImageDraw,ImageFont
from io import BytesIO
import requests


import base64
import json
import time,calendar
import re
import sqlite3
import os
import toml

from . import xp
from . import alchemy_manual

# 导入配置文件
toml_config_path = join(dirname(__file__), 'config.toml')
config = toml.load(toml_config_path)
word2img_url = config['word2img_url']   # 文字 -> 图片 apiURL
img2img_url = config['img2img_url']     # 以图生图 apiURL
token = config['token'] # token
# 口令间隔时间(默认每 60 秒可以使用一次口令)
interval = FreqLimiter(config['interval'] )
# 每日口令使用次数(默认每天可以使用 20 次口令)
daily_limit_ = config['daily_limit']
daily_limit = DailyNumberLimiter(daily_limit_)


sv_help = '''
【AI绘图数据库】
-[上传[参数]]  上传图片和tag至数据库内, [参数]为ai绘图的指令
-[炼金手册[序号]]  查询炼金手册内容，[序号]为页数, 每页显示8张
-[查看配方[序号]]  查询炼金配方内容，[序号]为图片标签
-[使用配方[序号]]  使用炼金配方内容，[序号]为图片标签
-[删除配方[序号]]  删除炼金配方内容，[序号]为图片标签
PS:上传仅限管理员使用，删除仅限超级管理员使用
'''

sv = Service(
    name = 'AI绘图数据库',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #是否可见
    enable_on_default = True, #是否默认启用
    bundle = '娱乐', #属于哪一类
    help_ = sv_help #帮助文本
    )

ttf_font_path = join(dirname(__file__), 'SIMSUNB.TTF')

async def wordimage(word):
    bg = Image.new('RGB', (950,300), color=(255,255,255))
    font = ImageFont.truetype(ttf_font_path, 30)  # 设置字体和大小
    draw = ImageDraw.Draw(bg)
    draw.text((10,5), word, fill="#000000", font=font)
    result_buffer = BytesIO()
    bg.save(result_buffer, format='JPEG', quality=100)
    imgmes = 'base64://' + base64.b64encode(result_buffer.getvalue()).decode()
    resultmes = f"[CQ:image,file={imgmes}]"
    return resultmes

@sv.on_fullmatch(["绘图数据库帮助"])
async def bangzhu(bot, ev):
    await bot.send(ev, await wordimage(sv_help), at_sender=True)



@sv.on_fullmatch(['我的XP'])
async def get_my_xp(bot, ev: CQEvent):
    xp_list = xp.get_xp_list(ev.user_id)
    uid = ev.user_id
    msg = '您的XP信息为：\n'
    if len(xp_list)>0:
        for xpinfo in xp_list:
            keyword, num = xpinfo
            msg += f'关键词：{keyword}；查询次数：{num}\n'
    else:
        msg += '暂无您的XP信息'
    await bot.send(ev, msg)


@sv.on_prefix(('上传'))
async def upload_header(bot, ev):
    """上传配方"""
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '上传配方仅限管理员使用', at_sender=True)
        return
    response = alchemy_manual.upload_recipe(bot, ev)
    if response[0] == 0:
        await bot.finish(ev, response[1], at_sender=True)
    else:
        await bot.send(ev, response[1], at_sender=True)
        

@sv.on_message('group')
async def replymessage(bot, ev: CQEvent):
    """通过回复 bot 消息上传"""
    print(f'收到来自{ev.user_id}的消息：{ev.message}, 类型：{ev.message_type}')
    seg=ev.message[0]
    if seg.type != 'reply':
        return
    tmid = seg.data['id']
    cmd = ev.message.extract_plain_text()
    flag1 = 0
    flag2 = 0
    for m in ev.message[2:]:
        if m.type == 'at' and m.data['qq'] == ev.self_id:
            flag1 = 1
    for name in NICKNAME:
        if name in cmd:
            flag1 = 1
            break
    for pfcmd in ['上传', '窃取', '偷了']:
        if pfcmd in cmd:
            flag2 = 1
    if not (flag1 and flag2):
        return
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev,f"仅限管理员上传！", at_sender=True)
        return
    try:
        tmsg = await bot.get_msg(self_id=ev.self_id, message_id=int(tmid))
    except ActionFailed:
        await bot.finish(ev, '该消息已过期，请重新转发~')
        return


    response = alchemy_manual.upload_recipe_by_reply(bot, ev, tmsg)
    if response[0] == 0:
        await bot.finish(ev, response[1], at_sender=True)
    else:
        await bot.send(ev, response[1], at_sender=True)



@sv.on_rex((r'^炼金手册([1-9]\d*)$'))
async def alchemy_book(bot, ev):
    match = ev['match']
    page=int(match.group(1))-1
    response = alchemy_manual.get_alchemy_manual(bot, ev, page)
    if response[0] == 1:
        await bot.send(ev, response[1])


@sv.on_rex((r'^查看配方([1-9]\d*)'))
async def view_recipe(bot, ev):
    uid = str(ev['user_id'])
    if not interval.check(uid):
        await bot.finish(ev, f'魔力回复中！(剩余 {int(interval.left_time(uid)) + 1}秒)', at_sender=True)
        return
    interval.start_cd(uid,30)
    match = ev['match']
    rowid=int(match.group(1))

    response = alchemy_manual.get_recipe(bot, ev, rowid)
    if response[0] == 1:
        await bot.send(ev, response[1])


@sv.on_rex((r'^使用配方([1-9]\d*)'))
async def generate_recipe(bot, ev):
    uid = str(ev['user_id'])
    if not daily_limit.check(uid):
        await bot.finish(ev, f'今日魔力已经用完，请明天再来~', at_sender=True)
        return
    if not interval.check(uid):
        await bot.finish(ev, f'魔力回复中！(剩余 {int(interval.left_time(uid)) + 1}秒)', at_sender=True)
        return
    daily_limit.increase(uid) 
    interval.start_cd(uid)
    match = ev['match']
    rowid=int(match.group(1))
    await bot.send(ev, f"\n正在炼金中, 请稍后...\n(今日剩余{daily_limit_ - int(daily_limit.get_num(uid))}次)", at_sender=True)

    response = alchemy_manual.use_recipe(bot, ev, rowid)

    if response[0] == 1:
        msg = response[1]
        data = await gen_pic(msg)
        await bot.send_group_forward_msg(group_id=ev["group_id"], messages=data)



@sv.on_rex((r'^删除配方([1-9]\d*)'))
async def delete_recipe(bot, ev):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.finish(ev, '删除配方仅限超级管理员使用', at_sender=True)
        return
    match = ev['match']
    rowid=int(match.group(1))

    response = alchemy_manual.delete_recipe_by_rowid(bot, ev, rowid)
    if response[0] == 1:
        await bot.send(ev, response[1])


async def gen_pic(text):
    try:
        # 去除掉换行符以及空格
        text = text.replace('\n', '').replace(' ', '')
        print(f'text:{text}, type: {type(text)}')
        get_url = f'{word2img_url}?token={token}&tags={text}'
        print(f'正在向{get_url}请求图片')
        res = await aiorequests.get(get_url)
        image = await res.content
        load_data = json.loads(re.findall('{"steps".+?}', str(image))[0])
        image_b64 = 'base64://' + str(base64.b64encode(image).decode())
        # mes = f"[CQ:image,file={image_b64}]"
        # mes += f'\nseed:{load_data["seed"]}'
        data = {"type": "node", "data": {"name": "ai绘图", "uin": "2854196310", "content": f"[CQ:image,file={image_b64}]"}}
        return data
    except Exception as e:
        print(f"炼金失败, 错误信息: {e}")
        return f"炼金失败了,原因:{e}"


ai_draw_group_list = config['ai_draw_group_list']
all_group_list = config['all_group_list']
black_list = []


@sv.on_prefix(('aidraw'))
async def gen_pic_safe(bot, ev: CQEvent):
    try:
        print(f'群号为:{ev.group_id}')
        if ev.group_id not in ai_draw_group_list:
                pass
        else:
            await bot.send(ev, f"正在生成", at_sender=True)
            text = ev.message.extract_plain_text()
            taglist = [chr.lower() for chr in text.split(',')]
            # 遍历 taglist, 如果在 black_list 中则删除
            for i in taglist:
                if i in black_list:
                    taglist.remove(i)
            print(taglist)
            uid = ev.user_id
            for tag in taglist:
                xp.add_xp_num(uid, tag)
            tags = ','.join(str(i) for i in taglist)
            get_url = word2img_url + "?r18=0&tags=" + tags + f'&token={token}'
            print(f'正在请求{get_url}')
            # image = await aiorequests.get(get_url)
            res = await aiorequests.get(get_url)
            image = await res.content
            load_data = json.loads(re.findall('{"steps".+?}', str(image))[0])
            image_b64 = f"base64://{str(base64.b64encode(image).decode())}"
            mes = f"[CQ:image,file={image_b64}]\n"
            mes += f'seed:{load_data["seed"]}   '
            mes += f'scale:{load_data["scale"]}\n'
            mes += f'tags:{text}'
            data = {
                "type": "node", 
                "data": {
                    "name": "QQ小冰", 
                    "uin": "2854196310", 
                    "content": mes
                }
            }
            await bot.send_group_forward_msg(group_id=ev["group_id"], messages=data)

    except:
        await bot.send(ev, "生成失败…")


@sv.on_prefix(('aigener'))
async def gen_pic_all(bot, ev: CQEvent):
    try:
        print(f'群号为:{ev.group_id}')
        if ev.group_id not in all_group_list:
            pass
        else:
            await bot.send(ev, f"正在生成", at_sender=True)
            text = ev.message.extract_plain_text()
            get_url = word2img_url + "?r18=1&tags=" + text + f'&token={token}'
            print(f'正在请求{get_url}')
            # image = await aiorequests.get(get_url)
            res = await aiorequests.get(get_url)
            image = await res.content
            load_data = json.loads(re.findall('{"steps".+?}', str(image))[0])
            image_b64 = 'base64://' + str(base64.b64encode(image).decode())
            mes = f"[CQ:image,file={image_b64}]\n"
            mes += f'seed:{load_data["seed"]}   '
            mes += f'scale:{load_data["scale"]}\n'
            mes += f'tags:{text}'
            await bot.send(ev, mes, at_sender=True)
    except:
        await bot.send(ev, "生成失败…")



@sv.on_prefix("img2img")
async def img2img(bot, ev):
    if ev.group_id not in ai_draw_group_list:
        pass
    else:
        tag = ev.message.extract_plain_text()
        if tag == "":
            url = ev.message[0]["data"]["url"]
        else:
            url = ev.message[1]["data"]["url"]
        await bot.send(ev, "正在生成", at_sender=True)
        image = Image.open(BytesIO(requests.get(url, timeout=20).content))
        # img_x, img_y = int(image.size[0] * (768 / image.size[1])), 768
        # image = image.resize((img_x, img_y))
        thumbSize = (768, 768)
        image = image.convert("RGB")
        if (image.size[0] > image.size[1]):
            image_shape = "Landscape"
        elif (image.size[0] == image.size[1]):
            image_shape = "Square"
        else:
            image_shape = "Portrait"

        image.thumbnail(thumbSize, resample=Image.ANTIALIAS)
        b_io = BytesIO()
        image.save(b_io, format="JPEG")
        posturl =  img2img_url + (f"?tags={tag}&token={token}" if tag != "" else f"?token={token}") 
        resp = await aiorequests.post(
            posturl,
            data=base64.b64encode(b_io.getvalue()),
        )
        print(f'正在向{posturl}发起请求')
        img = await resp.content
        # print(f'返回结果:{img}')
        image_b64 = f"base64://{str(base64.b64encode(img).decode())}"
        data = {"type": "node", "data": {"name": "ai绘图", "uin": "2854196310", "content": f"[CQ:image,file={image_b64}]"}}
        await bot.send_group_forward_msg(group_id=ev["group_id"], messages=data)
