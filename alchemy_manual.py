# 炼金手册
from os.path import dirname, join, exists
from os import makedirs, remove
import sqlite3
from hoshino.typing import CQEvent
import requests
from PIL import Image, ImageDraw,ImageFont
import re
from io import BytesIO
import base64
import calendar, time
from hoshino.config import NICKNAME
from aiocqhttp.exceptions import ActionFailed


curpath = dirname(__file__)
image_list_db = join(curpath, 'save_tags.db')   #保存tags数据库
save_image_path= join(curpath,'SaveImage')  # 保存图片路径

class AlchemyManual:
    def __init__(self):
        makedirs(dirname(image_list_db), exist_ok=True)
        makedirs(save_image_path, exist_ok=True)
        self._create_table()
    
    def _connect(self):
        return sqlite3.connect(image_list_db)

    def _create_table(self):
        try:
            self._connect().execute(
                """CREATE TABLE IF NOT EXISTS aitag(
                    scale TINYINT,
                    size CHAR,
                    tags TEXT,
                    seed INT,
                    saveconfig BLOB
                )
                """
            )
        except:
            raise Exception('创建炼金手册tags数据库发生错误')
    
    def _upload_recipe(self, scale, size, tags, seed, saveconfig):
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO aitag (scale, size, tags, seed, saveconfig) VALUES (?,?,?,?,?)", (scale, size, tags, seed, saveconfig)
                )
        except:
            raise Exception('上传配方时发生错误')

    def _get_alchemy_manual(self):
        """获取炼金手册, 返回由 (rowid, saveconfig) 组成的列表"""
        try:
            with self._connect() as conn:
                return conn.execute("SELECT rowid, saveconfig FROM aitag").fetchall()
        except:
            raise Exception('获取配方时发生错误')

    def _get_recipe(self, rowid):
        """获取配方, 返回所有信息, rowid: 配方id"""
        try:
            with self._connect() as conn:
                return conn.execute("SELECT * FROM aitag WHERE rowid=?", (rowid,)).fetchone()
        except:
            raise Exception('获取配方时发生错误')
    
    def _delete_recipe(self, rowid):
        """删除配方, rowid: 配方id"""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM aitag WHERE rowid=?", (rowid,))
        except:
            raise Exception('删除配方时发生错误')
    

def upload_recipe(bot, ev: CQEvent) -> tuple:
    """上传配方
    
    Args:
        bot (Bot): bot
        ev (CQEvent): event

    Returns: tuple(code, str)
        code - 0: 失败 1: 成功
        str:上传状态, 包括:
            上传成功
            图片格式出错
            种子格式出错
            权重格式出错
            标签格式出错
            其他报错
    """
    alchemy_manual = AlchemyManual()
    try:
        for i in ev.message:
            if i.type == "image":
                image=str(i)
                break
        image_url = re.match(r"\[CQ:image,file=(.*),url=(.*)\]", str(image))
        pic_url = image_url.group(2)
        response = requests.get(pic_url)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        ls_f=base64.b64encode(BytesIO(response.content).read())
        imgdata=base64.b64decode(ls_f)
        datetime = calendar.timegm(time.gmtime())
        image_path= './SaveImage/'+str(datetime)+'.png'
        saveconfig = join(curpath, f'{image_path}')
        size=f"{img.width}x{img.height}"
        pic = open(saveconfig, "wb")
        pic.write(imgdata)
        pic.close()
    except:
        return (0, '图片格式出错')
    try:
        seed_list1=str(ev.message).split(f"scale:")
        seed_list2=seed_list1[0].split('eed:')
        seed=seed_list2[1].strip ()
    except:
        return (0, '种子格式出错')
    try:
        scale_list=seed_list1[1].split(f"tags:")
        scale=scale_list[0].strip()
    except:
        return (0, '权重格式出错')
    try:
        tags=scale_list[1].strip()
    except:
        return (0, '标签格式出错')
    try:
        alchemy_manual._upload_recipe(scale, size, tags, seed, saveconfig)
        return (1, '上传成功')
    except Exception as e:
        return (0, f'其他报错: {e}')


def upload_recipe_by_reply(bot, ev: CQEvent, tmsg) -> tuple:
    """通过回复 bot 消息上传配方
    TODO: 没能成功复现, 有待后续测试
    """
    try:
        print(f'获取到的消息为: {tmsg}')
        # 获取转发消息中的第一条消息
        get_url = f"http://127.0.0.1:5701/get_forward_msg?message_id={tmsg['message_id']}"
        print(f'正在向 {get_url} 发送请求')
        # response = requests.get(get_url)
        # print(f'请求结果: {response.json()}')
        tmsg = tmsg.get_forward_msg()
        print(f'j解析转发消息中的消息为 {tmsg}')
        image_url = re.search(r"\[CQ:image,file=(.*),url=(.*)\]", str(tmsg["message"]))
        if not image_url:
            return (0, '未找到图片')
        file = image_url.group(1)
        pic_url = image_url.group(2)
        if ',subType=' in pic_url:
            sbtype=pic_url.split('=')[-1]
            pic_url = pic_url.split(',')[0]
        elif ',subType=' in file:
            sbtype=file.split('=')[-1]
            file = file.split(',')[0]
        else:
            sbtype=None
        if 'c2cpicdw.qpic.cn/offpic_new/' in pic_url:
            md5 = file[:-6].upper()
            pic_url = f"http://gchat.qpic.cn/gchatpic_new/0/0-0-{md5}/0?term=2"
        response = requests.get(pic_url)
        img = Image.open(BytesIO(response.content)).convert("RGB")
        ls_f=base64.b64encode(BytesIO(response.content).read())
        imgdata=base64.b64decode(ls_f)
        datetime = calendar.timegm(time.gmtime())
        image_path= './SaveImage/'+str(datetime)+'.png'
        saveconfig = join(curpath, f'{image_path}')
        size=f"{img.width}x{img.height}"
        pic = open(saveconfig, "wb")
        pic.write(imgdata)
        pic.close()
    except:
        return (0, '图片格式出错')
    try:
        seed_list1=str(tmsg["message"]).split(f"scale:")
        seed_list2=seed_list1[0].split('eed:')
        seed=seed_list2[1].strip ()
    except:
        return (0, '种子格式出错')
    try:
        scale_list=seed_list1[1].split(f"tags:")
        scale=scale_list[0].strip()
    except:
        return (0, '权重格式出错')
    try:
        tags=scale_list[1].strip()
    except:
        return (0, '标签格式出错')
    try:
        conn=sqlite3.connect(image_list_db)
        cur = conn.cursor()
        cur.execute("INSERT INTO aitag VALUES (?,?,?,?,?)",(scale,size,tags,seed,saveconfig))
        conn.commit()
        cur.close()
        conn.close()
        return (1, '上传成功!')
    except Exception as e:
        return (0, f'其他报错: {e}')

ttf_font_path = join(dirname(__file__), 'SIMSUNB.TTF')


def get_alchemy_manual(bot, ev: CQEvent, page: int = 1):
    """获取配方 page:页码, 默认为1"""
    alchemy_manual = AlchemyManual()
    image_list = alchemy_manual._get_alchemy_manual()
    target = Image.new('RGB', (1920,1080),(255,255,255))
    i=0
    for index in range(0+(page*8),8+(page*8)):
        try:
            image_msg=image_list[index]
        except:
            break
        rowid = image_msg[0]
        image_path=image_msg[1]
        region = Image.open(image_path)
        region = region.convert("RGB")
        region = region.resize((int(region.width/2),int(region.height/2)))
        font = ImageFont.truetype(ttf_font_path, 36)  # 设置字体和大小
        draw = ImageDraw.Draw(target)
        if i<4:
            target.paste(region,(80*(i+1)+384*i,50))
            draw.text((80*(i+1)+384*i+int(region.width/2)-18,80+region.height),str(rowid).replace(',',''),font=font,fill = (0, 0, 0))
        if i>=4:
            target.paste(region,(80*(i-3)+384*(i-4),150+384))
            draw.text((80*(i-3)+384*(i-4)+int(region.width/2)-18,180+384+region.height),str(rowid).replace(',',''),font=font,fill = (0, 0, 0))
        i+=1
    result_buffer = BytesIO()
    target.save(result_buffer, format='JPEG', quality=100) #质量影响图片大小
    imgmes = 'base64://' + base64.b64encode(result_buffer.getvalue()).decode()
    resultmes = f"[CQ:image,file={imgmes}]"
    return (1, resultmes)


def get_recipe(bot, ev: CQEvent, rowid: int):
    """获取配方 rowid:配方id"""
    alchemy_manual = AlchemyManual()
    recipe = alchemy_manual._get_recipe(rowid)
    scale, size, tags, seed, image_path = recipe

    pic = open(image_path, "rb")
    base64_str = base64.b64encode(pic.read())
    imgmes = 'base64://' + base64_str.decode()
    resultmes = f"[CQ:image,file={imgmes}]"
    pic.close()
    msg=f"序号为:{rowid}\n{resultmes}\n配方:ai绘图{tags}\nCFG scale: {scale}, Size:{size}"
    return (1, msg)


def use_recipe(bot, ev: CQEvent, rowid: int):
    """使用配方 rowid:配方id"""
    alchemy_manual = AlchemyManual()
    recipe = alchemy_manual._get_recipe(rowid)
    scale, size, tags, seed, image_path = recipe

    msg=f"{tags}\nCFG scale: {scale}, Size:{size}".replace('&r18=1','')
    return (1, msg)


def delete_recipe_by_rowid(bot, ev: CQEvent, rowid: int):
    """删除配方 rowid:配方id"""
    alchemy_manual = AlchemyManual()
    recipe = alchemy_manual._get_recipe(rowid)
    scale, size, tags, seed, image_path = recipe
    remove(image_path)
    alchemy_manual._delete_recipe(rowid)
    return (1, f'已删除配方{rowid}')

