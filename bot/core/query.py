import asyncio
import random
import json
from itertools import cycle
from time import time

import aiohttp
# import requests
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.core.agents import generate_random_user_agent
from bot.config import settings
# import cloudscraper

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from random import randint

import urllib3
from bot.utils.get_data import get_data
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Tạo một semaphore global để giới hạn số lượng Tapper chạy cùng lúc
tapper_semaphore = asyncio.Semaphore(settings.MULTI_TAPPERS)  # Giới hạn Tapper cùng lúc, bạn có thể điều chỉnh số này

def calc_id(x: int, y: int, x1: int, y1: int):
    px_id = randint(min(y, y1), max(y1, y))*1000
    px_id += randint(min(x, x1), max(x1, x))+1
    # print(px_id)
    return px_id

class Tapper:
    def __init__(self, query: str, session_name, multi_thread):
        self.query = query  # Lưu trữ query gốc
        self.session_name = session_name
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''
        self.auth_token = ""
        self.last_claim = None
        self.last_checkin = None
        self.balace = 0
        self.maxtime = 0
        self.fromstart = 0
        self.balance = 0
        self.checked = [False] * 5
        self.multi_thread = multi_thread
        self.session = None

    async def create_session(self):
        self.session = aiohttp.ClientSession(headers=headers)

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            async with http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(15)) as response:
                ip = (await response.json()).get('origin')
                logger.info(f"{self.session_name} | Proxy IP: {ip}")
                return True
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            return False

    async def login(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/users/me", headers=headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Logged in.</green>")
                return True
            else:
                print(await response.text())
                logger.warning(f"{self.session_name} | <red>Failed to login</red>")
                return False

    async def get_user_data(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/status", headers=headers) as response:
            response_json = await response.json()
            if response.status == 200:
                return response_json
            else:
                logger.warning(f"{self.session_name} | <red>Failed to get user data: {response_json}</red>")
                return None

    def generate_random_color(self):
        r = randint(0, 255)
        g = randint(0, 255)
        b = randint(0, 255)
        return "#{:02X}{:02X}{:02X}".format(r, g, b)

    def generate_random_pos(self):
        return randint(1, 1000000)

    def get_cor(self):
        with open('bot/utils/3xdata.json', 'r') as file:
            cor = json.load(file)

        paint = random.choice(cor['data'])
        color = paint['color']
        random_cor = random.choice(paint['cordinates'])
        # print(f"{color}: {random_cor}")
        px_id = calc_id(random_cor['start'][0], random_cor['start'][1], random_cor['end'][0], random_cor['end'][1])
        return [color, px_id]

    async def repaint(self, session: aiohttp.ClientSession, chance_left):
        #  print("starting to paint")
        if settings.X3POINTS:
            data = self.get_cor()
            payload = {
                "newColor": data[0],
                "pixelId": data[1]
            }
        else:
            data = [str(self.generate_random_color()), int(self.generate_random_pos())]
            payload = {
                "newColor": data[0],
                "pixelId": data[1]
            }
        async with session.post("https://notpx.app/api/v1/repaint/start", headers=headers, json=payload) as response:
            response_json = await response.json()
            if response.status == 200:
                if settings.X3POINTS:
                    logger.success(
                        f"{self.session_name} | <green>Painted <cyan>{data[1]}</cyan> successfully new color: <cyan>{data[0]}</cyan> | Earned <light-blue>{int(response_json['balance']) - self.balance}</light-blue> | Balace: <light-blue>{response_json['balance']}</light-blue> | Repaint left: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
                else:
                    logger.success(
                        f"{self.session_name} | <green>Painted <cyan>{data[1]}</cyan> successfully new color: <cyan>{data[0]}</cyan> | Earned <light-blue>{int(response_json['balance']) - self.balance}</light-blue> | Balace: <light-blue>{response_json['balance']}</light-blue> | Repaint left: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
            else:
                print(await response.text())
                logger.warning(f"{self.session_name} | Faled to repaint: {response.status}")

    async def repaintV2(self, session: aiohttp.ClientSession, chance_left, i, data):
        if i % 2 == 0:
            payload = {
                "newColor": data[0],
                "pixelId": data[1]
            }
        else:
            data1 = [str(self.generate_random_color()), int(self.generate_random_pos())]
            payload = {
                "newColor": data1[0],
                "pixelId": data[1]
            }
        async with session.post("https://notpx.app/api/v1/repaint/start", headers=headers, json=payload) as response:
            response_json = await response.json()
            if response.status == 200:
                if i % 2 == 0:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data[0]}</cyan> | Đã kiếm được <light-blue>{int(response_json['balance']) - int(self.balance)}</light-blue> | Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
                else:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data1[0]}</cyan> | Đã kiếm được <light-blue>{int(response_json['balance']) - int(self.balance)}</light-blue> | Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
            elif response.status != 200:
                if response_json.get('error') == "insufficient charges amount":
                    logger.warning(f"{self.session_name} | <yellow>Hết lượt vẽ</yellow>")
                else:
                    logger.warning(f"{self.session_name} | <yellow>{response_json.get('error')}</yellow>")


    # def auto_task(self, session: cloudscraper.CloudScraper):
    #     pass


    async def auto_upgrade_paint(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/paintReward", headers=headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade paint reward successfully!</green>")
        await asyncio.sleep(random.uniform(2,4))

    async def auto_upgrade_recharge_speed(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/reChargeSpeed", headers=headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade recharging speed successfully!</green>")
        await asyncio.sleep(random.uniform(2,4))

    async def auto_upgrade_energy_limit(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/energyLimit", headers=headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade energy limit successfully!</green>")


    async def claimpx(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/claim", headers=headers) as response:
            if response.status == 200:
                response_json = await response.json()
                logger.success(f"{self.session_name} | <green>Successfully claimed <cyan>{response_json['claimed']} px</cyan> from mining!</green>")
            else:
                logger.warning(f"{self.session_name} | <yellow>Failed to claim px from mining: {await response.text()}</yellow>")

    async def get_data_async(self, query: str):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, get_data, query)
        return result

    async def run(self, proxy: str | None) -> None:
        await self.create_session()
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)
        if proxy:
            proxy_check = await self.check_proxy(http_client=http_client, proxy=proxy)
            if proxy_check:
                proxy_type = proxy.split(':')[0]
                self.session.proxies = {
                    proxy_type: proxy
                }
                logger.info(f"{self.session_name} | bind with proxy ip: {proxy}")     

        token_live_time = randint(1000, 1500)
        try:
            if time() - access_token_created_time >= token_live_time:
                processed_query = await self.get_data_async(self.query)
                headers['Authorization'] = f"initData {processed_query}"
                access_token_created_time = time()
                token_live_time = randint(1000, 1500)
                

            if await self.login(self.session):
                user = await self.get_user_data(self.session)
                if user:
                    self.maxtime = user['maxMiningTime']
                    self.fromstart = user['fromStart']
                    self.balance = int(user['userBalance'])
                    
                    logger.info(
                        f"{self.session_name} | Pixel Balance: <light-blue>{int(user['userBalance'])}</light-blue> | Pixel available to paint: <cyan>{user['charges']}</cyan>")
                    
                    if int(user['charges']) > 0:
                        # print("starting to paint 1")
                        total_chance = int(user['charges'])
                        i = 0
                        data = self.get_cor()
                        while total_chance > 0:
                            total_chance -= 1
                            i += 1
                            if settings.X3POINTS:
                                await self.repaintV2(self.session, total_chance, i, data)
                            else:
                                await self.repaint(self.session, total_chance)
                            sleep_ = random.uniform(1, 3)
                            logger.info(f"{self.session_name} | Nghỉ <cyan>{sleep_}</cyan> trước khi tiếp tục...")
                            await asyncio.sleep(sleep_)
                                                    
                    r = random.uniform(2, 4)
                    if float(self.fromstart) >= self.maxtime / r:
                        await self.claimpx(self.session)
                        await asyncio.sleep(random.uniform(2, 5))
                    if settings.AUTO_TASK:
                        async with self.session.get("https://notpx.app/api/v1/mining/task/check/x?name=notpixel", headers=headers) as response:
                            if response.status == 200:
                                response_json = await response.json()
                                if response_json['x:notpixel'] and self.checked[1] is False:
                                    self.checked[1] = True
                                    logger.success("<green>Task Not pixel on x completed!</green>")

                        async with self.session.get("https://notpx.app/api/v1/mining/task/check/x?name=notcoin", headers=headers) as response:
                            if response.status == 200:
                                response_json = await response.json()
                                if response_json['x:notcoin'] and self.checked[2] is False:
                                    self.checked[2] = True
                                    logger.success("<green>Task Not coin on x completed!</green>")

                        async with self.session.get("https://notpx.app/api/v1/mining/task/check/paint20pixels", headers=headers) as response:
                            if response.status == 200:
                                response_json = await response.json()
                                if response_json['paint20pixels'] and self.checked[3] is False:
                                    self.checked[3] = True
                                    logger.success("<green>Task paint 20 pixels completed!</green>")

                    if settings.AUTO_UPGRADE_PAINT_REWARD:
                        await self.auto_upgrade_paint(self.session)
                    if settings.AUTO_UPGRADE_RECHARGE_SPEED:
                        await self.auto_upgrade_recharge_speed(self.session)
                    if settings.AUTO_UPGRADE_RECHARGE_ENERGY:
                        await self.auto_upgrade_energy_limit(self.session)

                else:
                    logger.warning(f"{self.session_name} | <yellow>Failed to get user data!</yellow>")
            else:
                logger.warning(f"invaild query: <yellow>{self.query}</yellow>")
            await self.close_session()
            await http_client.close()
        except InvalidSession as error:
            raise error
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error: {error}")
            await asyncio.sleep(delay=randint(5, 10))

async def run_query_tapper(query: str, name: str, proxy: str | None):
    try:
        sleep_ = randint(1, 5)
        logger.info(f" start after {sleep_}s")
        await Tapper(query=query, session_name=name, multi_thread=True).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"Invalid Query: {query}")

async def run_query_tapper1(querys: list[str], proxies):
    proxies_cycle = cycle(proxies) if proxies else None
    name = "Account"

    while True:
        i = 0
        for query in querys:
            try:
                await Tapper(query=query,session_name=f"{name} {i}",multi_thread=False).run(next(proxies_cycle) if proxies_cycle else None)
            except InvalidSession:
                logger.error(f"Invalid Query: {query}")

            sleep_ = randint(settings.DELAY_EACH_ACCOUNT[0], settings.DELAY_EACH_ACCOUNT[1])
            logger.info(f"Sleep {sleep_}s...")
            await asyncio.sleep(sleep_)

        sleep_ = randint(520, 700)
        logger.info(f"<red>Sleep {sleep_}s...</red>")
        await asyncio.sleep(sleep_)

# Hàm chạy nhiều Tapper đồng thời
async def run_tapper_with_semaphore(tapper, proxy):
    async with tapper_semaphore:
        sleep_ = randint(1, 5)
        logger.info(f" start after {sleep_}s")
        await asyncio.sleep(sleep_)
        await tapper.run(proxy)

async def run_multiple_tappers(queries, session_names, proxies):
    while True:
        tappers = [Tapper(query, name, True) for query, name in zip(queries, session_names)]
        proxies_cycle = cycle(proxies)
        
        tasks = [asyncio.create_task(run_tapper_with_semaphore(tapper, next(proxies_cycle))) 
                 for tapper in tappers]
        
        await asyncio.gather(*tasks)
        
        sleep_ = random.randint(settings.DELAY_AFTER_DONE_TAPPER[0], settings.DELAY_AFTER_DONE_TAPPER[1])
        logger.info(f"<red>Tất cả Tapper đã hoàn thành. Nghỉ {sleep_}s trước khi khởi động lại...</red>")
        await asyncio.sleep(sleep_)