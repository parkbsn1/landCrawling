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
from numpy import inf
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
            while(try_cnt < 5):
                land_info = self.get_land_info(driver, landName, url) #크롤링
                if land_info != -1:
                    landResult.extend(land_info)
                    break
                # elif(land_info == -2):
                #     break
                else:
                    try_cnt = try_cnt + 1
                    #driver.refresh()
                    self.logger.info(f"{landName} {try_cnt}회 실패")
        driver.quit()
        self.logger.info(f"총 {len(landResult)}건 파싱 완료")
        return landResult

    def click_rollback_info(self, crawledItems, click_idx):
        try:
            compile_str = re.compile('(중개사([\d]+)곳)')
            junggae = compile_str.search(crawledItems[click_idx].text)

            if (junggae):
                # self.logger.info(f"동일 매물 {junggae.group(2)}개")
                crawledItems[click_idx].click()
            return 1
        except Exception as ex:
            self.logger.critical(f"rollback click error: {ex}")
            return 0

    def click_land_info(self, crawledItems, click_idx):
        try:
            time.sleep(self.time_sleep_int2)
            add_idx = 0
            compile_str = re.compile('(중개사([\d]+)곳)')
            junggae = compile_str.search(crawledItems[click_idx].text)
            # self.logger.info(f"land info: {crawledItems[click_idx].text}")

            if (junggae): #동일-대표 매물
                self.logger.info(f"동일 매물 {junggae.group(2)}개")
                crawledItems[click_idx].click()
                add_idx = int(junggae.group(2))
                time.sleep(self.time_sleep_int1)
            elif "네이버에서 보기" in crawledItems[click_idx].text: #단일/동일-상세 매물 타플랫폼인경우
                view_naver = crawledItems[click_idx].find_element(By.LINK_TEXT, '네이버에서 보기')
                view_naver.click()
            else: #단일/동일-상세 매물인 경우
                # crawledItems[click_idx].click()
                crawledItems[click_idx].find_element(By.CLASS_NAME, "item_link").click()
            # if (click_idx+1) % 20 == 0 and click_idx != 0:
            #     time.sleep(self.time_sleep_int2 * 2)
            return add_idx
        except Exception as ex:
            self.logger.critical(f"click error: {ex}")
            return -1

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
            # time.sleep(3)
            for index, landTitle in enumerate(tmp):
                # self.logger.info(f"{landTitle.find('div', 'complex_title').text}")
                if landTitle.find('div', 'complex_title').text != complex_title:
                    continue
                for index2, landType in enumerate(landTitle.findAll('button', 'article_link')):
                    if landType.find('span', 'type').text in ['매매','전세','월세']:
                        self.logger.info(f"{complex_title}: {landType.find('span', 'type').text} {int(landType.find('span', 'count').text)}")
                        land_count[landType.find('span', 'type').text] = int(landType.find('span', 'count').text)

            if len(land_count) == 0:
                self.logger.info(f"매물 0건 : 파싱 에러")
                return -1
            self.logger.info(f"매물 개수: {land_count}")

            # time.sleep(self.time_sleep_int2)
            #매물정보가 없는 경우
            if len(crawledItems) == 0:
                self.logger.info(f"{complex_title} 매물 정보 없음")
                return -1

            #매물이 소수(5개 이하)인 경우
            # elif len(crawledItems) < 5:
            #     html = driver.page_source
            #     soup = bs(html, 'html.parser')
            #     self.logger.info(f"{1}: 수집({len(crawledItems)}) | {round((len(crawledItems) / len(crawledItems)) * 100)}% )")

            # 매물이 다수인 경우
            else:
                # time.sleep(3)
                maxLen = len(crawledItems)
                # time_value = 5
                totalLandCount = sum([v for v in land_count.values()])
                res = []
                click_idx = 0
                ad_dict = {'raw': 0, 'cnt':0} #raw 동일매물 초기값, cnt 클릭시 감소
                except_cnt = 0
                while(click_idx < totalLandCount):
                    try:
                        tmp_dict = {}
                        self.logger.info(f"click_idx: {click_idx} | ad_dict: {ad_dict} | totalLandCount: {totalLandCount}")
                        crawledItems = driver.find_elements(By.CLASS_NAME, "item_inner")
                        if len(crawledItems) < click_idx:
                            click_idx = click_idx - 1 #finally에서 증가하는 부분 상쇄
                            continue
                        if (crawledItems[click_idx].text == ''):
                            totalLandCount = totalLandCount + 1
                            continue #''이면 continue
                        if crawledItems[click_idx].text == '매물을 불러오는 중입니다.':
                            continue
                        try:
                            if crawledItems[click_idx].find_element(By.CLASS_NAME, "item_agent_title").text == '공인중개사협회매물':
                                break #공인중개사협회 매물은 패스
                        except:
                            pass
                        #Todo: root/copy/tmp 판단 기준 변경
                        #root: 중개사N건 / copy: div class='info_area' -> span class='spec' [0] 없는 경우(평/층/방향) / tmp
                        click_result = self.click_land_info(crawledItems, click_idx)
                        if (click_result != -1): # -1: 에러 / 0: 단일 또는 동일-상세 매물 / 1이상: 동일-대표 매물
                            if (ad_dict['cnt'] == 0 and click_result > 0):
                                ad_dict['cnt'] = click_result
                                ad_dict['raw'] = click_result
                            #동일-대표 / 동일-상세 / 단독 매물 판단
                            if click_result > 0 and ad_dict['raw'] > 0: #동일-대표: click_result > 0 ADN ad_dict['raw'] 또는 ad_dict['cnt'] == 0
                                item_type = 'root_dict'
                            elif click_result == 0 and ad_dict['raw'] > 0: #동일-상세: click_result == 0 AND ad_dict['raw'] 또는 ad_dict['cnt'] > 0
                                item_type = 'copy_dict'
                            elif click_result == 0 and ad_dict['raw'] == 0: #단독매물: click_result == 0 AND ad_dict['raw'] 또는 ad_dict['cnt'] == 0
                                item_type = 'tmp_dict'
                            else:
                                self.logger.critical(f"No item_type")
                                item_type = 'tmp'

                            #root dict 생성
                            if (item_type == 'root_dict'):#(click_result > 0):
                                root_dict = self.make_info_dict(crawledItems[click_idx], item_type, landName, item_type) #root_dict

                            # elif(click_result == 0):
                            else:
                                # if (ad_dict['cnt'] > 0): #root dict 적용 필요
                                if (item_type == 'copy_dict'):  # root dict 적용 필요
                                    #동일-상세 매물로 크롤링
                                    ad_dict['cnt'] = ad_dict['cnt'] - 1
                                    tmp_dict = root_dict.copy()
                                    landId = (driver.current_url.split('=')[-1])
                                    tmp_dict.update(self.make_info_dict(crawledItems[click_idx], landId, landName, 'copy_dict'))
                                    tmp_dict["duplicate"] = root_dict["item_title"] + "|" + root_dict["floor"].strip() + "|" + root_dict["area_p"]
                                else:
                                    #단일 매물로 크롤링
                                    landId = (driver.current_url.split('=')[-1])
                                    tmp_dict = self.make_info_dict(crawledItems[click_idx], landId, landName, 'tmp_dict')

                                if 'confirm_date' not in tmp_dict.keys(): #confirm_date 값이 없는 경우
                                    except_cnt = except_cnt + 1
                                    continue
                                elif tmp_dict['confirm_date'] < self.confirm_limit_day:
                                    except_cnt = except_cnt + 1
                                    continue
                                else:
                                    res.append(tmp_dict)
                            totalLandCount = totalLandCount + click_result
                    except Exception as ex:
                        self.logger.critical(f"{complex_title} 파싱 실패: {crawledItems[click_idx].text}")
                        self.logger.critical(f"{ex} click error")
                        if ad_dict['cnt'] > 0:
                            ad_dict['cnt'] = ad_dict['cnt'] - 1
                    finally:
                        if (click_idx+1) % 10 == 0 or (click_idx+1) == totalLandCount:
                            self.logger.info(f"[{complex_title}] landId crawling {click_idx}({click_idx + 1} / {totalLandCount})")
                            time.sleep(self.time_sleep_int2)
                        if ad_dict['cnt'] == 0:
                            self.logger.info(f"-" * 60)
                            if ad_dict['raw'] > 0:
                                #동일매물 재클릭
                                rollback_res = self.click_rollback_info(crawledItems, click_idx - (ad_dict['raw'] + 1))
                                if rollback_res == 1: #click_idx/ totalLandCount 초기화
                                    # click_idx = click_idx - (ad_dict['raw'] + 1)
                                    # totalLandCount = totalLandCount - (ad_dict['raw'] + 1)
                                    ad_dict['raw'] = 0
                        click_idx = click_idx + 1
            self.logger.info(f"{complex_title}: {len(res)}건 (*{self.confirm_limit_day}이전: {except_cnt}건 )")
            return res
        except Exception as ex:
            self.logger.critical(f"get_land_info Error")
            self.logger.critical(f"{ex}")
            return -2

    def make_info_dict(self, crawledItem, landID, landName, dict_type):
        try:
            #공통
            tmp_dict = {}
            tmp_dict["duplicate"] = "-"
            tmp_dict["landID"] = landID  # 매물번호
            tmp_dict["complex_title"] = landName  # complex_title

            try:
                tmp_dict["confirm_date"] = crawledItem.find_element(By.CLASS_NAME, 'label_area').find_element(
                    By.CLASS_NAME, 'data').text  # 23.07.13.
            except Exception as ex:
                tmp_dict["confirm_date"] = 0
                self.print_logger_error(ex, "confirm_date", crawledItem.text, landID, landName, dict_type)

            if dict_type in ['root_dict', 'tmp_dict']: #동일매물-대표, 단독매물 공통
                try:
                    tmp_dict["item_title"] = crawledItem.find_element(By.CLASS_NAME,'item_title').find_element(By.CLASS_NAME,'text').text  # 샛별삼부 408동
                except Exception as ex:
                    self.print_logger_error(ex, "item_title", crawledItem.text, landID, landName, dict_type)

                try:
                    tmp_dict["price_type"] = crawledItem.find_element(By.CLASS_NAME, 'price_line').find_element(By.CLASS_NAME, 'type').text  # 전세
                except Exception as ex:
                    self.print_logger_error(ex, "price_type", crawledItem.text, landID, landName, dict_type)
                if tmp_dict["price_type"] in ['매매', '전세']:  # 매매, 전세
                    tmp_dict["price"] = crawledItem.find_element(By.CLASS_NAME, 'price_line').find_element(By.CLASS_NAME, 'price').text  # 7억 5,000
                    tmp_dict["price_int"] = self.get_price_int(tmp_dict["price"], tmp_dict["price_type"])
                else:  # 월세
                    tmp_dict["price"] = crawledItem.find_element(By.CLASS_NAME, 'price_line').find_element(By.CLASS_NAME, 'price').text  # 7억 5,000
                    tmp_dict["price_int"] = self.get_price_int(tmp_dict["price"].split('/')[0])

                try:
                    tmp_dict["land_type"] = crawledItem.find_element(By.CLASS_NAME,'info_area').find_element(By.CLASS_NAME,'type').text  # 아파트
                except Exception as ex:
                    self.print_logger_error(ex, "land_type", crawledItem.text, landID, landName, dict_type)

                try:
                    tmp_dict["area_m"], tmp_dict["floor"], tmp_dict["direction"] = crawledItem.find_element(
                        By.CLASS_NAME, 'info_area').find_element(By.CLASS_NAME, 'spec').text.replace('\n', '').split(
                        ',')  # 158/128m², 15/25층, 남동향
                except Exception as ex:
                    self.print_logger_error(ex, "area_m|floor|direction", crawledItem.text, landID, landName, dict_type)
                try:
                    tmp_dict["area_p"] = self.get_area_num(tmp_dict["area_m"])
                except Exception as ex:
                    self.print_logger_error(ex, "area_p", crawledItem.text, landID, landName, dict_type)

            if dict_type == 'root_dict':  # 동일매물-대표
                try:
                    tmp_dict["info_area_spec2"] = crawledItem.find_element(By.CLASS_NAME,'tag_area').text # 25년이상 올수리 1층 방세개 (tag정보)
                except Exception as ex:
                    self.print_logger_error(ex, "info_area_spec2", crawledItem.text, landID, landName, dict_type)
                    tmp_dict["info_area_spec2"] = '-'

            if dict_type == 'tmp_dict':  # 단독매물
                try:
                    tmp_dict["info_area_spec1"] = crawledItem.find_element(By.CLASS_NAME, 'info_area').find_elements(By.CLASS_NAME, 'spec')[1].text #22입주특급정보바로확인클릭올수리확장샷시
                except IndexError:
                    self.logger.info(f"No info_area_spec1: {crawledItem.text}")
                    tmp_dict["info_area_spec1"] = '-'
                except Exception as ex:
                    self.print_logger_error(ex, "info_area_spec1", crawledItem.text, landID, landName, dict_type)
                    tmp_dict["info_area_spec1"] = '-'

            if dict_type == 'copy_dict': #동일-상세
                try:
                    tmp_dict["price_type"] = crawledItem.find_element(By.CLASS_NAME, 'item_title').find_element(By.CLASS_NAME, 'type').text  # 전세
                except Exception as ex:
                    self.print_logger_error(ex, "price_type", crawledItem.text, landID, landName, dict_type)
                if tmp_dict["price_type"] in ['매매', '전세']:  # 매매, 전세
                    tmp_dict["price"] = crawledItem.find_element(By.CLASS_NAME, 'item_title').find_element(By.CLASS_NAME, 'price').text  # 7억 5,000
                    tmp_dict["price_int"] = self.get_price_int(tmp_dict["price"], tmp_dict["price_type"])
                else:  # 월세
                    tmp_dict["price"] = crawledItem.find_element(By.CLASS_NAME, 'item_title').find_element(By.CLASS_NAME, 'price').text  # 7억 5,000
                    tmp_dict["price_int"] = self.get_price_int(tmp_dict["price"].split('/')[0])
                try:
                    tmp_dict["info_area_spec1"] = crawledItem.find_element(By.CLASS_NAME, 'info_area').find_element(By.CLASS_NAME, 'spec').text #22입주특급정보바로확인클릭올수리확장샷시
                except IndexError:
                    self.logger.info(f"No info_area_spec1: {crawledItem.text}")
                    tmp_dict["info_area_spec1"] = '-'
                except Exception as ex:
                    self.print_logger_error('-', "info_area_spec1", crawledItem.text, landID, landName, dict_type)
                    tmp_dict["info_area_spec1"] = '-'
            #self.logger.info(f"[TEST-{landName} {dict_type} {landID}]: {tmp_dict}")
            raw_str = (str(crawledItem.text)).replace('\n',' ')
            self.logger.info(f"[{dict_type}-{landID}]: {raw_str}")
        except Exception as ex:
            self.logger.critical(f"make info dict:{ex} | {tmp_dict}")
        finally:
            return tmp_dict

    def print_logger_error(self, ex, column, item_text, landID, landName, dict_type):
        self.logger.critical(f"[{landName}|{landID}|{dict_type}]{column}:{ex} | {item_text}")



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
            df = df.drop_duplicates(subset=['complex_title','item_title','price_type','price','area_m','floor','direction','landID'])
            brif_df = df[['complex_title', 'area_p']].drop_duplicates(subset=['complex_title', 'area_p']).reset_index(drop=True)
            agg_dict = {'최대':'max', '최소':'min', '평균':'mean', '중간값': 'median', '개수':'count'}

            for v in agg_dict.keys():
                brif_df['매매_'+v] = 0
                brif_df['전세_' + v] = 0

            price_m_list = []
            price_j_list = []
            jeonse_rate = []
            jeonse_sub = []

            agg_df = df.groupby(['complex_title','area_p','price_type'])['price_int'].agg(list(agg_dict.values()))

            for idx, value in brif_df.iterrows():
                df_idx = brif_df[(brif_df['complex_title'] == value['complex_title']) & (
                            brif_df['area_p'] == value['area_p'])].index[0]
                try:
                    agg_j = agg_df.loc[(value['complex_title'], value['area_p'], '전세')]
                    for k, v in agg_dict.items():
                        brif_df.loc[df_idx, '전세_' + k] = agg_j[v] if k!='평균' else round(agg_j[v],2)
                except:
                    for k, v in agg_dict.items():
                        brif_df.loc[df_idx, '전세_' + k] = 0

                try:
                    agg_m = agg_df.loc[(value['complex_title'], value['area_p'], '매매')]
                    for k, v in agg_dict.items():
                        brif_df.loc[df_idx, '매매_' + k] = agg_m[v] if k!='평균' else round(agg_m[v],2)
                except:
                    for k, v in agg_dict.items():
                        brif_df.loc[df_idx, '매매_' + k] = 0

            # brif_df['price_m'] = price_m_list
            # brif_df['price_j'] = price_j_list
            # brif_df['jeonse_sub'] = jeonse_sub
            # brif_df['jeonse_rate'] = jeonse_rate

            #신규 전세가율 추가
            brif_df['전세가율'] = (round(brif_df['전세_최대'] / brif_df['매매_최소'],2)*100).fillna(0)
            brif_df['전세가율(평균)'] = (round(brif_df['전세_평균'] / brif_df['매매_평균'],2)*100).fillna(0)
            brif_df['전세가율(중간값)'] = (round(brif_df['전세_중간값'] / brif_df['매매_중간값'],2)*100).fillna(0)

            #갭차이
            brif_df['갭차이'] = 0
            brif_df['갭차이(평균)'] = 0
            brif_df['갭차이(중간값)'] = 0
            for idx, value in brif_df.iterrows():
                if value['매매_최대'] != 0:
                    brif_df.loc[idx, '갭차이'] = value['매매_최소'] - value['전세_최대']
                    brif_df.loc[idx, '갭차이(평균)'] = value['매매_평균'] - value['전세_평균']
                    brif_df.loc[idx, '갭차이(중간값)'] = value['매매_중간값'] - value['전세_중간값']
            brif_df.replace([inf, -inf], 0, inplace=True)

            # 정렬
            brif_df = brif_df.sort_values(['complex_title', 'area_p'], ascending=False)
            brif_df.rename(columns=self.get_rename_col_dict(), inplace=True)
            # brif_df = brif_df[['아파트명','면적(평)','매매가_최소(억원)','전세가_최대(억원)','갭차이(억원)','전세가율(%)','매매_최대','매매_최소','매매_평균','매매_중간값','매매_개수','전세_최대','전세_최소','전세_평균','전세_중간값','전세_개수','전세가율(평균값)','전세가율(중간값)']]
            brif_df = brif_df[
                ['아파트명', '면적(평)', '매매_최대', '매매_최소', '매매_평균', '매매_중간값',
                 '매매_개수', '전세_최대', '전세_최소', '전세_평균', '전세_중간값', '전세_개수', '전세가율(평균)', '전세가율(중간값)','갭차이', '전세가율', '갭차이(평균)']]
            brif_info_df = brif_df[['아파트명','면적(평)','매매_최소','전세_최대','갭차이','전세가율','매매_평균','전세_평균','갭차이(평균)','전세가율(평균)']]
            brif_beta_df = brif_df[['아파트명','면적(평)','갭차이','전세가율','전세가율(평균)','전세가율(중간값)','매매_최대','매매_최소','매매_평균','매매_중간값','매매_개수','전세_최대','전세_최소','전세_평균','전세_중간값','전세_개수']]
            df.rename(columns=self.get_rename_col_dict(), inplace=True)
            return (df, brif_info_df, brif_beta_df)
        except Exception as ex:
            self.logger.critical(f"Excel 저장 에러 {ex}")

    def get_rename_col_dict(self)->dict:
        rename_col_dict = {
            'duplicate': '동일매물',
            'landID': '매물번호',
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

    def write_to_excel(self, df, brif_df, brif_beta_df):
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
            brif_beta_df.to_excel(writer, sheet_name='상세', index=False)
            writer.close()
            self.logger.info(f"Excel 저장 {file_full_path}")
            return file_full_path
        except Exception as ex:
            self.logger.critical(f"Excel 저장 에러 {ex}")
            return None

    def main(self):
        self.logger.info("="*50)
        self.print_config_info() #설정값 출력
        urls = self.read_url_file() #크롤링할 url 리스트 불러오기
        ladnList = self.start_crawling(urls) #매개변수: url, return 값: list[dict{}]
        df, brif_df, brif_beta_df = self.list_to_df(ladnList)
        # self.write_to_excel(df, brif_df)
        excel_file = self.write_to_excel(df, brif_df, brif_beta_df)
        if self.mail_send_flag == 'Y' or self.mail_send_flag == 'y':
            sendEmail = sendingEmail.sendingEmail('./config/config.ini')
            sendEmail.send_gmail(excel_file)

if __name__ == '__main__':
    naverLand = landCrawling('./config/config.ini')
    naverLand.main()
