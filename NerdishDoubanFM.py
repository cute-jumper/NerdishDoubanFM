#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date:<2013-03-31 Sun>

import os
from getpass import getpass

if __name__ == '__main__':
    from Settings import *

    if DEBUG:
        import logging
        logging.basicConfig(filename=os.path.join(app_cache_dir, 'example.log'), filemode='w', level=logging.DEBUG)

    dirs = [app_cache_dir, app_img_cache_dir, app_lrc_cache_dir, app_song_download_dir]
    for i in dirs:
        if not os.path.exists(i):
            os.mkdir(i)
            print '[Message]: mkdir', i
    
    if not user_email:
        user_email = raw_input('Email: ')
        user_password = getpass('Password: ')
    elif not user_password:
        user_password = getpass('Password: ')

    from CursesUI import CursesUI
    CursesUI(user_email, user_password, system_proxies, system_notification).run()
    
