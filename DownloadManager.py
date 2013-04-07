#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

import requests
import os

from Settings import app_lrc_cache_dir, app_img_cache_dir, app_song_download_dir

LYRIC_API_URL_TEMPLATE = 'http://geci.me/api/lyric/{title}/{artist}'

class DownloadManager(object):
    def __init__(self, proxies):
        self.proxies = proxies
    def download_lyric(self, song_info):
        filename = os.path.join(app_lrc_cache_dir, '%s_%s.lrc' %(song_info['title'].replace(' ', '-').replace(os.path.sep, ''), song_info['artist'].replace(' ', '-').replace(os.path.sep, '')))
        if not os.path.isfile(filename):
            try:
                ret = requests.get(LYRIC_API_URL_TEMPLATE.format(title=song_info['title'].replace(os.path.sep, ''), artist=song_info['artist'].replace(os.path.sep, '')), proxies=self.proxies).json()
            except:
                return None
            if ret['count'] == 0:
                return None
            lrc = requests.get(ret['result'][0]['lrc'], proxies=self.proxies)
            with open(filename, 'w') as fout:
                fout.write(lrc.content)                
            lines = lrc.content.split('\n')
        else:
            with open(filename) as fin:
                lines = fin.readlines()
        lines = filter(lambda x: len(x) != 0 and x.startswith('[0'), map(str.strip, lines))
        lyrics = dict()
        for line in lines:
            segments = line.split(']')
            timestamps, words = map(lambda x: x[1:-3], segments[:-1]), segments[-1]
            for ts in timestamps:
                lyrics[ts] = words
        return sorted(lyrics.items())
    def download_image(self, image_url):
        image_basename = image_url.split('/')[-1]
        image_abspath = os.path.join(app_img_cache_dir, image_basename)
        if not os.path.isfile(image_abspath):
            r = requests.get(image_url, proxies=self.proxies)
            with open(image_abspath, 'wb') as fout:
                fout.write(r.content)
        return image_abspath
    def download_song(self, song_info):
        filename = os.path.join(app_song_download_dir, '%s_%s.mp3' %(song_info['title'], song_info['artist']))
        if not os.path.isfile(filename):
            r = requests.get(url, proxies=self.proxies)
            with open(filename, 'wb') as fout:
                fout.write(r.content)
        return True
