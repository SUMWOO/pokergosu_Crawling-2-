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
import time
import urllib.parse  # URL 인코딩을 위해 urllib.parse 모듈 추가

# ------------------- 환경변수에서 민감 정보 읽기 -------------------
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO')
EMAIL_SMTP = os.environ.get('EMAIL_SMTP', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))

# ------------------- 크롤링 설정 -------------------
BASE_SEARCH_URL = "https://www.pokergosu.com/free/search?s=1&v="
KEYWORDS = ['피망', 'WPL', 'gg포커', '투에이스', '더블에이']

# ------------------- 날짜 계산 (어제 날짜) -------------------
today = datetime.now()
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.strftime('%m-%d')

# ------------------- 게시글 크롤링 함수 -------------------
def crawl_posts():
    """
    각 키워드에 대한 검색 결과 페이지에서 어제 날짜 게시글을 추출
    """
    posts = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 키워드별로 검색 URL을 만들어 요청을 보냄
    for keyword in KEYWORDS:
        # 키워드 URL 인코딩
        encoded_keyword = urllib.parse.quote(keyword)
        search_url = f"{BASE_SEARCH_URL}{encoded_keyword}"
        
        print(f"'{keyword}' 키워드 검색 페이지 요청: {search_url}")
        
        try:
            resp = requests.get(search_url, headers=headers)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTPError: {e} - '{keyword}' 검색 결과를 가져올 수 없습니다. 다음 키워드로 넘어갑니다.")
            continue
            
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 게시판의 게시글 행(tr) 구조를 분석하여 각 게시글 추출
        for row in soup.select('table.board_list tbody tr'):
            cols = row.find_all('td')
            if len(cols) < 4:
                continue

            date_text = cols[3].get_text(strip=True)
            # 날짜가 어제 날짜인지 확인
            if date_text.endswith(yesterday_str):
                title_tag = cols[1].find('a')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag['href']
                if not link.startswith('http'):
                    link = "https://www.pokergosu.com" + link
                views = cols[-1].get_text(strip=True)
                
                posts.append({
                    'keyword': keyword,
                    'title': title,
                    'date': date_text,
                    'views': views,
                    'link': link
                })
        
        # 다음 키워드 검색 전에 2초 대기
        time.sleep(2)
        
    return posts

# ------------------- HTML 테이블 생성 -------------------
def make_email_html(posts, send_date):
    """
    posts: [{'keyword': str, 'title': str, 'date': str, 'views': str, 'link': str}, ...]
    send_date: 전송 기준 날짜(str)
    """
    # 키워드별 그룹핑
    grouped = {}
    for p in posts:
        grouped.setdefault(p['keyword'], []).append(p)

    html = f'''
    <div style="background:#22344b;color:white;padding:20px;font-size:22px;">
        <b>포커고수 키워드 알림</b><br>
        <span style="font-size:14px;color:#bce0ff;">전날({send_date})의 키워드 새 게시물 모음</span>
    </div>
    '''
    total = len(posts)
    html += f'<div style="padding:12px 0;">총 <b>{total}</b>개의 새로운 게시물이 발견되었습니다</div>'

    for keyword, plist in grouped.items():
        html += f'<hr style="border:1px solid #bce0ff;">'
        html += f'<h3 style="color:#1566d6;">🔍 키워드: {keyword} <span style="font-size:14px;color:#666;">({len(plist)}개)</span></h3>'
        for p in plist:
            html += f'''
            <div style="padding:7px 0 7px 10px;border-bottom:1px solid #ececec;">
                <b style="font-size:17px;">{p['title']}</b><br>
                <span style="color:#888;font-size:13px;">날짜: {p['date']} | 조회수: {p['views']}</span><br>
                <a href="{p['link']}" style="color:#0088ee;text-decoration:underline;" target="_blank">게시물 보기 →</a>
            </div>
            '''
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
    html_content = make_email_html(posts, yesterday.strftime('%Y-%m-%d'))

    # 3. 이메일 제목 생성 (예시: [포커고수 요약] 2025-07-31 키워드 게시글)
    subject = f"[포커고수 요약] {yesterday.strftime('%Y-%m-%d')} 키워드 게시글"

    # 4. 이메일 발송
    if posts:
        send_email(subject, html_content)
    else:
        print("어제 날짜의 키워드 게시물이 없습니다. 이메일을 발송하지 않습니다.")

if __name__ == '__main__':
    main()
