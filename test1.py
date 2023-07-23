import time
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import os
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pynput import keyboard
from logging.handlers import RotatingFileHandler
import random
import sys
import pyautogui
from multiprocessing import Process
from configparser import ConfigParser
from bs4 import BeautifulSoup as bs
import json


class landCrawling():
    def __init__(self, conf_name):
        try:
            Process.__init__(self)
            config = ConfigParser()
            config.read(conf_name)

            self.set_logger(config.get("PATH", "LOG_PATH"))
            self.raw_data_dir = config.get("PATH", "DATA_PATH")

            self.refresh_wait_time = 2  # 새로고침 주기(초) / 기본값

            self.run_status = 0  # 0:중지 / 1:서칭 / -1:종료
            self.current_x, self.current_y = pyautogui.position()  # 마우스 현재 위치
            self.w, self.h = pyautogui.size()  # 화면 전체 사이즈

        except Exception as ex:
            print(f'__init__ Error: {str(ex)}')
        print(f"now dir: {os.getcwd()}")

        driver = webdriver.Chrome() #brew install --cask chromedriver 실행 후 가능
        driver.get('https://new.land.naver.com/complexes/1654?ms=37.3725959,127.1258526,17&a=APT:PRE&b=A1&e=RETAIL&ad=true')
        driver.implicitly_wait(time_to_wait=5)

        # temperature = WebDriverWait(driver, 10)

        html = driver.page_source
        # soup에 넣어주기
        soup = BeautifulSoup(html, 'html.parser')
        # print(soup.text) #텍스트로는 출력됨
        time.sleep(3)

        elements = soup.findAll('div', 'item_inner')
        for i in range(5):
            print(f"="*30)
            for index, element in enumerate(elements):
                print(f"{index}: {element}")
            self.scrolling(driver=driver)


        driver.find_element_by_tag_name('body').send_keys(Keys.PAGE_DOWN)
        # action = ActionChains(driver)
        # action.move_to_element(elements[-1]).perform()
        time.sleep(10)
        elements2 = soup.findAll('div', 'item_inner')
        time.sleep(100000)

    def set_logger(self, log_path):
        self.logger = logging.getLogger("landCrawling_index")
        self.logger.setLevel(logging.INFO)

        log_name = "landCrawling.log"
        formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(filename)s(%(lineno)d) %(message)s")
        # formatter = logging.Formatter("[%(asctime)s][%(levelname)s] (%(lineno)d) %(message)s")
        file_handler = RotatingFileHandler(os.path.join(log_path, log_name), maxBytes=5 * 1024 * 1024, backupCount=10)
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def scrolling(self, driver):
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            driver.execute_script("window.scrollBy(0, -10);")

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:  # 페이지 맨아래로 스크롤 완료 상태
                break

            last_height = new_height

    def main(self):
        print('start landCrawling')
        self.logger.info("start landCrawling")


if __name__ == '__main__':
    naverLand = landCrawling('./config/config.ini')
    naverLand.main()

    # find_element(By.ID, "id")
    # find_element(By.NAME, "name")
    # find_element(By.XPATH, "xpath")
    # find_element(By.LINK_TEXT, "link text")
    # find_element(By.PARTIAL_LINK_TEXT, "partial link text")
    # find_element(By.TAG_NAME, "tag name")
    # find_element(By.CLASS_NAME, "class name")
    # find_element(By.CSS_SELECTOR, "css selector")