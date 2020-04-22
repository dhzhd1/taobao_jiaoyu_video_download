import re
from bs4 import BeautifulSoup
from seleniumwire import webdriver
import time
import os
import urllib.request
from datetime import datetime


DEBUG = True
URL_TB_EDU = 'https://jiaoyu.taobao.com'
URL_COURSE = ''
URL_DRAWING = 'https://v.daxue.taobao.com/detail.htm?courseId=81586'
URL_PREFIX = 'http://v.xue.taobao.com/'
VIDEO_DL_FOLDER = './Videos/'

# if not DEBUG:
#     option = Options()
#     option.add_argument('-headless')
#     driver = webdriver.Firefox(firefox_options=option)
# else:
#     driver = webdriver.Firefox()

driver = webdriver.Firefox()

driver.get(URL_TB_EDU)
print("Waiting 60s Manually login your account...")
time.sleep(60)
# Access the URL_COURSE
driver.get(URL_COURSE)
print("Waiting 10s...")
time.sleep(10)
page_source = driver.page_source
bs = BeautifulSoup(page_source)

# Get course list
outlines = bs.find(id='J_CourseListContent')

# print(course_outlines_section)

# Chapters data structure
# chapters = [{'chapter_name': 'chaptername', 'courses': [{'course_name': 'name', 'course_url': 'url-addr'}]}, {}, ...]
print("Get chapter information...")
chapters = []
for idx in range(69, 78):
    chapter_info = {}
    temp = outlines.find(attrs={'data-id': str(idx)})
    chapter_info['chapter_name'] = '_'.join(temp.find('span', 'chapter-num').text.replace('\n', '').strip().split())
    chapter_subs = outlines.find(attrs={'data-sub': str(idx)})
    lesson_list = chapter_subs.find_all('a', 'clearfix')
    lessons = []
    for lesson in lesson_list:
        course = {}
        course_chapter = lesson.find('div', 'course-chapter').text.strip()
        course_name = lesson.find('div', 'course-title').text.replace('\n', '').strip()
        course_url = URL_PREFIX + lesson['href']
        # http://v.xue.taobao.com/learn.htm?courseId=119819&chapterId=12858588&sectionId=13303029
        course['course_name'] = course_chapter + '_' + course_name
        course['course_url'] = course_url
        lessons.append(course)

    chapter_info['courses'] = lessons
    chapters.append(chapter_info)


for cpt in chapters:
    print("Chapter Name: " + cpt['chapter_name'])
    chapter_folder = os.path.join(VIDEO_DL_FOLDER, cpt['chapter_name'])
    if not os.path.exists(chapter_folder):
        os.mkdir(chapter_folder)
    for course in cpt['courses']:
        course_name = course['course_name']
        course_url = course['course_url']
        print('-- Course Name: ' + course_name)
        print('-- Course URL:  ' + course_url)
        target_full_path = os.path.join(chapter_folder, course_name + ".mp4")
        if os.path.exists(target_full_path):
            print("Target video [{}] existed under {}, ignore...".format(course_name, chapter_folder))
            continue
        # Clear webdriver requests cache
        del driver.requests
        driver.get(course_url)
        time.sleep(5)
        """
        M3U8 method (not finished)
        Below are the code for extract the m3u8 ts files. I was abandent this method since I was found there is a way to
        get the MP4 file directly.
        
        # m3u8_files = [url_path.path for url_path in driver.requests if ".m3u8" in url_path.path]
        # auth_key = m3u8_files[-1].split("auth_key=")[-1].strip()
        # m3u8_file_content = m3u8_files[-1].response.body.decode().split('\n')
        # ts_file_list = [f.replace('__hd-', '__ud-') for f in m3u8_file_content if f.endwith(".ts")]
        """

        # MP4 directly method
        while True:
            try:
                async_jsonp31_req = [req for req in driver.requests if "callback=jsonp31" in req.path]
                async_jsonp31_response = async_jsonp31_req[0].response.body
                break
            expcept Exception as e:
                driver.get(course_url)
                time.sleep(10)
                print("Keeping waiting async_jsonp31 data...")
                
        re_auth_key = r'authKey\":\"[^\"]+'
        re_mp4_hd = r'(https://cloud.video.taobao.com/play/./[0-9]+/./././7/./././hd/[0-9]+.mp4)'
        re_mp4_ud = r'(https://cloud.video.taobao.com/play/./[0-9]+/./././7/./././ud/[0-9]+.mp4)'

        # Get auth_key
        auth_key_matches = re.findall(re_auth_key, str(async_jsonp31_response))
        auth_key = auth_key_matches[0].split('"')[-1].strip()

        # Get mp4 directly link
        mp4_matches = re.findall(re_mp4_ud, str(async_jsonp31_response))
        if len(mp4_matches) < 1:
            print("Switch to HD video...")
            mp4_matches = re.findall(re_mp4_hd, str(async_jsonp31_response))
        mp4_url = mp4_matches[0].strip()

        download_url = mp4_url + "?auth_key=" + auth_key
        # Download mp4 file by urllib
        print("Downloading video {} to {}".format(course_name, chapter_folder))
        DONE = False
        while not DONE:
            retry_num = 0
            try:
                urllib.request.urlretrieve(download_url, target_full_path+".cache")
                os.rename(target_full_path+".cache", target_full_path)
                DONE = True
            except Exception as e:
                print(e)
                retry_num += 1
                print("Retry #{} times...".format(retry_num))

print("Sleeping 60 seconds...")
time.sleep(60)
driver.close()

