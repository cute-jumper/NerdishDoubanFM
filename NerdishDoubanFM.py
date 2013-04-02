#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date:<2013-03-31 Sun>

import os
import gst
from ConfigParser import ConfigParser
from getpass import getpass
import unicodedata
import re

if not os.path.exists(app_cache_dir):
    os.mkdir(app_cache_dir)
    print '[Message]: mkdir', app_cache_dir
if not os.path.exists(app_img_cache_dir):
    os.mkdir(app_img_cache_dir)
    print '[Message]: mkdir', app_img_cache_dir
if not os.path.exists(app_lrc_cache_dir):
    os.mkdir(app_lrc_cache_dir)
    print '[Message]: mkdir', app_lrc_cache_dir
if not os.path.exists(app_song_download_dir):
    os.mkdir(app_song_download_dir)
    print '[Message]: mkdir', app_song_download_dir
if not os.path.exists(app_settings_dir):
    os.mkdir(app_settings_dir)
    print '[Message]: mkdir', app_settings_dir


lyric_api_url_template = 'http://geci.me/api/lyric/{title}/{artist}'
MAX_CHANNEL = 7
LYRIC_LENGTH = 40

def display_len(s):
    return sum(map(lambda x: 2 if unicodedata.east_asian_width(x) == 'W' else 1, s))

RE = re.compile(u'[⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]', re.UNICODE)
def display_len1(s):            # The dirty version
    original_length = len(s)
    nonchinese_length = RE.sub('', s)
    return original * 2 - nonchinese


parser = ConfigParser()
if not os.path.isfile(app_settings_file):
    answer = raw_input('Can not find %s, create one[Y/N]: ' %app_settings_file)
    if answer == 'y' or answer == 'Y':
        with open(app_settings_file, 'w') as fout:
            parser.add_section('USER')
            parser.add_section('SYSTEM')
            email = raw_input('Email: ')
            password = getpass('Password: ')
            parser.set('USER', 'email', email)
            parser.set('USER', 'password', password)
            parser.write(fout)
        print '[Message] Settings saved at ' + app_settings_file

user_email, user_password = '', ''
system_proxies = None
system_notification = False

if os.path.isfile(app_settings_file):
    parser.read(app_settings_file)
    try:
        user_email = parser.get('USER', 'email')
        user_password = parser.get('USER', 'password')
        if parser.has_option('SYSTEM', 'proxies'):
            system_proxies = eval(parser.get('SYSTEM', 'proxies'))
        if parser.has_option('SYSTEM', 'notification'):
            system_notification = parser.getboolean('SYSTEM', 'notification')
    except:
        print '[Error] Abnormal setting file. Please check ' + app_settings_file
        exit(1)


        
            
def make_local_filename(song_info):
    return os.path.join(app_song_download_dir, '%s_%s_%s'
                        %(song_info['title'], song_info['artist'], song_info['url'].split('/')[-1]))
    
if __name__ == '__main__':
    CursesUI().run()
    
