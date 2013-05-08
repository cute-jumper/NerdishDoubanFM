#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

#########################################
# **DON'T CHANGE**
import os
app_dir = os.path.dirname(os.path.abspath(__file__))
app_cache_dir = os.path.join(app_dir, '.cache')
app_img_cache_dir = os.path.join(app_cache_dir, '.img')
app_lrc_cache_dir = os.path.join(app_cache_dir, '.lrc')
app_song_download_dir = os.path.join(app_cache_dir, '.song')
#########################################

#########################################
# USER Settings. Change here.
user_email = ''
user_password = ''
system_proxies = None
system_notification = False
#########################################

# Developer settings
DEBUG = True
