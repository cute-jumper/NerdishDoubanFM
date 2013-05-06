#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

import requests
from getpass import getpass

app_name = 'radio_desktop_win'
version = 100
APP_INFO = {'app_name': app_name, 'version': version}
DOUBAN_FM_LOGIN_URL = 'http://www.douban.com/j/app/login'
DOUBAN_FM_CHANNEL_URL = 'http://www.douban.com/j/app/radio/channels'
DOUBAN_FM_API_URL = 'http://www.douban.com/j/app/radio/people'
LIST_LENGTH = 20
EXCLUDE_TITLES = [u'暑期开发训练营', u'流浪动物救助站',
                  u'豆瓣阅读Android版更新']

from Settings import DEBUG
if DEBUG:
    import logging

class DoubanFM(object):
    def __init__(self, proxies):
        self.current_channel = 1
        self.history = []
        self.playlist = None
        self.logined = False
        self.user_info = {'email': '', 'password': ''}
        self.proxies = proxies
        
    def is_logined(self):
        return self.logined
    
    def login(self, email = None, password = None):
        if self.logined:
            return True
        if not self.user_info['email']:
            self.user_info.update({'email': email if email != None else raw_input('Email: ')})
        if not self.user_info['password']:
            self.user_info.update({'password': password if password != None else getpass('Password: ')})
        payload = dict(self.user_info.items() + APP_INFO.items())
        data = requests.post(DOUBAN_FM_LOGIN_URL, data=payload, proxies=self.proxies).json()
        if data['err']!='ok':
            return False
        self.login_info = data
        self.logined = True
        return True
    
    def get_json_from_api(self, payload):
        return requests.get(DOUBAN_FM_API_URL, params=payload, proxies=self.proxies).json()
    
    def get_params(self, channel_id, report):
        params = dict(APP_INFO.items() + [('type', report), ('channel', channel_id)])
        if report != 'n':
            params.update({'sid': self.cur_song['sid'], 'h': '|' + ':s|'.join([i['sid'] for i in self.history]) + ':p'})
            self.history = []
        if self.logined:
            params.update({i: self.login_info[i] for i in ['user_id', 'expire','token']})
        return params

    def get_new_playlist(self, channel_id):
        payload = self.get_params(channel_id, 'n')
        ret = self.get_json_from_api(payload)['song']
        if DEBUG: logging.info(' '.join([i['title'] for i in ret]))
        return ret
    
    def get_next_playlist(self, channel_id):
        payload = self.get_params(channel_id, 'p')
        ret = self.get_json_from_api(payload)['song']
        if DEBUG: logging.info(' '.join([i['title'] for i in ret]))
        return ret
    
    def rate_song(self, channel_id, to_rate):
        payload = self.get_params(channel_id, 'r' if to_rate else 'u')
        return self.get_json_from_api(payload)
    
    def skip_song(self, channel_id):
        payload = self.get_params(channel_id, 's')
        return self.get_json_from_api(payload)['r']
    
    def get_next_song_info(self):
        cid = self.current_channel['channel_id']
        if len(self.playlist) < 2:
            self.playlist.extend(self.get_next_playlist(cid))
        self.playlist = [song for song in self.playlist if song['title'] not in EXCLUDE_TITLES]
        song = self.playlist.pop(0)
        self.history.append(song)
        while len(self.history) > LIST_LENGTH:
            self.history.pop(0)
        self.cur_song = song
        if DEBUG: logging.info(song)
        return song
    
    def change_channel(self, channel):
        self.current_channel = channel
        self.playlist = self.get_new_playlist(channel['channel_id'])
        
    def get_channel_list(self):
        r = requests.get(DOUBAN_FM_CHANNEL_URL, proxies=self.proxies)
        return r.json()['channels']

