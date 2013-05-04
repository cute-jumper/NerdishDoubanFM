#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

#############################################################
# Using to concatenate the song file name
import os
from Settings import app_song_download_dir
def make_local_filename(song_info):
    return os.path.join(app_song_download_dir, ('%s_%s_%s'
                        %(song_info['title'], song_info['artist'], song_info['url'].split('/')[-1])).replace(' ', '-').replace(os.path.sep, ''))
#############################################################

#############################################################
# Calculate the real length of unicode string on screen
# Seems to have problems to work with curses
import unicodedata
def display_len(s):
    return sum(map(lambda x: 2 if unicodedata.east_asian_width(x) == 'W' else 1, s))

import re
RE = re.compile(u'[⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]', re.UNICODE)
def display_len1(s):            # The dirty version
    original_length = len(s)
    nonchinese_length = RE.sub('', s)
    return original * 2 - nonchinese

# Probably not correct, but works in a lot of situations
def display_len2(s):
    return sum([2 if ord(i) > 128 else 1 for i in s])
#############################################################

def scanl(f, acc, l):
    for x in l:
        acc = f(acc, x)
        yield acc
