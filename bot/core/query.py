import asyncio
import random
import json
from itertools import cycle
from tenacity import retry, stop_after_attempt, wait_fixed
import aiohttp
import aiofiles
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

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            async with http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(15)) as response:
                ip = (await response.json()).get('origin')
                logger.info(f"{self.session_name} | Proxy IP: {ip}")
                return True
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def login(self, session: aiohttp.ClientSession):
        try:
            async with session.get("https://notpx.app/api/v1/users/me", 
                                   headers=headers, 
                                   timeout=aiohttp.ClientTimeout(total=30)) as response:  # Tăng timeout lên 30 giây
                if response.status == 200:
                    logger.success(f"{self.session_name} | <green>Đã đăng nhập thành công.</green>")
                    return True
                else:
                    logger.warning(f"{self.session_name} | <red>Đăng nhập thất bại: {await response.text()}</red>")
                    return False
        except asyncio.TimeoutError:
            logger.error(f"{self.session_name} | <red>Đăng nhập bị timeout. Thử lại...</red>")
            raise  # Raise lỗi để retry mechanism có thể bắt và thử lại
        except Exception as e:
            logger.error(f"{self.session_name} | <red>Lỗi khi đăng nhập: {str(e)}</red>")
            raise  # Raise lỗi để retry mechanism có thể bắt và thử lại

    async def get_user_data(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/status", headers=headers) as response:
            response_json = await response.json()
            if response.status == 200:
                return response_json
            else:
                logger.warning(f"{self.session_name} | <red>Không thể lấy dữ liệu người dùng: {response_json}</red>")
                return None

    def generate_random_color(self):
        r = randint(0, 255)
        g = randint(0, 255)
        b = randint(0, 255)
        return "#{:02X}{:02X}{:02X}".format(r, g, b)

    def generate_random_pos(self):
        return randint(1, 1000000)

    async def get_cor(self):
        async with aiofiles.open('bot/utils/3xdata.json', 'r') as file:
            cor = await file.read()
            cor = json.loads(cor)

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
            if response.status == 200:
                response_json = await response.json()
                if i % 2 == 0:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data[0]}</cyan> | Đã kiếm được <light-blue>{int(response_json['balance']) - int(self.balance)}</light-blue> | Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
                else:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data1[0]}</cyan> | Đã kiếm được <light-blue>{int(response_json['balance']) - int(self.balance)}</light-blue> | Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{chance_left}</yellow></green>")
                    self.balance = int(response_json['balance'])
            else:
                logger.warning(f"{self.session_name} | <yellow>{await response.text()}</yellow>")

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

    # async def get_data_async(self, query: str):
    # # Sử dụng asyncio.to_thread thay vì ThreadPoolExecutor để xử lý hàm đồng bộ trong thread khác
    #     result = await asyncio.to_thread(get_data, query)
    #     return result

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        # Sử dụng async with cho session và CloudflareScraper
        async with aiohttp.ClientSession(headers=headers) as session:
            headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
            async with CloudflareScraper(headers=headers, connector=proxy_conn) as http_client:

                # Kiểm tra và thiết lập proxy
                if proxy:
                    proxy_check = await self.check_proxy(http_client=http_client, proxy=proxy)
                    if proxy_check:
                        proxy_type = proxy.split(':')[0]
                        session.proxies = {proxy_type: proxy}
                        logger.info(f"{self.session_name} | bind with proxy ip: {proxy}")

                try:
                    query = await get_data(self.query)
                    if query:
                        self.query = query
                    headers['Authorization'] = f"initData {query}"

                    # Login và lấy dữ liệu user
                    if await self.login(session):
                        user = await self.get_user_data(session)
                        if user:
                            await self.process_user(session, user)
                        else:
                            logger.warning(f"{self.session_name} | <yellow>Không thể lấy dữ liệu người dùng!</yellow>")
                    else:
                        logger.warning(f"{self.session_name} | <yellow>Đăng nhập không thành công query: {self.query}</yellow>")

                except InvalidSession as error:
                    raise error
                except Exception as error:
                    logger.error(f"{self.session_name} | Lỗi không xác định: {error}")
                    await asyncio.sleep(delay=randint(5, 10))

    async def process_user(self, session, user):
        self.maxtime = user['maxMiningTime']
        self.fromstart = user['fromStart']
        self.balance = int(user['userBalance'])

        logger.info(
            f"{self.session_name} | Số dư: <light-blue>{self.balance}</light-blue> | Lượt vẽ còn lại: <cyan>{user['charges']}</cyan>")

        if int(user['charges']) > 0:
            await self.handle_painting(session, user['charges'])

        await self.handle_claim(session)
        await self.check_tasks(session)
        await self.auto_upgrade_tasks(session)

    async def handle_painting(self, session, total_chance):
        i = 0
        data = await self.get_cor()
        while int(total_chance) > 0:
            total_chance -= 1
            i += 1
            if settings.X3POINTS:
                await self.repaintV2(session, total_chance, i, data)
            else:
                await self.repaint(session, total_chance)

    async def handle_claim(self, session):
        r = random.uniform(2, 4)
        if float(self.fromstart) >= self.maxtime / r:
            await self.claimpx(session)
            await asyncio.sleep(random.uniform(2, 5))

    async def check_tasks(self, session):
        if settings.AUTO_TASK:
            task_urls = [
                ("https://notpx.app/api/v1/mining/task/check/x?name=notpixel", 1, "Task Not pixel on x hoàn thành!"),
                ("https://notpx.app/api/v1/mining/task/check/x?name=notcoin", 2, "Task Not coin on x hoàn thành!"),
                ("https://notpx.app/api/v1/mining/task/check/paint20pixels", 3, "Task paint 20 pixels hoàn thành!")
            ]
            for url, index, success_msg in task_urls:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        if response_json.get(f'x:notpixel', False) and not self.checked[index]:
                            self.checked[index] = True
                            logger.success(f"<green>{success_msg}</green>")

    async def auto_upgrade_tasks(self, session):
        if settings.AUTO_UPGRADE_PAINT_REWARD:
            await self.auto_upgrade_paint(session)
        if settings.AUTO_UPGRADE_RECHARGE_SPEED:
            await self.auto_upgrade_recharge_speed(session)
        if settings.AUTO_UPGRADE_RECHARGE_ENERGY:
            await self.auto_upgrade_energy_limit(session)

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