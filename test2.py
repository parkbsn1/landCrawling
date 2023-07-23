import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By

import os
import re
import logging
import pandas as pd
from bs4 import BeautifulSoup as bs
import xlsxwriter

from logging.handlers import RotatingFileHandler
from multiprocessing import Process
from configparser import ConfigParser

class landCrawling():
    def __init__(self, conf_name):
        try:
            Process.__init__(self)
            config = ConfigParser()
            config.read(conf_name)

            self.set_logger(config.get("PATH", "LOG_PATH"))
            self.data_dir = config.get("PATH", "DATA_PATH")
            self.url_list = config.get("PATH", "URL_LIST")

            self.confirm_limit_day = (datetime.now() - timedelta(days=int(config.get("OPTION", "CONFIRM_LIMIT_DATE")))).strftime('%y.%m.%d') +'.'
            self.datetime_now = datetime.now().strftime('%Y%m%d%H%M%S')


        except Exception as ex:
            print(f'__init__ Error: {str(ex)}')
        print(f"now dir: {os.getcwd()}")

    def set_logger(self, log_path):
        self.logger = logging.getLogger("landCrawling_index")
        self.logger.setLevel(logging.INFO)

        log_name = "landCrawling.log"
        formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(filename)s(%(lineno)d) %(message)s")
        # formatter = logging.Formatter("[%(asctime)s][%(levelname)s] (%(lineno)d) %(message)s")
        file_handler = RotatingFileHandler(os.path.join(log_path, log_name), maxBytes=5 * 1024 * 1024,
                                           backupCount=10)
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def start_crawling(self, urls) -> list:
        self.logger.info("start landCrawling")
        # driver = webdriver.Chrome()  # brew install --cask chromedriver 실행 후 가능
        landResult = []
        #chrome option 세팅
        options = webdriver.ChromeOptions()  # Browser 세팅하기
        options.add_argument('lang=ko_KR')  # 사용언어 한국어
        options.add_argument('disable-gpu')  # 하드웨어 가속 안함
        # options.add_argument('headless') # 창 숨기기

        # 브라우저 옵션 적용
        driver = webdriver.Chrome(options=options)

        for landName, url in urls.items():
            try:
                # URL 호출
                driver.get(url)
                driver.implicitly_wait(time_to_wait=10)
                time.sleep(1)
                complex_title = driver.find_element(By.ID, "complexTitle").text
                self.logger.info("-" * 50)
                self.logger.info(f"{complex_title} Crawling Start!")
                crawledItems = driver.find_elements(By.CLASS_NAME,"item_inner")

                #매물 건수 파싱 -> land_count = {'매매': 33, '전세': 28}
                html = driver.page_source
                soup = bs(html, 'html.parser')
                tmp = soup.findAll('div', 'complex_infos')
                land_count = {}
                for index, landTitle in enumerate(tmp):
                    # self.logger.info(f"{landTitle.find('div', 'complex_title').text}")
                    if landTitle.find('div', 'complex_title').text != complex_title:
                        continue
                    for index2, landType in enumerate(landTitle.findAll('button', 'article_link')):
                        if landType.find('span', 'type').text in ['매매','전세','월세']:
                            self.logger.info(f"{complex_title}: {landType.find('span', 'type').text}-{int(landType.find('span', 'count').text)}")
                            land_count[landType.find('span', 'type').text] = int(landType.find('span', 'count').text)
                self.logger.info(f"매물 개수: {land_count}")
                #매물정보가 없는 경우
                if len(crawledItems) == 0:
                    self.logger.critical(f"{complex_title} 매물 정보 없음")
                    continue

                #매물이 소수(5개 이하)인 경우
                elif len(crawledItems) < 5:
                    html = driver.page_source
                    soup = bs(html, 'html.parser')
                    landItems = soup.findAll('div', 'item_inner')
                    self.logger.info(f"{1}: 수집({len(crawledItems)}) | {round((len(crawledItems) / len(crawledItems)) * 100)}% )")

                #매물이 다수인 경우
                else:
                    maxLen = len(crawledItems)
                    time_value = 5
                    totalLandCount = sum([v for v in land_count.values()])
                    for i in range(50):
                        if len(crawledItems) == totalLandCount:
                            break
                        crawledItems = driver.find_elements(By.CLASS_NAME, "item_inner")
                        if maxLen == len(crawledItems) and totalLandCount > maxLen:
                            time.sleep(time_value)
                            time_value = time_value + 1
                        else:
                            time_value = 5
                        click_idx = -1

                        if "네이버에서 보기" in crawledItems[click_idx].text:
                            # self.logger.info(f"click index{click_idx}\n{crawledItems[click_idx].text}")
                            view_naver = crawledItems[click_idx].find_element(By.LINK_TEXT, '네이버에서 보기')
                            view_naver.click()
                        else:
                            crawledItems[click_idx].click()
                        time.sleep(1)

                        html = driver.page_source
                        # soup에 넣어주기
                        soup = bs(html, 'html.parser')
                        # landItems = soup.findAll('div', 'item_inner')
                        # self.logger.info(f"{i + 1}: crawledItems({len(crawledItems)}) | landItem_cnt({len(landItems)})")
                        # self.logger.info(f"{i + 1}: 수집({len(crawledItems)}) | 대상({len(landItems)}) | {round((len(crawledItems) / len(landItems)) * 100)}% )")
                        self.logger.info(
                            f"{i + 1}: 수집({len(crawledItems)}) | 대상({totalLandCount}) | {round((len(crawledItems) / totalLandCount) * 100)}% )")
                        # if len(landItems) <= maxLen:
                        if len(crawledItems) <= maxLen and len(crawledItems) == totalLandCount:
                            break
                        else:
                            maxLen = len(crawledItems)
                landItems = soup.findAll('div', 'item_inner')
                self.logger.info(f"{complex_title} 매물 수집({len(crawledItems)}건) 완료")
                res = []
                for index, value in enumerate(landItems):
                    try:
                        if value.find('em', 'data').string < self.confirm_limit_day:
                            continue
                        tmp_dict = {}
                        tmp_dict["confirm_date"] = value.find('em', 'data').string  # 23.07.13.
                        tmp_dict["complex_title"] = landName #complex_title
                        # tmp_dict["land_title"], tmp_dict["dong"] = (value.find('div','item_title').find('span','text').string).split(' ') #샛별삼부 408동
                        tmp_dict["item_title"] = value.find('div', 'item_title').find('span', 'text').string  # 샛별삼부 408동
                        tmp_dict["price_type"] = value.find('div', 'price_line').find('span', 'type').string #전세
                        tmp_dict["price"] = value.find('div', 'price_line').find('span', 'price').string #7억 5,000
                        tmp_dict["price_int"] = self.get_price_int(value.find('div', 'price_line').find('span', 'price').string)
                        tmp_dict["land_type"] = value.find('div', 'info_area').find('strong','type').string #아파트
                        # tmp_dict["info_area_spec"] = (value.find('div', 'info_area').find('span','spec').string).replace('\n','') #158/128m², 15/25층, 남동향
                        tmp_dict["area_m"], tmp_dict["floor"], tmp_dict["direction"] = (value.find('div', 'info_area').find('span', 'spec').string).replace('\n', '').split(',')  # 158/128m², 15/25층, 남동향
                        tmp_dict["area_p"] = self.get_area_num(tmp_dict["area_m"])
                        tmp_dict["info_area_spec2"] = (value.find('div', 'info_area').get_text().split(',')[-1]).replace('\n','').strip() #8월중입주협의

                        #tmp_dict["raw_text"] = value.get_text().replace('\n','')
                        res.append(tmp_dict)
                    except Exception as ex:
                        self.logger.critical(f"{complex_title} 파싱 실패: {value}")
                landResult.extend(res)
                self.logger.info(f"{complex_title}: {len(res)}건")
            except Exception as ex:
                self.logger.critical(f"{url} landCrawling 실패 {ex}")

        driver.quit()
        self.logger.info(f"총 {len(landResult)}건 파싱 완료")
        return landResult

    def get_area_num(self, area_m):
        try:
            regex = re.compile(r'(\d+)\w*\/(\d+)')
            area_num = regex.search(area_m)
            area_m = area_m.replace(area_num.group(1), str(round(int(area_num.group(1))*0.3025)) )
            area_m = area_m.replace(area_num.group(2), str(round(int(area_num.group(2))*0.3025)) )
            area_m = area_m[:-2]+"평"
            return area_m
        except Exception as ex:
            self.logger.critical(f"get_area_num: {ex}")
            return '-/-평'

    def get_price_int(self, price_str):
        try:
            regex = re.compile(r'(\d+)[억]\s*([\d\,]+)*')
            r = regex.search(price_str)
            price_int = 0
            if r.group(1) is not None:
                price_int = price_int + int(r.group(1))
            if r.group(2) is not None:
                price_int = price_int + int(r.group(2).replace(',','')) / 10000
            return price_int

        except Exception as ex:
            self.logger.critical(f"get_price_int: {ex}")
            return 0


    def read_url_file(self) -> dict:
        try:
            read_full_path = os.getcwd() + self.url_list.replace('./','/')
            f = open(f"{read_full_path}", 'r')
            lines = f.readlines()
            urls_dict = {line.split('|', 1)[0]: line.split('|', 1)[1].strip() for line in lines}
            f.close()
            return urls_dict
        except Exception as ex:
            self.logger.critical(f"URL 파일 불러오기 실패 {ex}")
            return []

    def list_to_df(self, data) -> set:
        try:
            """ data 형태
            [
                {'land_title': '샛별우방', 
                'dong': '306동', 
                'price_type': '매매', 
                'price': '12억 5,000', 
                'info_area_type': '아파트', 
                'info_area_spec': '104/84m², 중/15층, 남동향', '
                info_area_spec2': ' 남동향확장올수리', 
                'confirm_date': '23.07.19.', 
                'raw_text': '샛별우방 306동매매12억 5,000아파트104/84m², 중/15층, 남동향확장올수리한국공인중개사협회 제공삼우공인중개사사무소등록일23.07.19.'},
                {},{}
                ...
            ]
            """
            df = pd.DataFrame.from_records(data)

            # col_dict ={'item_title': '샛별우방 306동',
            #     'price_type': '매매',
            #     'price': '12억 5,000',
            #     'info_area_type': '아파트',
            #     'info_area_spec': '104/84m², 중/15층, 남동향',
            #     'info_area_spec2': ' 남동향확장올수리',
            #     'confirm_date': '23.07.19.'}
            # col_dict = {
            #     'complex_title': '아파트명',
            #     'item_title': '아파트_동',
            #     'price_type': '거래타입',
            #     'price': '가격',
            #     'land_type': '건물타입',
            #     'area': '면적(m²)'
            #     'floor'
            #     'direction'
            #     'area_supply'
            #     'area_private'
            #     'info_area_spec2'
            #     'confirm_date'
            # }

            #Todo 요약본 df_brif 생성
            brif_df = df[['complex_title', 'area_p']].drop_duplicates(subset=['complex_title', 'area_p']).reset_index(drop=True)
            price_m_list = []
            price_j_list = []
            jeonse_rate = []
            jeonse_sub = []
            for idx, value in brif_df.iterrows():
                # print(f"{idx} : {value['complex_title']} | {value['area_p']}")
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
            file_path = os.path.join(os.getcwd() + self.data_dir.replace('./','/'))
            file_name = self.datetime_now+'.xlsx'
            file_pull_path = os.path.join(file_path, file_name)
            self.logger.info(f"Excel 저장 준비 {file_pull_path}")

            writer = pd.ExcelWriter(file_pull_path, engine="openpyxl")
            # df.to_excel(excel_writer=file_pull_path, sheet_name='전체 리스트',index=False, na_rep='', inf_rep='')
            df.to_excel(writer, sheet_name='전체 리스트', index=False)
            brif_df.to_excel(writer, sheet_name='요약', index=False)
            writer.close()
            #na_rep = '',  결측값을 ''으로 채우기
            #inf_rep = ''  무한값을 ''으로 채우기
            self.logger.info(f"Excel 저장 {file_pull_path}")
        except Exception as ex:
            self.logger.critical(f"Excel 저장 에러 {ex}")

    def main(self):
        self.logger.info("="*50)
        self.logger.info("start main")
        urls = self.read_url_file()
        ladnList = self.start_crawling(urls) #매개변수: url, return 값: list[dict{}]
        df, brif_df = self.list_to_df(ladnList)
        self.write_to_excel(df, brif_df)

if __name__ == '__main__':
    naverLand = landCrawling('./config/config.ini')
    naverLand.main()