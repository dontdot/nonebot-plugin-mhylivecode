from nonebot import get_driver, on_command, require
from nonebot.internal.matcher import Matcher
from loguru import logger
from nonebot_plugin_saa import TargetQQPrivate, enable_auto_select_bot, TargetQQGroup, MessageFactory, Image, Text

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

import time

from .live_code import LiveCode

driver = get_driver()

@driver.on_startup
def _():
    LiveCode.read_file()
    enable_auto_select_bot()

code = on_command("lcode", aliases={"直播兑换码"})

@code.handle()
async def code(event = None, matcher: Matcher = None):
    
    lc = LiveCode()
    logger.info('开始执行mys直播兑换码获取')
    status_gs, status_sr = False, False
    if await lc.gs_actid():
        status_gs = True
        logger.info('原神直播兑换码执行完毕')
    if await lc.sr_actid():
        status_sr = True
        logger.info('崩铁直播兑换码执行完毕')
    if not status_gs and not status_sr:
        logger.info('所有直播兑换码获取失败')
    # user_id = event.get_user_id()
    code_data = LiveCode.read_file()
    send_func = code_data['send']
    nowtime = time.time ()
    name = {'genshin': '原神', 'starrail': '崩铁'}
    for game, game_data in code_data.items():
        if game in {'genshin', 'starrail'}:
            game_data['is_notice'] = False
            if game_data['expired_time']:
                if nowtime < LiveCode.time_trans(game_data['expired_time']):
                    game_data['is_notice'] = True   
            await LiveCode.save_liveData(game, game_data)
            codes = game_data['code']
            title = '原神' if game=='genshin' else '崩铁'
            if codes and game_data['is_notice']:
                expired_time = game_data['expired_time']
                msgs = [f'{title}{game_data["version"]}版本 \
                        \n{game_data["version_title"]}前瞻直播： \
                        \n兑换码到期：{expired_time}']
                for code in codes:
                    msgs.append(code)
                # msgs.append({code[1]})
                # msgs.append({code[2]})
            elif not codes and game_data['is_notice']:
                if game_data["version_img"]:
                    version_img = Image(game_data["version_img"])
                    msgs = [[f'{title}{game_data["version"]}版本\n{game_data["version_title"]}\n \
                            将于{game_data["live_starttime"]}开启前瞻直播', version_img]]
                else:
                    msgs = [f'{title}{game_data["version"]}版本\n{game_data["version_title"]}：\n \
                            将于{game_data["live_starttime"]}开启前瞻直播']
            else:
                msgs = [f'<{name[game]}>没有可用兑换码']
            for msg in msgs:
                if isinstance(msg, list):
                    msg = MessageFactory([msg[0], msg[1]])
                else:
                    msg = MessageFactory(msg)
                if matcher:
                    await msg.send()
                else:
                    if game_data['is_notice']:
                        if len(send_func['qq']) > 0:
                            for one_qq in send_func['qq']:
                                target = TargetQQPrivate(user_id=int(one_qq))
                                await msg.send_to(target=target)
                        if len(send_func['group']) > 0:
                            for one_group in send_func['group']:
                                target = TargetQQGroup(group_id=int(one_group))
                                await msg.send_to(target=target)

@scheduler.scheduled_job("cron",
                         hour='20',
                         minute='45',
                         id="check_myslive")
async def auto_check_myslivecode():
    logger.info(f"开始执行米游社直播检查自动任务")
    await code()
    logger.info(f"米游社直播检查自动任务执行完成")
    