# XP 查询 by 季落
import os
import sqlite3

# XP 数据库路径
XP_DB_PATH = os.path.expanduser('~/.hoshino/AI_image_xp.db')
class XpCounter:
    def __init__(self):
        os.makedirs(os.path.dirname(XP_DB_PATH), exist_ok=True)
        self._create_table()
    def _connect(self):
        return sqlite3.connect(XP_DB_PATH)
        
    def _create_table(self):
        try:
            self._connect().execute(
                    '''CREATE TABLE IF NOT EXISTS XP_NUM
                        (UID             INT    NOT NULL,
                        KEYWORD         TEXT   NOT NULL,
                        NUM             INT    NOT NULL,
                        PRIMARY KEY(UID,KEYWORD));
                    '''
            )
        except:
            raise Exception('创建表发生错误')
            
    def _add_xp_num(self, uid, keyword):
        try:
        
            num = self._get_xp_num(uid, keyword)
            if num == None:
                num = 0
            num += 1
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO XP_NUM (UID,KEYWORD,NUM) \
                                VALUES (?,?,?)", (uid, keyword, num)
                )
        except:
            raise Exception('更新表发生错误')
            
    def _get_xp_num(self, uid, keyword):
        try:
            r = self._connect().execute("SELECT NUM FROM XP_NUM WHERE UID=? AND KEYWORD=?", (uid, keyword)).fetchone()
            return 0 if r is None else r[0]
        except:
            raise Exception('查找表发生错误')
    
    def _get_xp_list(self, uid, num):
        """获取个人 xp 列表"""
        with self._connect() as conn:
            r = conn.execute(
                f"SELECT KEYWORD,NUM FROM XP_NUM WHERE UID={uid} ORDER BY NUM desc LIMIT {num}").fetchall()
        return r if r else {}

    def _get_xp_list_all(self, num):
        """获取全体 xp 列表前 num 项"""
        with self._connect() as conn:
            r = conn.execute(
                f"SELECT KEYWORD,NUM FROM XP_NUM ORDER BY NUM desc LIMIT {num}").fetchall()
        return r if r else {}

def add_xp_num(uid, keyword):
    """xp 计数"""
    XP = XpCounter()
    XP._add_xp_num(uid, keyword)

def get_xp_list(uid):
    """获取个人 xp 列表(前15项"""
    XP = XpCounter()
    xp_list = XP._get_xp_list(uid, 15)
    if len(xp_list)>0:
        data = sorted(xp_list,key=lambda cus:cus[1],reverse=True)
        new_data = []
        for xp_data in data:
            keyword, num = xp_data
            new_data.append((keyword,num))
        rankData = sorted(new_data,key=lambda cus:cus[1],reverse=True)
        print(f'返回查询结果为: {rankData}')
        return rankData
    else:
        return []


def get_xp_list_all():
    """获取群友的 xp 列表(前15项)"""
    xp = XpCounter()
    print('已进入查询函数, 准备调用数据库查询函数查询')
    xp_list = xp._get_xp_list_all(15)
    print(f'''查询结果为: {xp_list}''')
    if len(xp_list)>0:
        data = sorted(xp_list,key=lambda cus:cus[1],reverse=True)
        new_data = []
        for xp_data in data:
            keyword, num = xp_data
            new_data.append((keyword,num))
        rankData = sorted(new_data,key=lambda cus:cus[1],reverse=True)
        return rankData
    else:
        return []


def add_xp_num(uid, keyword):
    XP = XpCounter()
    XP._add_xp_num(uid, keyword)

