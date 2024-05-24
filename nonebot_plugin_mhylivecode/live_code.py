import os
import json
import re
import pathlib
import httpx
import datetime
from loguru import logger

class LiveCode():

    live = {
        'send': {
            'qq': [],
            'group':[]
        },
        'genshin':{
            'version': '',
            'version_title': '',
            'version_img': '',
            'act_id': '',
            'live_starttime': '',
            'code': [],
            'expired_time': '',
            'is_notice': ''
        },
        'starrail':{
            'version': '',
            'version_title': '',
            'version_img': '',
            'act_id': '',
            'live_starttime': '',
            'code': [],
            'expired_time': '',
            'is_notice': ''
        }
    }

    comm = {'genshin':'2', 'starrail':'6'}
    
    def __init__(self) -> None:
        self.genshin = {}
        self.starrail = {}
        self.load_config()


    @staticmethod
    def read_file():
        if not os.path.exists('data/myslivecode/mys_livecode.json'):
            pathlib.Path('data/myslivecode').mkdir(parents=True, exist_ok=True)
            with open('data/myslivecode/mys_livecode.json', 'w', encoding='utf-8') as f:
                json.dump(LiveCode.live, f, indent=4)
        with open('data/myslivecode/mys_livecode.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def load_config(self):
        config = self.read_file()
        self.genshin = config['genshin']
        self.starrail = config['starrail']

    @staticmethod
    async def save_liveData(namekey, data):
        with open('data/myslivecode/mys_livecode.json', 'r', encoding='utf-8') as file:
            live_data = json.load(file)
        live_data[namekey] = data
        with open('data/myslivecode/mys_livecode.json', 'w', encoding='utf-8') as new:
            json.dump(live_data, new, indent=4, ensure_ascii=False)

    @staticmethod
    def time_trans(intime):
        if isinstance(intime, int):
            dt = datetime.datetime.fromtimestamp(intime)
            revise_time = dt.replace(hour=12, minute=0, microsecond=0) + datetime.timedelta(days=1)
            outtime = revise_time.strftime('%Y-%m-%d %H:%M')
        elif isinstance(intime, str):
            dt = datetime.datetime.strptime(intime, '%Y-%m-%d %H:%M')
            outtime = int(dt.timestamp())
        return outtime

    @staticmethod
    async def get_file(url: str):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=10, follow_redirects=True)
            return res.content
        except Exception:
            logger.exception(f'下载文件 - {url} 失败')

    async def get_livecode(self, gamecomm, data_config):
        try:
            url = "https://api-takumi.mihoyo.com/event/miyolive/index"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "referer": "https://webstatic.mihoyo.com/",
                "x-rpc-act_id": data_config['act_id'],
                "x-requested-with": "com.mihoyo.hyperion"
            }
            # "x-requested-with": "com.mihoyo.hyperion"     gs
            # "x-requested-with": "com.hiker.youtoo"        sr

            # if gamecomm == '2':
            #     headers["x-requested-with"] = "com.mihoyo.hyperion"
            # elif gamecomm == '6':
            #     headers["x-requested-with"] = "com.mihoyo.hyperion"
            #     headers["x-rpc-act_id"] = "ea202404231611044487"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
            codeVer_data = json.loads(response.text)
            if codeVer_data['retcode'] == 0:
                code_ver = codeVer_data["data"]["live"]["code_ver"]
                code_url = f"https://api-takumi-static.mihoyo.com/event/miyolive/refreshCode?version={code_ver}"
                async with httpx.AsyncClient() as client:
                    res = await client.get(code_url, headers=headers, timeout=10)
                code_data = json.loads(res.text)
                data_config['live_starttime'] = str(codeVer_data['data']['live']['start'][:-3])
                expired_time = self.time_trans(int(code_data['data']['code_list'][2]['to_get_time']))
                data_config['expired_time'] = expired_time
                data_config['is_notice'] = True
                code = []
                for item in code_data["data"]["code_list"]:
                    if item['code']:
                        code.append(item["code"])
                data_config['code'] = code
                for k, v in self.comm.items():
                    if gamecomm == str(v):
                        await self.save_liveData(k, data_config)
                        logger.info('成功保存前瞻直播数据')
            else:
                logger.info('没有code')
                data_config['is_notice'] = False
                for k, v in self.comm.items():
                    if gamecomm == str(v):
                        await self.save_liveData(k, data_config)
        except IndexError as e:
            logger.debug('没有兑换码列表')
        except Exception as e:
            logger.debug(type(e).__name__,e)
            pass
    
    async def get_ver_imgandtitle(self,version):
        try:
            url = 'https://bbs-api.miyoushe.com/post/wapi/userPost?size=20&uid=75276539'
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "referer": "https://www.miyoushe.com/"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
            data = json.loads(response.text)['data']['list']
            num = 0
            for d in data:
                if num < 1 and '前瞻特别节目预告' in d['post']['subject']:
                    version_p = re.findall(r"\d+.\d+", d['post']['subject'])[0]
                    if version_p == version:
                        num += 1
                        version_title = re.findall(r"「.*」", d['post']['subject'])[0]
                        version_img = d['post']['cover']
                        return {'version_title': version_title, 'version_img': version_img}
        except Exception:
            raise

    async def act_id(self,url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "referer": "https://www.miyoushe.com/"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10)
            data = json.loads(response.text)['data']['list']
            num = 0
            for d in data:
                if num < 1 and '前瞻' in d['post']['subject']:
                    matches = re.findall(r"\d+.\d+", d['post']['subject'])
                    if matches:
                        matches = matches[0]
                        num += 1
                        gamecomm = str(d['post']['game_id'])
                        data_config = self.genshin if gamecomm == self.comm['genshin'] else self.starrail
                        if matches > data_config['version'] or not data_config['code']:
                            data_config["version"] = matches
                            get_sth_data = await self.get_ver_imgandtitle(matches)
                            data_config['version_title'] = get_sth_data['version_title']
                            data_config['version_img'] = get_sth_data['version_img']
                            content = json.loads(d['post']['structured_content'])
                            for d in content:
                                if 'attributes' not in d:
                                    continue
                                if 'link' in d['attributes']:
                                    link = d['attributes'].get("link", "")
                                    act_id_start = link.find("act_id=") + len("act_id=")
                                    act_id_end = link.find("&", act_id_start)
                                    act_id = link[act_id_start:act_id_end]
                                    data_config['act_id'] = act_id
                                    await self.get_livecode(gamecomm, data_config)
                                    return True
                                else:
                                    continue
        except Exception:
            return False
  
    async def gs_actid(self):
        url = 'https://bbs-api.miyoushe.com/post/wapi/userPost?size=20&uid=75276550'
        if await self.act_id(url):
            return True

    async def sr_actid(self):
        url = 'https://bbs-api.miyoushe.com/post/wapi/userPost?size=20&uid=80823548'
        if await self.act_id(url):
            return True



