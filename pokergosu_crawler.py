# -*- coding: utf-8 -*-
"""
포커고수 자유게시판에서 특정 키워드가 포함된 전날 게시글을 크롤링하고,
게시글 정보를 이메일로 요약 발송하는 자동화 파이썬 스크립트.

- 이메일 발신자, 수신자, 비밀번호 등 모든 민감 정보는 환경변수로만 불러옵니다.
- GitHub Actions 등 환경변수 기반 자동화 환경에서 안전하게 동작합니다.
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ------------------- 환경변수에서 민감 정보 읽기 -------------------
EMAIL_USER = os.environ.get('EMAIL_USER')         # 발신자 이메일 주소
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD') # 발신자 이메일 비밀번호/앱 비밀번호
EMAIL_TO = os.environ.get('EMAIL_TO')             # 수신자 이메일 주소 (여러 명이면 콤마로 구분)
EMAIL_SMTP = os.environ.get('EMAIL_SMTP', 'smtp.gmail.com')  # SMTP 서버 (기본: gmail)
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))           # SMTP 포트 (기본: 587)

# ------------------- 크롤링 설정 -------------------
BASE_URL = "https://www.pokergosu.com/free"
KEYWORDS = ['피망', 'WPL', 'gg포커', '투에이스', '더블에이']

# ------------------- 날짜 계산 (어제 날짜) -------------------
today = datetime.now()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.strftime('%Y-%m-%d')  # 게시판 날짜 포맷에 맞게 조정 필요

# ------------------- 게시글 크롤링 함수 -------------------
def crawl_posts():
    """
    자유게시판에서 어제 날짜의 특정 키워드 포함 게시글을 추출
    """
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    posts = []
    # 게시판의 게시글 행(tr) 구조를 분석하여 각 게시글 추출
    for row in soup.select('table.board_list tbody tr'):
        cols = row.find_all('td')
        if len(cols) < 4:
            continue  # 광고 등 비정상 행 제외

        # 날짜, 제목, 조회수, 링크 추출 (포커고수 게시판 구조에 맞게 조정)
        date_text = cols[3].get_text(strip=True)
        # 날짜 포맷이 'YYYY-MM-DD' 또는 'MM-DD' 형태일 수 있음
        if '-' in date_text and len(date_text) >= 5:
            # 어제 날짜만 추출
            if not date_text.endswith(yesterday.strftime('%m-%d')):
                continue
        else:
            continue

        title_tag = cols[1].find('a')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag['href']
        if not link.startswith('http'):
            link = "https://www.pokergosu.com" + link
        views = cols[-1].get_text(strip=True)

        # 키워드 필터
        if any(keyword in title for keyword in KEYWORDS):
            posts.append({
                'title': title,
                'date': date_text,
                'views': views,
                'link': link
            })
    return posts

# ------------------- HTML 테이블 생성 -------------------
def make_html_table(posts):
    """
    게시글 리스트를 HTML 테이블로 변환
    """
    if not posts:
        return "<p>어제는 키워드가 포함된 게시글이 없습니다.</p>"
    html = '<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;">'
    html += '<tr><th>제목</th><th>날짜</th><th>조회수</th><th>링크</th></tr>'
    for post in posts:
        html += f'<tr>' \
                f'<td>{post["title"]}</td>' \
                f'<td>{post["date"]}</td>' \
                f'<td>{post["views"]}</td>' \
                f'<td><a href="{post["link"]}">바로가기</a></td>' \
                f'</tr>'
    html += '</table>'
    return html

# ------------------- 이메일 발송 함수 -------------------
def send_email(subject, html_content):
    """
    환경변수 기반 이메일 발송
    """
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))

    # SMTP 서버 연결 및 메일 발송
    with smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_TO.split(','), msg.as_string())

# ------------------- 메인 실행 -------------------
def main():
    # 1. 게시글 크롤링
    posts = crawl_posts()

    # 2. HTML 요약 생성
    html_content = make_html_table(posts)

    # 3. 이메일 제목 생성 (예시: [포커고수 요약] 2025-07-31 키워드 게시글)
    subject = f"[포커고수 요약] {yesterday.strftime('%Y-%m-%d')} 키워드 게시글"

    # 4. 이메일 발송
    send_email(subject, html_content)

if __name__ == '__main__':
    main()
