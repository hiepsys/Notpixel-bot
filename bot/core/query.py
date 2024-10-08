import asyncio
import random
import json
import copy
from itertools import cycle
from tenacity import retry, stop_after_attempt, wait_fixed
import aiohttp
import aiofiles
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.core.agents import generate_random_user_agent
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from random import randint

import urllib3
from bot.utils.get_data import get_data

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
        self.query = query
        self.checked = [False] * 5
        self.multi_thread = multi_thread
        self.session_name = session_name
        self.charges = 0
        self.balance = 0
        self.headers = copy.deepcopy(headers)  # Tạo bản sao của headers chung
        self.setup_headers()

    def setup_headers(self):
        self.headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        # Cập nhật Authorization header với query của người dùng cụ thể
        self.headers['Authorization'] = f"initData {self.query}"

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            async with http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(15), ssl=settings.PROXY_CHECK_SSL) as response:
                ip = (await response.json()).get('origin')
                logger.info(f"{self.session_name} | Proxy IP: {ip}")
                return True
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def login(self, session: aiohttp.ClientSession):
        try:
            async with session.get("https://notpx.app/api/v1/users/me", headers=self.headers, timeout=aiohttp.ClientTimeout(30)) as response:
                if response.status == 200:
                    logger.success(f"{self.session_name} | <green>Đã đăng nhập thành công.</green>")
                    return True
                else:
                    print(await response.text())
                    logger.warning(f"{self.session_name} | <red>Đăng nhập thất bại</red>")
                    return False
        except asyncio.TimeoutError:
            logger.error(f"{self.session_name} | <red>Đăng nhập bị timeout. Thử lại...</red>")
            raise  # Raise lỗi để retry mechanism có thể bắt và thử lại
        except Exception as e:
            print(f"Lỗi khi đăng nhập: {str(e)}")
            logger.error(f"{self.session_name} | <red>Lỗi khi đăng nhập</red>")
            raise  # Raise lỗi để retry mechanism có thể bắt và thử lại

    async def get_user_data(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/status", headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.warning(f"{self.session_name} | <red>Không thể lấy dữ liệu người dùng</red>")
                return {}

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
        px_id = calc_id(random_cor['start'][0], random_cor['start'][1], random_cor['end'][0], random_cor['end'][1])
        return [color, px_id]

    async def repaint(self, session: aiohttp.ClientSession, chance_left):
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
        async with session.post("https://notpx.app/api/v1/repaint/start", headers=self.headers, json=payload) as response:
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

    async def repaintV2(self, session: aiohttp.ClientSession, charges_left, i, data):
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
        async with session.post("https://notpx.app/api/v1/repaint/start", headers=self.headers, json=payload) as response:
            if response.status == 200:
                response_json = await response.json()
                if i % 2 == 0:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data[0]}</cyan> | <light-blue>+{int(response_json['balance']) - self.balance}</light-blue> Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{charges_left}</yellow></green>")
                else:
                    logger.success(
                        f"{self.session_name} | <green>Đã vẽ <cyan>{data[1]}</cyan> thành công với màu mới: <cyan>{data1[0]}</cyan> | <light-blue>+{int(response_json['balance']) - self.balance}</light-blue> Số dư: <light-blue>{response_json['balance']}</light-blue> | Còn lại: <yellow>{charges_left}</yellow></green>")
                self.balance = int(response_json['balance'])
            else:
                print(await response.text())
                logger.warning(f"{self.session_name} | <yellow>Painted failed</yellow>")

    async def auto_upgrade_paint(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/paintReward", headers=self.headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade paint reward successfully!</green>")
        await asyncio.sleep(random.uniform(2,4))

    async def auto_upgrade_recharge_speed(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/reChargeSpeed", headers=self.headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade recharging speed successfully!</green>")
        await asyncio.sleep(random.uniform(2,4))

    async def auto_upgrade_energy_limit(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/boost/check/energyLimit", headers=self. headers) as response:
            if response.status == 200:
                logger.success(f"{self.session_name} | <green>Upgrade energy limit successfully!</green>")


    async def claimpx(self, session: aiohttp.ClientSession):
        async with session.get("https://notpx.app/api/v1/mining/claim", headers=self.headers) as response:
            if response.status == 200:
                response_json = await response.json()
                logger.success(f"{self.session_name} | <green>Successfully claimed <cyan>{response_json['claimed']} px</cyan> from mining!</green>")
            else:
                print(await response.text())
                logger.warning(f"{self.session_name} | <yellow>Failed to claim px from mining</yellow>")

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as session:
            if proxy:
                proxy_check = await self.check_proxy(session, proxy)
                if proxy_check:
                    logger.info(f"{self.session_name} | bind with proxy ip: {proxy}")
            try:
                query = await get_data(self.query)
                if query:
                    self.query = query
                    self.setup_headers()
                if await self.login(session):
                    await self.process_user(session)
                else:
                    logger.warning(f"{self.session_name} | <yellow>Đăng nhập không thành công query: {query}</yellow>")

            except InvalidSession as error:
                raise error
            except Exception as error:
                logger.error(f"{self.session_name} | Lỗi không xác định: {error}")
                await asyncio.sleep(delay=randint(5, 10))

    async def process_user(self, session):
        user_data = await self.get_user_data(session)
        self.balance = int(user_data.get('userBalance', 0))
        self.charges = int(user_data.get('charges', 0))
        logger.info(f"{self.session_name} | Số dư: <light-blue>{self.balance}</light-blue> | Lượt vẽ còn lại: <cyan>{self.charges}</cyan>")

        i = 0
        data = await self.get_cor()
        while self.charges > 0:
            i += 1
            self.charges -= 1
            if settings.X3POINTS:
                await self.repaintV2(session, self.charges, i, data)
            else:
                await self.repaint(session, self.charges)
            # await asyncio.sleep(random.uniform(1, 3))

        await self.handle_claim(session)
        await self.check_tasks(session)
        await self.auto_upgrade_tasks(session)

    async def handle_claim(self, session):
        # r = random.uniform(2, 4)
        # if float(self.fromstart) >= self.maxtime / r:
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
                async with session.get(url, headers=self.headers) as response:
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

async def run_query_tapper(query: str, proxy: str | None, name: str):
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
        sleep_ = random.randint(settings.DELAY_BEFORE_TAPPER[0], settings.DELAY_BEFORE_TAPPER[1])
        logger.info(f"<red>Sleep {sleep_}s...</red>")
        await asyncio.sleep(sleep_)
        await tapper.run(proxy)

async def run_multiple_tappers(queries, session_names, proxies):
    while True:
        tappers = [Tapper(query, session_name, True) for query, session_name in zip(queries, session_names)]
        proxies_cycle = cycle(proxies)
        
        tasks = [asyncio.create_task(run_tapper_with_semaphore(tapper, next(proxies_cycle))) 
                 for tapper in tappers]
        
        await asyncio.gather(*tasks)
        
        sleep_ = random.randint(settings.DELAY_AFTER_DONE_TAPPER[0], settings.DELAY_AFTER_DONE_TAPPER[1])
        logger.info(f"<red>Tất cả Tapper đã hoàn thành. Nghỉ {sleep_}s trước khi khởi động lại...</red>")
        await asyncio.sleep(sleep_)