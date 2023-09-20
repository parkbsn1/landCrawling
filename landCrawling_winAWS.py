# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import os
import platform
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup as bs

from logging.handlers import RotatingFileHandler
from multiprocessing import Process
from configparser import ConfigParser

import sendingEmail
import sys

class landCrawling():
    def __init__(self, conf_name):
        try:
            Process.__init__(self)
            config = ConfigParser()
            config.read(conf_name)
            sys.stdin.reconfigure(encoding="utf-8")
            sys.stdout.reconfigure(encoding="utf-8")

            if 'macOS' in platform.platform():
                self.os_name = 'mac'
            elif 'win' in platform.platform().lower():
                self.os_name = 'win'
            else:
                self.os_name = 'etc'

            if self.os_name == 'win':
                self.set_logger(config.get("PATH", "LOG_PATH").replace('/','\\'))
                self.data_dir = config.get("PATH", "DATA_PATH").replace('/','\\')
                self.url_list = config.get("PATH", "URL_LIST").replace('/','\\')
            else:
                self.set_logger(config.get("PATH", "LOG_PATH"))
                self.data_dir = config.get("PATH", "DATA_PATH")
                self.url_list = config.get("PATH", "URL_LIST")


            self.confirm_limit_day = (datetime.now() - timedelta(days=int(config.get("OPTION", "CONFIRM_LIMIT_DATE")))).strftime('%y.%m.%d') +'.'
            self.time_sleep_int1 = int(config.get("OPTION", "TIME_SLEEP_INT1"))
            self.time_sleep_int2 = int(config.get("OPTION", "TIME_SLEEP_INT2"))
            self.time_sleep_int3 = int(config.get("OPTION", "TIME_SLEEP_INT3"))
            self.mail_send_flag = (config.get("OPTION", "MAIL_SEND"))
            self.datetime_now = datetime.now().strftime('%Y%m%d%H%M%S')
        except Exception as ex:
            print(f'__init__ Error: {str(ex)}')

    def set_logger(self, log_path):
        self.logger = logging.getLogger("landCrawling_index")
        self.logger.setLevel(logging.INFO)

        log_name = "landCrawling.log"
        # formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(filename)s(%(lineno)d) %(message)s")
        formatter = logging.Formatter("[%(asctime)s][%(levelname)s] (%(lineno)d) %(message)s")
        file_handler = RotatingFileHandler(os.path.join(log_path, log_name), maxBytes=5 * 1024 * 1024,
                                           backupCount=10, encoding='utf-8')
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def print_config_info(self):
        self.logger.info(f"os_name: {self.os_name}")
        self.logger.info(f"data_dir: {self.data_dir}")
        self.logger.info(f"url_list: {self.url_list}")
        self.logger.info(f"confirm_limit_day: {self.confirm_limit_day}")
        self.logger.info(f"time_sleep_int1: {self.time_sleep_int1}")
        self.logger.info(f"time_sleep_int2: {self.time_sleep_int2}")
        self.logger.info(f"time_sleep_int3: {self.time_sleep_int3}")
        self.logger.info(f"mail_send_flag: {self.mail_send_flag}")
        self.logger.info(f"datetime_now: {self.datetime_now}")
        self.logger.info(f"--------------------------------------------------")


    def start_crawling(self, urls) -> list:
        self.logger.info("start landCrawling")
        landResult = []

        # chrome option 세팅
        options = webdriver.ChromeOptions()  # Browser 세팅하기
        options.add_argument('lang=ko_KR')  # 사용언어 한국어
        #options.add_argument('disable-gpu')  # 하드웨어 가속 안함
        options.add_argument('Content-Type=application/json; charset=utf-8')
        #options.add_argument("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36")
        #options.add_argument('headless') # 창 숨기기


        # 브라우저 옵션 적용
        # driver = webdriver.Chrome(options=options)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        for landName, url in urls.items():
            try_cnt = 0
            while(try_cnt < 3):
                land_info = self.get_land_info(driver, landName, url)
                if land_info != -1:
                    landResult.extend(land_info)
                    break
                elif(land_info == -2):
                    break
                else:
                    try_cnt = try_cnt + 1
                    driver.refresh()
                    self.logger.info(f"{landName} {try_cnt}회 실패")
        driver.quit()
        self.logger.info(f"총 {len(landResult)}건 파싱 완료")
        return landResult

    def get_land_info(self, driver,landName, url):
        try:
            # URL 호출
            driver.get(url)
            driver.implicitly_wait(time_to_wait=self.time_sleep_int3)
            time.sleep(self.time_sleep_int2)
            complex_title = driver.find_element(By.ID, "complexTitle").text
            self.logger.info("-" * 50)
            self.logger.info(f"{complex_title} Crawling Start!")
            crawledItems = driver.find_elements(By.CLASS_NAME,"item_inner")

            #매물 건수 파싱 -> land_count = {'매매': 33, '전세': 28}
            html = driver.page_source
            soup = bs(html, 'html.parser')
            tmp = soup.findAll('div', 'complex_infos')
            land_count = {}
            time.sleep(3)
            for index, landTitle in enumerate(tmp):
                # self.logger.info(f"{landTitle.find('div', 'complex_title').text}")
                if landTitle.find('div', 'complex_title').text != complex_title:
                    continue
                for index2, landType in enumerate(landTitle.findAll('button', 'article_link')):
                    if landType.find('span', 'type').text in ['매매','전세','월세']:
                        self.logger.info(f"{complex_title}: {landType.find('span', 'type').text} {int(landType.find('span', 'count').text)}")
                        land_count[landType.find('span', 'type').text] = int(landType.find('span', 'count').text)
            self.logger.info(f"매물 개수: {land_count}")

            time.sleep(self.time_sleep_int2)
            #매물정보가 없는 경우
            if len(crawledItems) == 0:
                self.logger.info(f"{complex_title} 매물 정보 없음")
                return -1

            #매물이 소수(5개 이하)인 경우
            elif len(crawledItems) < 5:
                html = driver.page_source
                soup = bs(html, 'html.parser')
                self.logger.info(f"{1}: 수집({len(crawledItems)}) | {round((len(crawledItems) / len(crawledItems)) * 100)}% )")

            #매물이 다수인 경우
            else:
                time.sleep(3)
                maxLen = len(crawledItems)
                # time_value = 5
                totalLandCount = sum([v for v in land_count.values()])
                for i in range(50):
                    if len(crawledItems) == totalLandCount:
                        break
                    crawledItems = driver.find_elements(By.CLASS_NAME, "item_inner")
                    # if maxLen == len(crawledItems) and totalLandCount > maxLen:
                    #     time.sleep(time_value)
                    #     time_value = time_value + 1
                    # else:
                    #     time_value = 5
                    click_idx = -1
                    try:
                        time.sleep(self.time_sleep_int2)
                        if "네이버에서 보기" in crawledItems[click_idx].text:
                            view_naver = crawledItems[click_idx].find_element(By.LINK_TEXT, '네이버에서 보기')
                            time.sleep(self.time_sleep_int1)
                            view_naver.click()
                        else:
                            time.sleep(self.time_sleep_int1)
                            crawledItems[click_idx].click()
                    except Exception as ex:
                        self.logger.critical(f"click error")

                    html = driver.page_source
                    # soup에 넣어주기
                    soup = bs(html, 'html.parser') #.encode("utf-8")
                    self.logger.info(
                        f"{i + 1}: 수집({len(crawledItems)}) | 대상({totalLandCount}) | {round((len(crawledItems) / totalLandCount) * 100)}% )")
                    if len(crawledItems) <= maxLen and len(crawledItems) >= totalLandCount:
                        break
                    else:
                        maxLen = len(crawledItems)
            landItems = soup.findAll('div', 'item_inner')
            self.logger.info(f"{complex_title} 매물 수집({len(crawledItems)}건) 완료")
            res = []
            except_cnt = 0
            for index, value in enumerate(landItems):
                try:
                    if value.find('em', 'data').string < self.confirm_limit_day:
                        except_cnt = except_cnt + 1
                        continue
                    tmp_dict = {}
                    tmp_dict["confirm_date"] = value.find('em', 'data').string  # 23.07.13.
                    tmp_dict["complex_title"] = landName #complex_title
                    # tmp_dict["land_title"], tmp_dict["dong"] = (value.find('div','item_title').find('span','text').string).split(' ') #샛별삼부 408동
                    tmp_dict["item_title"] = value.find('div', 'item_title').find('span', 'text').string  # 샛별삼부 408동
                    tmp_dict["price_type"] = value.find('div', 'price_line').find('span', 'type').string #전세
                    if tmp_dict["price_type"] in ['매매','전세']: #매매, 전세
                        tmp_dict["price"] = value.find('div', 'price_line').find('span', 'price').string #7억 5,000
                        tmp_dict["price_int"] = self.get_price_int(value.find('div', 'price_line').find('span', 'price').string, tmp_dict["price_type"])
                    else: #월세
                        tmp_dict["price"] = value.find('div', 'price_line').get_text()[2:]
                        tmp_dict["price_int"] = self.get_price_int(tmp_dict["price"].split('/')[0])
                    tmp_dict["land_type"] = value.find('div', 'info_area').find('strong','type').string #아파트
                    # tmp_dict["info_area_spec"] = (value.find('div', 'info_area').find('span','spec').string).replace('\n','') #158/128m², 15/25층, 남동향
                    tmp_dict["area_m"], tmp_dict["floor"], tmp_dict["direction"] = (value.find('div', 'info_area').find('span', 'spec').string).replace('\n', '').split(',')  # 158/128m², 15/25층, 남동향
                    tmp_dict["area_p"] = self.get_area_num(tmp_dict["area_m"])
                    tmp_dict["info_area_spec2"] = (value.find('div', 'info_area').get_text().split(',')[-1]).replace('\n','').strip() #8월중입주협의
                    #tmp_dict["raw_text"] = value.get_text().replace('\n','')
                    res.append(tmp_dict)
                except Exception as ex:
                    self.logger.critical(f"{complex_title} 파싱 실패: {value}")
                    self.logger.critical(f"{ex}")
            self.logger.info(f"{complex_title}: {len(res)}건 (*{self.confirm_limit_day}이전: {except_cnt}건 )")
            return res
        except Exception as ex:
            self.logger.critical(f"get_land_info Error")
            self.logger.critical(f"{ex}")
            return -2

    def get_area_num(self, area_m):
        try:
            regex = re.compile(r'(\d+)\S*\/(\d+)')
            area_num = regex.search(area_m)
            area_m = area_m.replace(area_num.group(1), str(round(int(area_num.group(1))*0.3025)) )
            area_m = area_m.replace(area_num.group(2), str(round(int(area_num.group(2))*0.3025)) )
            area_m = area_m[:-2]+"평"
            return area_m
        except Exception as ex:
            self.logger.critical(f"get_area_num:{area_m} | {ex}")
            return '-/-평'

    def get_price_int(self, price_str, price_type=''):
        try:
            regex = re.compile(r'((\d+)[억]\s*)*([\d\,]+)*')
            r = regex.search(price_str)
            price_int = 0
            if r.group(2) is not None:
                price_int = price_int + int(r.group(2))
            if r.group(3) is not None:
                price_int = price_int + int(r.group(3).replace(',','')) / 10000
            return price_int

        except Exception as ex:
            self.logger.critical(f"get_price_int: {price_str} | {ex}")
            return 0


    def read_url_file(self) -> dict:
        try:
            if self.os_name == 'win':
                read_full_path = os.path.join(os.getcwd(), self.url_list.replace('/','\\'))
            elif self.os_name == 'mac':
                read_full_path = os.path.join(os.getcwd(), self.url_list)
            else:
                read_full_path = os.path.join(os.getcwd(), self.url_list)

            f = open(f'{read_full_path}', 'r', encoding='utf-8' )
            lines = f.readlines()
            urls_dict = {line.split('|', 1)[0].strip(): line.split('|', 1)[1].strip() for line in lines}
            f.close()
            return urls_dict
        except Exception as ex:
            self.logger.critical(f"URL 파일 불러오기 실패 {ex}")
            return []

    def list_to_df(self, data) -> set:
        try:
            df = pd.DataFrame.from_records(data)
            df = df.sort_values(by=['complex_title','item_title','price_type','price','area_m','floor','direction','confirm_date'],ascending=[True,True,True,True,True,True,True,False])
            df = df.drop_duplicates(subset=['complex_title','item_title','price_type','price','area_m','floor','direction'])
            brif_df = df[['complex_title', 'area_p']].drop_duplicates(subset=['complex_title', 'area_p']).reset_index(drop=True)
            price_m_list = []
            price_j_list = []
            jeonse_rate = []
            jeonse_sub = []
            for idx, value in brif_df.iterrows():
                price_m = df[(df['complex_title'] == value['complex_title']) & (df['area_p'] == value['area_p']) & (
                            df['price_type'] == '매매')]['price_int'].min()
                price_m = price_m if price_m == price_m else 0
                price_j = df[(df['complex_title'] == value['complex_title']) & (df['area_p'] == value['area_p']) & (
                            df['price_type'] == '전세')]['price_int'].max()
                price_j = price_j if price_j == price_j else 0

                price_m_list.append(price_m)
                price_j_list.append(price_j)
                if price_m > 0:
                    jeonse_sub.append(round(price_m - price_j, 1))
                    jeonse_rate.append(round(price_j/price_m*100, 1))
                else:
                    jeonse_sub.append(0)
                    jeonse_rate.append(0)
            brif_df['price_m'] = price_m_list
            brif_df['price_j'] = price_j_list
            brif_df['jeonse_sub'] = jeonse_sub
            brif_df['jeonse_rate'] = jeonse_rate

            # 정렬
            brif_df = brif_df.sort_values(['complex_title', 'area_p'], ascending=False)
            brif_df.rename(columns=self.get_rename_col_dict(), inplace=True)
            df.rename(columns=self.get_rename_col_dict(), inplace=True)
            return (df, brif_df)
        except Exception as ex:
            self.logger.critical(f"Excel 저장 에러 {ex}")

    def get_rename_col_dict(self)->dict:
        rename_col_dict = {
            'complex_title': '아파트명',
            'area_p': '면적(평)',
            'area_m': '면적(m²)',
            'price_type': '거래유형',
            'item_title': '동',
            'price': '가격',
            'price_int': '가격(단위:억)',
            'land_type': '건물타입',
            'floor': '층',
            'direction': '방향',
            'info_area_spec1': '상세정보',
            'info_area_spec2': '비고',
            'confirm_date': '매물확인날짜',
            'price_m': '매매가_최소(억원)',
            'price_j': '전세가_최대(억원)',
            'jeonse_sub': '갭차이(억원)',
            'jeonse_rate': '전세가율(%)',
        }
        return rename_col_dict

    def write_to_excel(self, df, brif_df):
        try:
            if self.os_name == 'win':
                file_path = os.path.join(os.getcwd() + self.data_dir.replace('/', '\\'))
            elif self.os_name == 'mac':
                file_path = os.path.join(os.getcwd(), self.data_dir)
            else:
                file_path = os.path.join(os.getcwd(), self.data_dir)
            file_name = self.datetime_now+'.xlsx'
            file_full_path = os.path.join(file_path, file_name)
            self.logger.info(f"Excel 저장 준비 {file_full_path}")

            writer = pd.ExcelWriter(file_full_path, engine="xlsxwriter")
            df.to_excel(writer, sheet_name='전체 리스트', index=False)
            brif_df.to_excel(writer, sheet_name='요약', index=False)
            writer.close()
            self.logger.info(f"Excel 저장 {file_full_path}")
            return file_full_path
        except Exception as ex:
            self.logger.critical(f"Excel 저장 에러 {ex}")
            return None

    def main(self):
        self.logger.info("="*50)
        self.print_config_info()
        urls = self.read_url_file()
        ladnList = self.start_crawling(urls) #매개변수: url, return 값: list[dict{}]
        df, brif_df = self.list_to_df(ladnList)
        # self.write_to_excel(df, brif_df)
        excel_file = self.write_to_excel(df, brif_df)
        if self.mail_send_flag == 'Y' or self.mail_send_flag == 'y':
            sendEmail = sendingEmail.sendingEmail('./config/config.ini')
            sendEmail.send_gmail(excel_file)

if __name__ == '__main__':
    naverLand = landCrawling('./config/config.ini')
    naverLand.main()
