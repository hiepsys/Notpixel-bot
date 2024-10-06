import time
import sys
import requests
import asyncio
from bot.utils import logger
from random import randint
from bot.config import settings
sys.path.append("..")
from bot.utils.GPMLoginAPI import GPMLoginAPI
from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Define a helper function for running selenium code in a separate thread
async def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

# Keep the original synchronous version of get_data, which will be run in a separate thread
def sync_get_data(profileId):
    api = GPMLoginAPI(settings.GPM_API_URL)
    win_pos = f"{200*randint(1,20)},20"
    startedResult = api.Start(profileId, win_size='500,700', win_scale='0.4', win_pos=win_pos)
    
    time.sleep(3)

    chrome_options = Options()
    chrome_options.headless = True
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_experimental_option("debuggerAddress", startedResult["data"]["remote_debugging_address"])
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")

    driver_path = startedResult["data"]["driver_path"]
    logger.info(f'Tiến hành lấy iframe')
    ser = Service(driver_path)
    driver = webdriver.Chrome(service=ser, options=chrome_options)

    driver.get(settings.CHANNEL_REF_LINK)
    time.sleep(1)
    
    try:
        refLink = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, f'(//a[contains(@href,"https://t.me/{settings.BOT_NAME}")])[1]'))
        )
        refLink.click()
        time.sleep(2)

        buttons = [
            ("START", '(//button[@class="btn-primary btn-transparent text-bold chat-input-control-button rp"]//span[text()="START"])[2]'),
            ("PLAY NOW", '(//span[@class="reply-markup-button-text"])[1]'),
            ("Launch", '//span[text()="Launch"]'),
            ("Play", '//div[@class="new-message-bot-commands-view"]'),
            ("Confirm", '//span[text()="Confirm"]')
        ]

        for button_name, xpath in buttons:
            try:
                button = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                button.click()
                print(f"Đã click nút {button_name}")
            except (TimeoutException, NoSuchElementException):
                pass
            except Exception as e:
                print(f"Lỗi khi xử lý nút {button_name}: {str(e)}")

    except Exception as e:
        logger.error(f"<red>Lỗi không xác định: {str(e)}</red>")

    try:
        iframe = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//iframe[@class="payment-verification"]'))
        )
        iframe_src = iframe.get_attribute('src')
        index1 = iframe_src.find("#tgWebAppData")
        index2 = iframe_src.find("&tgWebAppVersion")
        if index1 != -1 and index2 != -1:
            encoded_data = iframe_src[index1 + 14:index2]
            decoded_data = requests.utils.unquote(encoded_data)
            logger.success(f'<green>Lấy iframe thành công</green>')
        else:
            logger.error("<red>Không tìm thấy dữ liệu WebApp trong src của iframe</red>")
    except TimeoutException:
        logger.error("<red>Không tìm thấy iframe payment-verification sau 60 giây</red>")

    driver.close()
    driver.quit()
    return decoded_data

# Create the asynchronous wrapper for get_data
async def get_data(profileId):
    decoded_data = await run_in_executor(sync_get_data, profileId)
    return decoded_data
