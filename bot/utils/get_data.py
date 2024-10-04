import time
import sys
import requests
from bot.utils import logger
sys.path.append("..")
from bot.utils.GPMLoginAPI import GPMLoginAPI
from selenium import webdriver
from selenium.webdriver.chrome import service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def get_data(profileId):
    api = GPMLoginAPI("http://127.0.0.1:19995")
    startedResult = api.Start(profileId)
    
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
    print('Tiến hành lấy iframe')
    ser = Service(driver_path)
    # driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
    driver = webdriver.Chrome(service=ser, options=chrome_options)
    # input()
    #userName = input('User name: ')
    #password = getpass('Password: ')
    driver.get("https://web.telegram.org/k/#@lhsdevlink")
    time.sleep(3)
    try:
        refLink = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, '(//a[contains(@href,"https://t.me/notpixel")])[1]'))
        )
        refLink.click()
        time.sleep(4)

        # buttons = [
        #     ("START", '(//button[@class="btn-primary btn-transparent text-bold chat-input-control-button rp"]//span[text()="START"])[2]'),
        #     ("PLAY NOW", '(//span[@class="reply-markup-button-text"])[1]'),
        #     ("Launch", '//span[text()="Launch"]'),
        #     ("Play", '//div[@class="new-message-bot-commands-view"]'),
        #     ("Confirm", '//span[text()="Confirm"]')
        # ]

        # for button_name, xpath in buttons:
        #     try:
        #         button = WebDriverWait(driver, 1).until(
        #             EC.element_to_be_clickable((By.XPATH, xpath))
        #         )
        #         print(f"Nút {button_name} đã xuất hiện và có thể click")
        #         button.click()
        #         time.sleep(3)
        #     except TimeoutException:
        #         print(f"Không tìm thấy nút {button_name} sau 1 giây")

    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")

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
            print(decoded_data)
        else:
            print("Không tìm thấy dữ liệu WebApp trong src của iframe")
    except TimeoutException:
        print("Không tìm thấy iframe payment-verification sau 60 giây")

    driver.close()
    driver.quit()
    return decoded_data