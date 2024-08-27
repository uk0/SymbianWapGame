import os
import re
import shutil
from urllib.parse import urljoin, unquote

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 设置 Chrome
chrome_options = Options()
# chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)

BASE_URL = "http://java.52emu.cn/xq.php?id="


def sanitize_filename(filename):
    # 移除或替换不允许的字符
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # 替换冒号为下划线
    filename = filename.replace(':', '_')
    # 移除前导和尾随的空格和点
    filename = filename.strip('. ')
    # 如果文件名为空，使用默认名称
    if not filename:
        filename = "未命名游戏"
    return filename


def download_game_files(game_details, base_url, base_path):
    # 创建游戏文件夹，使用清理后的名称
    sanitized_title = sanitize_filename(game_details['title'])
    game_folder = os.path.join(base_path, sanitized_title)
    os.makedirs(game_folder, exist_ok=True)

    # 下载游戏文件
    if game_details['download_url'] != 'No download link':
        file_url = urljoin(base_url, game_details['download_url'])

        try:
            response = requests.get(file_url, stream=True, allow_redirects=True)
            response.raise_for_status()

            # 尝试从Content-Disposition头获取文件名
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                file_name = re.findall("filename=(.+)", content_disposition)[0].strip('"')
            else:
                # 如果没有Content-Disposition，使用URL的最后一部分
                file_name = unquote(os.path.basename(response.url))

            # 清理文件名
            file_name = sanitize_filename(file_name)

            # 如果文件名仍然无效，使用通用名称
            if not file_name or file_name == '.':
                file_name = 'game_file.jar'

            file_path = os.path.join(game_folder, file_name)

            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            print(f"Downloaded: {file_name}")
        except requests.RequestException as e:
            print(f"Error downloading file {file_url}: {str(e)}")

    # 下载截图
    for i, screenshot_url in enumerate(game_details['screenshots']):
        img_url = urljoin(base_url, screenshot_url)
        img_name = f"screenshot_{i + 1}.jpg"
        img_path = os.path.join(game_folder, img_name)

        try:
            response = requests.get(img_url, stream=True)
            response.raise_for_status()
            with open(img_path, 'wb') as img:
                shutil.copyfileobj(response.raw, img)
            print(f"Downloaded: {img_name}")
        except requests.RequestException as e:
            print(f"Error downloading image {img_url}: {str(e)}")

    print(f"All files for '{game_details['title']}' have been downloaded.")


def scrape_game_details(url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 提取游戏标题
        title = soup.find('h2').text.strip().split('[')[0] if soup.find('h2') else 'Unknown Title'

        # 提取游戏分类
        category = soup.find(text="【分类】：")
        category = category.next_element.strip() if category else 'Unknown Category'

        # 提取游戏简介
        intro = soup.find('h3', text="【游戏简介】")
        intro = intro.find_next(text=True).strip() if intro else 'No introduction available'

        # 提取下载地址（默认第一个）
        download_section = soup.find(text=lambda text: text and "【下载地址】" in text)
        download_url = 'No download link'
        if download_section:
            download_links = download_section.find_next_siblings('a')
            if download_links:
                download_url = download_links[0]['href']

        # 提取游戏截图
        screenshots = []
        img_tags = soup.find_all('img', alt=title)
        for img in img_tags:
            screenshots.append(img['src'])

        return {
            'id': url.split('=')[-1],
            'title': title,
            'category': category,
            'intro': intro,
            'download_url': download_url,
            'screenshots': screenshots
        }
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None


def crawl_website():
    for id in range(1, 20000):  # 从1到20000
        url = BASE_URL + str(id)
        print(f"Crawling: {url}")
        base_url = "http://java.52emu.cn/"
        base_path = "D:\\BaiduNetdiskDownload\\7723Games\\52emu"  # 替换为您想要保存游戏的基础路径

        game_details = scrape_game_details(url)
        if game_details:
            print(f"Game ID: {game_details['id']}")
            print(f"Title: {game_details['title']}")
            print(f"Category: {game_details['category']}")
            print(f"Intro: {game_details['intro']}...")  # 只打印简介的前100个字符
            print(f"Download URL: {game_details['download_url']}")
            print(f"Screenshots: {', '.join(game_details['screenshots'])}")
            print("---")

            # 下载游戏文件和截图
            download_game_files(game_details, base_url, base_path)
        time.sleep(1)

    driver.quit()


if __name__ == "__main__":
    crawl_website()