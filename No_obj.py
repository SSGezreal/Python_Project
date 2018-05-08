import json
import requests
from queue import Queue
from bs4 import BeautifulSoup as soup
from threading import Thread
import os
from time import sleep
headers = {
    'user-agent': 'Mozilla/5.0(compatible;MSIE9.0;WindowsNT6.1;Trident/5.0'}
process_line = 8
# 4线程
Log_file_name = 'Novel_log.txt'

# use data abstraction to initialize the concept novel,chapter
# log(both for individual novel and whole novels)
# get doc from biquke.com


def check_file_in_path(path, *files):
    """
    check if file in path given,create it if not
    """
    for file in files:
        if file not in os.listdir(path):
            fp = open(file, 'w')
            fp.close()


check_file_in_path('.', Log_file_name)


def load_log(filename):
    """
    load log from given filename
    """
    check_file_in_path('.', filename)
    try:
        fp = open(filename, encoding='utf-8')
        log = json.load(fp)
        fp.close()
    except Exception:
        print('读取文件失败，创建新日志..........')
        return {}
    else:
        print("读取日志成功...........")
        return log


Novel_log = load_log(Log_file_name)


def update_Novel_log():
    """
    update world Novel log:stores the novel names and source pages
    """
    write_log(Log_file_name, Novel_log)


def write_log(filename, log):
    """
    write log into given filename\n
    if failed,return original log
    """
    try:
        fp = open(filename, 'w', encoding='utf-8')
        json.dump(log, fp, ensure_ascii=False, indent=4)
        fp.close()
    except Exception:
        print('日志写入 %s 失败' % filename)
        return log
    else:
        print('日志写入成功')


def web_to_text(url):
    """
    return a soup object from a url
    """
    try:
        web = requests.get(url, headers=headers, timeout=5)
        web.encoding = 'utf-8'
    except requests.ConnectionError:
        print('Conenction failed,service no response')
        return
    else:
        return soup(web.text, 'lxml')


class worker(Thread):
    """
    a specific customized class  inherited from Thread to dowanload chapters
    member in input_queue is Chapter object\n
    member in container is Chapter.content\n
    worker function has already specified in class Chapter
    """

    def __init__(self, input_queue, output_container):
        Thread.__init__(self)
        self.input_queue = input_queue
        self.output_container = output_container

    def run(self):
        pass

# To establish a Novel object ,only need to provide the novel name
# and its source page doc(beautifoulsoup object,to save time)
# but we have already establish its profile including multi attributes
# these attributes can be viewd in the Novel's selectors
# all the src_page input will be stored in Novel_log.txt
# if src_page exist in Novel_log.txt,all need passed to Novel selector is its name


def Novel(name):
    """
    create a Novel object use data abstraction\n
    Novel constructor
    """
    global Novel_log
    if name in Novel_log:
        src_page = Novel_log[name]
    else:
        src_page = input('请输入小说页面(包括章节网址):').strip()
        Novel_log[name] = src_page
        update_Novel_log()
    html_doc = web_to_text(src_page)
    return [name, src_page, html_doc]


def novel_src_page(Novel):
    """
    return the source page of novel
    """
    return Novel[1]


def novel_name(Novel):
    """
    chapter name selector
    """
    return Novel[0]


def novel_html_doc(Novel):
    """
    novel html doc selector
    """
    return Novel[2]


def novel_log(Novel):
    """
    novel log constructor or read\n 
    The novel log is a dict,contains keys:
        [tutor,finished,name,loaded chapters number]
    """
    log = load_log(filename='%s_log.txt' % novel_name(Novel))
    if not log:
        doc = novel_html_doc(Novel)
        log['name'] = doc.h1.text
        log['finished'] = False
        log['tutor'] = doc.find('meta', property='og:novel:author')['content']
        log['loaded chapter number'] = 0
    return log
# only update the loaded chapters number and write it to file and after write chapters'content to file


def write_novel_log(log, Novel):
    """
    write log to file
    """
    write_log('%s_log.txt' % novel_name(Novel), log)


def update_novel_log(Novel, num):
    """
    update novel's log loaded chapters number and finished\n 
    write it to file\n
    the number is the number of chapters in a written process
    """
    log = novel_log(Novel)
    doc = novel_html_doc(Novel)
    log['loaded chapter number'] += num
    log['finished'] = False if doc.find('meta', property='og:novel:status')[
        'content'] == '连载中' else True
    write_novel_log(log=log, Novel=Novel)

# the right order of update a novel's log is:
# First: read the novel's log via function-novel_log
# Second: update novel log via function-update_novel_log(including the write action)


def check_novel_file(Novel):
    """
    check the file and log file of the novel
    """
    name = novel_name(Novel)
    check_file_in_path('.', '%s.txt' % name, '%s_log.txt' % name)


def novel_chapters(Novel):
    """
    return chapters queue
    """
    doc = novel_html_doc(Novel)
    owned_length = novel_log(Novel)['loaded chapter number']
    original_url = doc.find('meta', property='og:novel:read_url')['content']
    chapters_links = [original_url + tag['href']
                      for tag in doc.find(id='list').find_all('a')][owned_length:]
    return chapters_links


def novel_update(Novel):
    """
    update novel
    """

    def chapter_to_doc(link_queue, doc_container):
        """
        chapters:a chapter article generator\n
        doc_container: the container which store the index and article of a chapter
        """
        while True:
            sleep(0.1)
            if link_queue.empty():
                break
            try:
                index, link = link_queue.get()
                chapter = Chapter(link)
                title = chapter_title(chapter)
                article = chapter_article(chapter)
                doc_container.append((index, title, article))
                print(title, '已经载入')
            except Exception:
                continue
    chapters_links = novel_chapters(Novel)
    # load links of chapters to update
    chapters = Queue()
    for index, link in enumerate(chapters_links):
        chapters.put((index, link))
    # initialize chapters queue to update
    check_novel_file(Novel)
    # check file and log file for the Novel
    update_number = 0
    # record the number of chapter in this update process
    doc_container = []
    # create the doc container list
    thread_pool = [Thread(target=chapter_to_doc, args=(
        chapters, doc_container)) for _ in range(process_line)]
    # load multi process to load chapter article
    for line in thread_pool:
        line.start()
    # start all the thread
    for line in thread_pool:
        line.join()
    # wait until all the chapters end to continue write process
    novel_file = open('%s.txt' % novel_name(Novel), 'a', encoding='utf-8')
    # open the novel's file,wait to write in in additive mode
    for index, title, article in sorted(doc_container, key=lambda x: x[0]):
        novel_file.write(article)
        print(title, '已经写入文件')
        update_number += 1
    # write the docs to novel's txt file
    novel_file.close()
    # close the novel file handle
    sleep(0.1)
    update_novel_log(Novel, update_number)
    # update novel's log after a update
    print('%s 更新完成' % novel_name(Novel))

# Chapter constructor and its attributes' selector
# to establish a chapter
# also provided its html doc(beautisoup object and the Novel it belongs to)


def Chapter(src_page):
    """
    to establish a Chapter,all to provide are src_page and the novel it belongs to\n
    Chapter constructor
    """
    html_doc = web_to_text(src_page)
    return [src_page, html_doc]


def chapter_src_page(Chapter):
    """
    return the src_page of chapter's source page
    """
    return Chapter[0]


def chapter_html_doc(Chapter):
    """
    chapter html_doc selector
    """
    return Chapter[1]


def chapter_title(Chapter):
    """
    chapter title selector
    """
    html_doc = chapter_html_doc(Chapter)
    return html_doc.h1.text


def chapter_content(Chapter):
    """
    chapter content selector
    """
    return chapter_html_doc(Chapter).find('div', id='content').text.replace('\xa0', '\n')


def chapter_article(Chapter):
    """
    chapter article selector
    """
    return ''.join([chapter_title(Chapter), '\n\n', chapter_content(Chapter)])


def chapter_write(Chapter, fp):
    fp.write(chapter_article(Chapter))


def update_all_novel():
    """
    update all Novels
    """
    novels = Novel_log.keys()
    for novel in novels:
        item = Novel(novel)
        novel_update(item)
    print('所有小说已经更新完毕')
    print('本次更新小说数：%d'%len(novels))