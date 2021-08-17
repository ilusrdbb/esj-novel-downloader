#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""

esj zone爬虫，获取全部日轻，包含插图
author by chaocai 
	
"""

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import requests, sys, os, re, socket, uuid
 
class downloader():
	
    def __init__(self):
        #列表页地址前缀
        self.list_url = 'https://www.esjzone.cc/list-11/'
        #书籍页地址前缀
        self.book_url = 'https://www.esjzone.cc'
        #章节页地址前缀（esj中不需要，预留）
        self.content_url = ''
        #列表开始页码，从1开始
        self.list_start_page = 1
        #列表结束页码，需要加1
        self.list_end_page = 40
        #设置请求延迟，防止被封ip（esj中不需要，预留）
        self.delay = 0
        #设置请求默认重试次数
        self.http_retry = 2
        #设置请求超时时间
        self.http_timeout = 15
        #通用报错标识
        self.error_flag = 'error'
		#代理开关 0关1开
		self.proxy_switch = 0
        
    def main(self):
        """ 
		
		主函数 
		
        """
		#全局禁用https安全请求警告
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        #全局socket超时，防止卡死，并推荐阿里dns
        socket.setdefaulttimeout(20)
        for i in range(self.list_start_page, self.list_end_page):
			#遍历列表页
            print('开始获取列表，第' + str(i) + '页')
            try:
                list_html = self.get_request_html(self.list_url + str(i) + '.html')
            except Exception as e:
                print('请求列表出错：' + str(e))
                continue
            else:
                book_div_list = self.get_div_list(list_html, 'list')
                if book_div_list == self.error_flag:
                    continue
                else:
                    for book in book_div_list:
                        book_tag = self.get_book_div(book)
                        book_name = str(book_tag['title'])
                        book_url = self.book_url + str(book_tag.a['href'])
                        self.get_chapter_list(book_name, book_url)
                        #最后下载封面图片
                        book_pic = str(book_tag.find_all('div', class_='lazyload')[0].get('data-src'))
                        self.download_img(book_name + '/书籍封面.jpg', book_pic)
						
					   
    def get_request_html(self, url):
        """
		
		通用请求方法
		参数：url 请求地址
		返回：html 响应页面html
			
        """
		#构造请求头
        headers = {
			"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
        }
		#设置翻墙的代理，v2ray为socks5端口+1
        proxies = {'http':'http://127.0.0.1:1081','https':'http://127.0.0.1:1081'}
        session = requests.Session()
        session.mount('http://', HTTPAdapter(max_retries=self.http_retry))
        session.mount('https://', HTTPAdapter(max_retries=self.http_retry))
		if self.proxy_switch == 0:
		    request = session.get(url, verify=False, headers=headers, timeout=self.http_timeout)
		else:
            request = session.get(url, verify=False, headers=headers, proxies=proxies, timeout=self.http_timeout)
        html = request.text
        return html
	
    def get_div_list(self, html, type):
        """

        通用获取列表div list方法
        参数：html
              type 类型 'list' 列表中书籍div的list 'book' 书籍中章节div的list
        返回：div_list 列表tag
              
        """
        try:
            bf = BeautifulSoup(html)
            if type == 'list':
                div_list = bf.section.div.find_all('div',class_ = 'col-lg-3')        
            else:
                div_list = bf.find_all('div',id = 'chapterList')[0].find_all('a',target = '_blank')
            return div_list
        except Exception as e:
            print('获取' + type + '_div_list出错：' + str(e))
            return self.error_flag
			
    def get_book_div(self, tag):
        """
        
        进一步解析书籍div
        参数：tag 列表tag
        返回：book_div 书籍tag 
              
        """
        try:
            book_div = tag.find_all('div',class_ = 'card mb-30')[0]
            return book_div
        except Exception as e:
            print('获取列表书籍tag出错：' + str(e))
            return self.error_flag
			
		
    def get_book_introduce(self, name, html):
        """
        
        解析书籍介绍
        参数：html 书籍html 
              name 书籍名称
              
        """
        try:
            bf = BeautifulSoup(html)
            #包含html格式，防止漏掉关键链接
            div = bf.find_all('div',class_ = 'description')[0]
            self.write(name + '/书籍简介.txt', str(div))
        except Exception as e:
            print('获取书籍介绍出错：' + str(e))
			
    def get_chapter_list(self, name, url):
        """
        
        解析书籍章节列表
        参数：name 书名 
              url 书籍地址
              
        """
        print('开始获取书籍：' + name + '||||地址：' + url)
        self.mkdir(name)
        try:
            book_html = self.get_request_html(url)
        except Exception as e:
            print('请求书籍出错：' + str(e))
        else:    
            self.get_book_introduce(name, book_html)
            chapter_div_list = self.get_div_list(book_html, 'book')          
            for chapter in chapter_div_list :
                try:
                    chapter_name = chapter.p.string
                    if chapter_name is None:
                        chapter_name = str(chapter['data-title'])
                        chapter_name = re.sub('[\/:*?"<>|]','',chapter_name)
                    chapter_url = str(chapter['href'])
                except Exception as e:
                    print('解析书籍章节列表出错：' + str(e))
                    continue
                self.get_content(chapter_url, name, chapter_name)
              
    def get_pic_list(self, tag, book_path):
        """
        
        解析章节内容图片
        参数：tag 章节内容tag
              book_path 书籍路径
        """
        try:
            div_list = tag.find_all('img')   
            for pic in div_list:
                pic_src = str(pic['src'])
				#图片名为uuid，有可能会重复下载，由于没多少图片，自行筛选吧
                pic_name = str(uuid.uuid1()) + '.jpg'
                self.download_img(book_path + pic_name, pic_src)
        except Exception as e:
            print('获取图片出错：' + str(e))		  

    def get_content(self, url, book_name, chapter_name):
        """
        
        解析书籍内容
        参数：book_name 书名
              chapter_name 章节名
              url 内容地址
              
        """
        print('开始获取内容：' + chapter_name + '||||书籍：' + book_name + '||||地址：' + url)
        #排除非法字符
        book_name = re.sub('[\:*?"<>|]','',book_name)
        chapter_name = re.sub('[\:*?"<>|]','',chapter_name)
        #文件校验，存在文件跳过，防止重复请求地址消耗资源
        if os.path.exists(book_name + '/' + chapter_name + '.txt'):
            print('已存在章节' + chapter_name + '||||书籍：' + book_name)
            return
        try:
            content_html = self.get_request_html(url)
            bf = BeautifulSoup(content_html)
            result = bf.find_all('div', class_= 'forum-content')[0]   
            self.get_pic_list(result, book_name + '/')
        except Exception as e:
            print('获取正文出错' + str(e))
            #拿不到文章可能是贴吧或者轻国外链，写入到文件中
            self.write(book_name + '/' + chapter_name + '.txt', url)
        else:
            #去除nbsp空白符
            result = result.text.replace('\xa0'*8,'\n\n')
            self.write(book_name + '/' + chapter_name + '.txt', result)
 
    def write(self, path, text):
        """
        
        通用写入文件方法
        参数：path 文件路径
              
        """
        #排除非法字符
        path = re.sub('[\:*?"<>|]','',path)
        #文件存在时跳过，防止重复写入
        if os.path.exists(path):
            return
        try:
            file = open(path, 'w')
            file.close()
        except Exception as e:
            print('创建文件出错' + str(e))
        else:
            with open(path, 'a' , encoding = 'utf-8') as f:
                f.writelines(text)
            
    def mkdir(self, path):
        """
        
        通用创建文件夹方法
        参数：path 文件夹路径
              
        """
        #排除非法字符
        path = re.sub('[\:*?"<>|]','', path)
        folder = os.path.exists(path)
        if not folder:
            try:
                os.makedirs(path)  
            except Exception as e:
                print('创建文件夹出错：' + str(e))

    def download_img(self, path, src):
        """
        
        通用图片下载方法
        参数：path 下载图片路径
              src 图片地址
              
        """
        print('下载图片：' + src)
        #排除非法字符
        path = re.sub('[\:*?"<>|]','', path)
        #校验图片地址，防止重复写入图片
        if os.path.exists(path):
            return
        try:
			#构造请求头
            headers = {
				"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
				"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
				"Accept-encoding":"gzip, deflate, br",
				"Accept-Language":"zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
				"Connection":"keep-alive"
            }
			#设置翻墙的代理，v2ray为socks5端口+1
            proxies = {'http':'http://127.0.0.1:1081','https':'http://127.0.0.1:1081'}
            session = requests.Session()
            session.mount('http://', HTTPAdapter(max_retries=self.http_retry))
            session.mount('https://', HTTPAdapter(max_retries=self.http_retry))
			if self.proxy_switch == 0:
			    request = session.get(src, verify=False, headers=headers, timeout=self.http_timeout)
			else:
			    request = session.get(src, verify=False, headers=headers, proxies=proxies, timeout=self.http_timeout)
        except Exception as e:
            print('图片下载出错' + str(e))
        else:
            fp = open(path, 'wb')
            fp.write(request.content)
            fp.close()
 
dl = downloader()
dl.main()
