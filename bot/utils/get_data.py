import time
import sys
import requests
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

def get_data(profileId):
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

    #chrome_options.arguments.extend(["--no-default-browser-check", "--no-first-run"])

    driver_path = startedResult["data"]["driver_path"]
    logger.info(f'Tiến hành lấy iframe')
    ser = Service(driver_path)
    # driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    driver = webdriver.Chrome(service=ser, options=chrome_options)
    # input()
    #userName = input('User name: ')
    #password = getpass('Password: ')
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
                # Tìm nút với thời gian chờ ngắn (ví dụ: 0.5 giây)
                button = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                # Nếu tìm thấy, thử click
                button.click()
                print(f"Đã click nút {button_name}")
            except (TimeoutException, NoSuchElementException):
                # Nếu không tìm thấy, bỏ qua và tiếp tục
                pass
            except Exception as e:
                # Xử lý các lỗi khác nếu có
                print(f"Lỗi khi xử lý nút {button_name}: {str(e)}")

    except Exception as e:
        logger.error(f"<red>Lỗi không xác định: {str(e)}</red>")

    try:
        # Đợi cho đến khi phần tử iframe xuất hiện hoặc hết thời gian chờ (60 giây)
        iframe = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//iframe[@class="payment-verification"]'))
        )
        # Lấy thuộc tính src của iframe
        iframe_src = iframe.get_attribute('src')
        # Xử lý src để lấy dữ liệu WebApp
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