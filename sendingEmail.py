# -*- coding: utf-8 -*-
import os
import logging
import sys
import platform

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.encoders import encode_base64
from email.mime.base import MIMEBase

from configparser import ConfigParser
from logging.handlers import RotatingFileHandler


class sendingEmail():
    def __init__(self, conf_name):
        try:
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
                self.mail_id = config.get("MAIL", "MAIL_ID").replace('/','\\')
                self.mail_auth = config.get("MAIL", "MAIL_AUTH").replace('/','\\')
            else:
                self.set_logger(config.get("PATH", "LOG_PATH"))
                self.mail_id = config.get("MAIL", "MAIL_ID")
                self.mail_auth = config.get("MAIL", "MAIL_AUTH")

            self.mail_to = config.get("MAIL", "MAIL_TO").replace(' ', '')
            self.mail_from = config.get("MAIL", "MAIL_FROM")

        except Exception as ex:
            print(f'__init__ Error: {str(ex)}')

    def set_logger(self, log_path):
        self.logger = logging.getLogger("send_mail")
        self.logger.setLevel(logging.INFO)

        log_name = "send_email.log"
        formatter = logging.Formatter("[%(asctime)s][%(levelname)s] %(filename)s(%(lineno)d) %(message)s")
        # formatter = logging.Formatter("[%(asctime)s][%(levelname)s] (%(lineno)d) %(message)s")
        file_handler = RotatingFileHandler(os.path.join(log_path, log_name), maxBytes=5 * 1024 * 1024,
                                           backupCount=10, encoding='utf-8')
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def send_gmail(self, attached_file_name=None):
        #메일 세션 생성
        try:
            s = smtplib.SMTP('smtp.gmail.com', 587)  # 세션생성 gmail사용하기위한 변수, 지메일포트(587)
            s.starttls()  # TLS보안시작
            self.logger.info(f"메일서버 로그인 인증: {s.login(self.mail_id, self.mail_auth)}")  # 로그인 인증
        except Exception as ex:
            self.logger.critical(f"메일 로그인 실패")

        # 보낼 메시지 설정
        # 본문 메시지
        mail_text = f'<p><font size=2>네이버 부동산 크롤링 결과 <br><br>'

        pre = """<html>
                    <head>
                    <head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" >
                    <style>
                    .ft-default-1 { font-size: 24px; }
                    .ft-default-2 { font-size: 32px; }
                    .ft-smaller { font-size: smaller; }
                    .ft-larger { font-size: larger; }
                    table {
                        width : 90%;
                        text-align: center;
                        line-height: 1.5;
                        margin: 3px 3px;
                        border-collapse: collapse;
                        font-size: 11px;
                    }
                    table th {
                        width: 155px;
                        padding: 7px;
                        font-weight: bold;
                        text-align: center;
                        vertical-align: top;
                        color: #fff;
                        background: #2dbdb6 ;
                        font-size: 13px;
                    }
                    table td {
                        width: 155px;
                        vertical-align: top;
                        text-align: center;
                    }
                    tr:nth-child(2n){
                        background-color: #e7f4f1;
                    }
                    </style>
                    </head>"""

        sendHtml = f'{pre}<body><div>{mail_text}</div>'

        part2 = MIMEText(sendHtml, 'html')


        msg = MIMEMultipart('Test')
        msg['Subject'] = Header(s="[공유] 네이버 부동산 관심단지 매물 정보", charset='utf-8')
        msg['From'] = self.mail_from

        msg.attach(part2)

        # 첨부파일 추가
        if attached_file_name is not None:
            self.logger.info(f"attach file({attached_file_name}) load")
            attach_file = MIMEBase('application', "octet-stream")
            attach_file.set_payload(open(attached_file_name, "rb").read())

            encode_base64(attach_file)
            self.logger.info(f"attachment file: {os.path.basename(attached_file_name)}")
            attach_file.add_header('Content-Disposition',
                                   'attachment', filename=f'{os.path.basename(attached_file_name)}')
            msg.attach(attach_file)

        #실제 메일 전송
        recipients = self.mail_to.split(',')
        for recipient in recipients:
            try:
                s.sendmail(self.mail_id, recipient, msg.as_string())
                self.logger.info(f"메일 발송 완료(to: {recipient})")
            except Exception as ex:
                self.logger.critical(f"메일 발송 실패: {ex}")

    def main(self):
        self.logger.info("send email")
        self.send_gmail("./data/20230902161700.xlsx")

if __name__ == "__main__":
    send_email = sendingEmail('./config/config.ini')
    send_email.main()
