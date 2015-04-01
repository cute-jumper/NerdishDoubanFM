#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

import curses
import pynotify
import locale
import sys
import os
from collections import deque
from select import select

from DoubanFM import DoubanFM
from DownloadManager import DownloadManager
from MusicPlayer import MusicPlayer
from Utils import make_local_filename, display_len2, scanl
from operator import add
from itertools import takewhile
from Settings import DEBUG


MAX_CHANNEL = 9
LYRIC_LENGTH = 40

if DEBUG:
    import logging

class CursesUI(object):
    def __init__(self, user_email, user_password, system_proxies, system_notification, show_lyric, channels_file):
        self.current_channel = None
        self.channel_list = None
        self.channels_file = channels_file
        self.dbfm = DoubanFM(system_proxies)
        self.has_lyric = False
        self.download_manager = DownloadManager(system_proxies)
        self.current_song_info = None
        self.setup_main_win()
        self.setup_left_win()
        self.setup_right_win()
        self.setup_console_win()
        self.user_email = user_email
        self.user_password = user_password
        self.enable_notification = system_notification
        self.show_lyric = show_lyric
        self.console_log = deque()
    def setup_main_win(self):
        #locale
        locale.setlocale(locale.LC_CTYPE, '')
        global code
        code = locale.getpreferredencoding()
        ## initialize
        self.stdscr = stdscr = curses.initscr()
        ## use color
        if curses.has_colors():
            curses.start_color()
        ## set options
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(1)
        ## set colors
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(13, curses.COLOR_CYAN, curses.COLOR_BLACK)

    def end_curses_app(self):
        curses.nocbreak()
        self.left_win.keypad(0)
        self.right_win.keypad(0)
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def left_win_restore(self):
        self.left_win.border(0)
        l_title = "channel"
        self.left_win.addstr(0, 0, l_title.encode(code), curses.A_BOLD)
    def right_win_restore(self):
        self.right_win.border(0)
        r_title = "Playing"
        self.right_win.addstr(0, 0, r_title.encode(code), curses.A_BOLD)
    def console_win_restore(self):
        self.console_win.border(0)
        self.console_win.addstr(0, 0, 'Console'.encode(code), curses.A_BOLD)
        
    def setup_console_win(self):
        console_x, console_y = 30, 16
        console_height, console_width = 8, 49
        self.console_win = console_win = curses.newwin(console_height, console_width, console_y, console_x)
        self.console_win_restore()
        console_win.refresh()
        
    def setup_left_win(self):
        ## left window
        l_begin_x, l_begin_y = 0, 0
        l_height, l_width = 24, 29
        self.left_win = left_win = curses.newwin(l_height, l_width, l_begin_y, l_begin_x)
        left_win.keypad(1)
        self.left_win_restore()
        # Add Hearted Radio, which is not in the API's returning list
        self.channel_list = [{'abbr_en': 'Hearted',
                              'channel_id': -3,
                              'name': u'红心兆赫',
                              'name_en': 'Hearted Radio',
                              'seq_id': -1}] + self.dbfm.get_channel_list()
        if DEBUG: logging.info(self.channel_list)
        # Below is dirty and quick hack...
        if os.path.exists(self.channels_file):
            with open(self.channels_file) as fin:
                extra_channel = eval(fin.readline())
                extra_channel['channel_id'] = extra_channel['id']
                self.channel_list[MAX_CHANNEL - 1] = extra_channel;

        for idx, channel in enumerate(self.channel_list):
            if idx >= MAX_CHANNEL: # TODO: List all channels
                break
            left_win.addstr((idx + 1) * 2, 2, channel['name'].strip())
        left_win.addstr(19, 2, '-' * (l_width - 4))
        left_win.addstr(20, 2, "上移: k或↑, 下移: j或↓")
        left_win.addstr(21, 2, "登录: l, 选择: c")
        left_win.addstr(22, 2, "退出: q")
        
        left_win.refresh()
    
    def setup_right_win(self):
        ## right window
        r_begin_x = 30; r_begin_y = 0
        r_height = 16; r_width = 49
        self.right_win = right_win = curses.newwin(r_height, r_width, r_begin_y, r_begin_x)
        self.right_win_restore()

        right_win.addstr(13, 10, "取消喜欢(u)", curses.color_pair(1))
        right_win.addstr(13, 24, "加红心(r)", curses.color_pair(1))
        right_win.addstr(13, 36, "下一首(n)", curses.color_pair(1))
        right_win.addstr(10, 2, '[')
        right_win.addstr(10, 44, ']')
        
        right_win.refresh()
        
    def set_like_status(self):
        if True:
            right_win.addstr(14, 30, "加红心(f)")
        else:
            right_win.addstr(14, 29, "删除红心(d)")
    def set_progress(self, position_int):
        length = position_int * 40 / 1000000000 / self.current_song_info['length']
        if length > 40:
            length = 40         # Force it!
        self.right_win.addstr(10, 3, '-' * length + '>' + ' ' * (40 - length))
        position_text = self.convert_seconds(position_int, 1000000000)
        self.right_win.addstr(11, 34, position_text)
        if self.has_lyric:
            lyric_line = self.get_lyric_line(position_text)
            self.right_win.addstr(7, 2, '%', curses.color_pair(13))
            self.right_win.addstr(7, 4, lyric_line +
                                  ' ' * (LYRIC_LENGTH - display_len2(lyric_line.decode('utf-8'))))
        else:
            self.right_win.addstr(7, 2, ' ' * (LYRIC_LENGTH + 2))
        self.right_win.refresh()
         # Really really really ugly... But it seems the problem was caused by
         # the library... Well, I'm not sure though.
        return abs(position_int / 100000000 - self.current_song_info['length'] * 10) <= 5
        
    def add_console_output(self, message):
        self.console_log.append(message)
        while len(self.console_log) > 5:
            self.console_log.popleft()
        for (idx, msg) in enumerate(reversed(self.console_log)):
            self.console_win.addstr(2 + idx, 2, (str(msg)).encode(code))
            self.console_win.clrtoeol()
        self.console_win_restore()
        self.console_win.refresh()
        
    def show_song_info(self, song_info):
        self.right_win.addstr(2, 2, song_info['artist'].encode(code))
        self.right_win.clrtoeol()
        self.right_win.addstr(3, 2, ('%s %s' %(song_info['albumtitle'], song_info['public_time'])).encode(code))
        self.right_win.clrtoeol()
        self.right_win.move(4, 1)
        self.right_win.clrtoeol()
        self.right_win.addstr(5, 2, song_info['title'].encode(code), curses.A_BOLD)
        self.right_win.clrtoeol()
        self.right_win.move(6, 1)
        self.right_win.clrtoeol()
        self.right_win.addstr(13, 2, ('♡' if song_info['like'] == 0 else '♥').encode(code), curses.A_BOLD)
        
        duration_text = self.convert_seconds(self.current_song_info['length'], 1)
        self.right_win.addstr(11, 34, "00:00/%s" %duration_text)
        self.right_win_restore()
        self.right_win.refresh()
        
    def convert_seconds(self, t, times):
        # This method was submitted by Sam Mason.
        # It's much shorter than the original one.
        s, _ = divmod(t, times)
        m, s = divmod(s, 60)
        if m < 60:
            return "%02i:%02i" %(m,s)
        else:
            h, m = divmod(m, 60)
            return "%i:%02i:%02i" %(h,m,s)


    def get_channel_to_play(self, cursor_y):
        selected_idx = cursor_y / 2 - 1
        selected_channel = self.channel_list[selected_idx]
        if selected_idx == 0 and not self.dbfm.is_logined():
            self.add_console_output('Please log in first! Press "l".')
            return None
        for idx, channel in enumerate(self.channel_list):
            if idx == selected_idx:
                self.left_win.addstr((selected_idx + 1) * 2, 2,
                                     selected_channel['name'],
                                     curses.color_pair(1))
            elif idx < MAX_CHANNEL:
                self.left_win.addstr((idx + 1) * 2, 2, channel['name'])
        self.left_win.refresh()
        return selected_channel

    def play_next_song(self, p):
        self.has_lyric = False
        self.current_song_info = self.dbfm.get_next_song_info()
        self.show_song_info(self.current_song_info)
        # show lyric?
        if not self.show_lyric:
            self.has_lyric = False
        else:
            ret = self.download_manager.download_lyric(self.current_song_info)
            if ret == None:
                self.has_lyric = False
                self.add_console_output('No lyric found!')
            else:
                self.has_lyric = True
                self.lyrics = ret
                self.add_console_output('Lyric downloaded.')
        # send notifications?
        if self.enable_notification:
            self.send_notification(self.current_song_info)
        p.play_song(self.current_song_info)
        
    def stop_and_remove(self, player, song_info):
        player.stop_song()
        local_filename = make_local_filename(self.current_song_info)
        if player.is_http_player() and os.path.exists(local_filename):
            os.remove(local_filename)
        
    def run(self):
        try:
            self.left_win.move(2, 2)
            p = MusicPlayer()
            player_started = False
            while True:
                self.right_win.refresh()
                self.left_win.refresh()
                if player_started:
                    try:
                        position_int = p.position
                        if self.set_progress(position_int):
                            if DEBUG: logging.info("set_progress true")
                            p.stop_song()
                            self.play_next_song(p)
                    except:
                        continue
                self.left_win.refresh()
                rlist, _, _ = select([sys.stdin], [], [], 1)
                if not rlist:
                    continue
                ch = self.left_win.getch()
                if DEBUG: logging.info("getch: %c" %ch)
                cursor_y, cursor_x = self.left_win.getyx()
                if ch == ord('c'):
                    if cursor_x != 2:
                        self.left_win.move(2, 2)
                        continue
                    if player_started:
                        self.stop_and_remove(p, self.current_song_info['url'])
                    player_started = False # Can't leave out this
                    current_channel = self.get_channel_to_play(cursor_y)
                    if current_channel == None:
                        continue
                    self.current_channel = current_channel
                    player_started = True
                    self.dbfm.change_channel(self.current_channel)
                    self.play_next_song(p)
                    self.left_win.move(cursor_y, cursor_x)
                elif ch == ord('n'):
                    if not player_started:
                        continue
                    self.stop_and_remove(p, self.current_song_info['url'])
                    self.play_next_song(p)
                elif ch == ord('r'):
                    if not self.dbfm.is_logined():
                        self.add_console_output('Please log in first! Press "l".')
                        continue
                    if self.current_song_info['like'] == 1:
                        self.add_console_output('Already hearted!')
                        continue
                    if self.dbfm.rate_song(self.current_channel['channel_id'], True)['r'] == 0:
                        self.add_console_output("Hearted %s successfully!" %self.current_song_info['title'])
                        self.current_song_info['like'] = 1
                        self.show_song_info(self.current_song_info)
                    else:
                        self.add_console_output("Hearted %s failure!" %self.current_song_info['title'])
                elif ch == ord('u'):
                    if not self.dbfm.is_logined():
                        self.add_console_output('Please log in first! Press "l".')
                        continue
                    if self.current_song_info['like'] == 0:
                        self.add_console_output("Haven't hearted yet!")
                        continue
                    if self.dbfm.rate_song(self.current_channel['channel_id'], False)['r'] == 0:
                        self.add_console_output("Unhearted %s successfully!" %self.current_song_info['title'])
                        self.current_song_info['like'] = 0
                        self.show_song_info(self.current_song_info)
                    else:
                        self.add_console_output("Unhearted %s failure!" %self.current_song_info['title'])

                elif ch == ord('j') or ch == curses.KEY_DOWN:
                    if cursor_y <= (MAX_CHANNEL + 2) * 2:
                        self.left_win.move(cursor_y + 2, 2)
                    else:
                        continue
                elif ch == ord('k') or ch == curses.KEY_UP:
                    if cursor_y > 2:
                        self.left_win.move(cursor_y - 2, 2)
                    else:
                        continue
                elif ch == ord('p'):
                    p.toggle_paused_song()
                elif ch == ord('l'):
                    if self.dbfm.login(self.user_email, self.user_password):
                        self.add_console_output("Successfully log in!")
                    else:
                        self.add_console_output('Failed to log in!')
                else:
                    self.stop_and_remove(p, self.current_song_info['url'])
                    break
        except Exception, e:
            if player_started and self.current_song_info != None:
                self.stop_and_remove(p, self.current_song_info['url'])
            if DEBUG: logging.info(e)
        finally:
            self.end_curses_app()
        
    def get_lyric_line(self, position_text):
        def get_longest_lyrics_len(index):
            return len(list(takewhile(lambda s: s <= LYRIC_LENGTH,
                            scanl(add, 0,
                                  [2 if ord(i) > 127 else 1 for i in self.lyrics[index][1].decode('utf-8')]))))
        for (idx, line) in enumerate(self.lyrics):
            if line[0] > position_text:
                index = max(idx - 1, 0)
                return self.lyrics[index][1].decode('utf-8')[:get_longest_lyrics_len(index)] # Only part of the lyric if too long
        return self.lyrics[-1][1].decode('utf-8')[:get_longest_lyrics_len(-1)]
    
    def send_notification(self, song_info):
        description = '歌手: %s<br/>专辑: %s' %(song_info['artist'], song_info['albumtitle'])
        image = self.download_manager.download_image(song_info['picture'])
        pynotify.init(song_info['title'])
        n = pynotify.Notification(song_info['title'], description, image)
        n.set_hint_string('x-canonical-append','')
        n.show()
