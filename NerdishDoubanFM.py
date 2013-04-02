#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date:<2013-03-31 Sun>

import urllib, urllib2, json, requests
import os
import curses
import pynotify
import gst
import locale
from select import select
import sys
import time
from ConfigParser import ConfigParser
from getpass import getpass
import unicodedata
import re

app_dir = os.path.dirname(os.path.abspath(__file__))

app_cache_dir = os.path.join(app_dir, '.cache')
app_img_cache_dir = os.path.join(app_cache_dir, '.img')
app_lrc_cache_dir = os.path.join(app_cache_dir, '.lrc')
app_song_download_dir = os.path.join(app_cache_dir, '.song')

app_settings_dir = os.path.join(app_dir, '.config')
app_settings_file = os.path.join(app_settings_dir, 'settings.conf')

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

app_name = 'radio_desktop_win'
version = 100
app_info = {'app_name': app_name, 'version': version}
douban_fm_login_url = 'http://www.douban.com/j/app/login'
douban_fm_channel_url = 'http://www.douban.com/j/app/radio/channels'
douban_fm_api_url = 'http://www.douban.com/j/app/radio/people'
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

# ncurses UI code
class CursesUI(object):
    def __init__(self):
        self.current_channel = 1
        self.channel_list = None
        self.dbfm = DoubanFM()
        self.has_lyric = False
        self.download_manager = DownloadManager()
        self.current_song_info = None
        self.setup_main_win()
        self.setup_left_win()
        self.setup_right_win()
        self.setup_console_win()
        self.enable_notification = system_notification
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
        for channel in self.channel_list:
            if channel['seq_id'] > MAX_CHANNEL: # TODO: List all channels
                continue
            left_win.addstr((channel['seq_id'] + 2) * 2, 2, channel['name'])
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
        self.right_win.addstr(10, 3, '-' * length + '>' + ' ' * (40 - length))
        position_text = self.convert_seconds(position_int, 1000000000)
        self.right_win.addstr(11, 34, position_text)
        if self.has_lyric:
            lyric_line = self.get_lyric_line(position_text)
            self.right_win.addstr(7, 2, '%', curses.color_pair(13))
            self.right_win.addstr(7, 4, lyric_line +
                                  ' ' * (LYRIC_LENGTH - len(lyric_line)))
        self.right_win.refresh()
        return length == 40
        
    def setup_console_win(self):
        console_x, console_y = 30, 16
        console_height, console_width = 8, 49
        self.console_win = console_win = curses.newwin(console_height, console_width, console_y, console_x)
        self.console_win_restore()
        console_win.refresh()
        self.console_win_line = 0
        
    def add_console_output(self, message, input_line = None):
        line = self.console_win_line
        if input_line != None:
            line = input_line
        else:
            self.console_win_line += 1
            if self.console_win_line > 5:
                self.console_win_line = 0
        self.console_win.addstr(2 + line, 2, (str(message)).encode(code))
        self.console_win.clrtoeol()
        self.console_win_restore()
        self.console_win.refresh()
        
    def show_song_info(self, song_info):
        self.right_win.addstr(2, 2, song_info['artist'].encode(code))
        self.right_win.clrtoeol()
        self.right_win.addstr(3, 2, ('%s %s' %(song_info['albumtitle'], song_info['public_time'])).encode(code))
        self.right_win.clrtoeol()
        self.right_win.addstr(5, 2, song_info['title'].encode(code), curses.A_BOLD)
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
        seq_id = (cursor_y / 2 - 2)
        if (seq_id == -1 or seq_id == 0) and not self.dbfm.is_logined():
            self.add_console_output('Please log in first! Press "l".')
            return None
        ret = None
        for i in self.channel_list:
            if i['seq_id'] == seq_id:
                self.left_win.addstr((i['seq_id'] + 2) * 2, 2, i['name'], curses.color_pair(1))
                ret = i
            elif i['seq_id'] <= MAX_CHANNEL: # TODO
                self.left_win.addstr((i['seq_id'] + 2) * 2, 2, i['name'])
        self.left_win.refresh()
        return ret

    def play_next_song(self, p):
        self.has_lyric = False
        self.current_song_info = self.dbfm.get_next_song_info()
        self.show_song_info(self.current_song_info)
        ret = self.download_manager.download_lyric(self.current_song_info)
        if ret == None:
            self.has_lyric = False
            self.add_console_output('No lyric found!')
        else:
            self.has_lyric = True
            self.lyrics = ret
            self.add_console_output('Lyric downloaded.')
        if self.enable_notification:
            self.send_notification(self.current_song_info)
        p.play_song(self.current_song_info)
        
    def stop_and_remove(self, player, song_info):
        player.stop_song()
        if player.is_http_player():
            os.remove(make_local_filename(self.current_song_info))
        
    def run(self):
        self.left_win.move(2, 2)
        p = MusicPlayer()
        player_started = False
        # while True:
        #     time.sleep(0.2)
        #     self.duration_int = p.duration
        #     if self.duration_int == -1:
        #         continue
        #     duration_text = self.convert_ns(self.duration_int)
        #     self.right_win.addstr(11, 34, "00:00/%s" %duration_text)
        #     self.right_win.refresh()
        #     break
        while True:
            self.right_win.refresh()
            self.left_win.refresh()
            rlist, _, _ = select([sys.stdin], [], [], 1)
            if player_started:
                try:
                    position_int = p.position
                    if self.set_progress(position_int):
                        p.stop_song()
                        self.play_next_song(p)
                except:
                    continue
            if not rlist:
                continue
            ch = self.left_win.getch()
            cursor_y, cursor_x = self.left_win.getyx()
            if ch == ord('c'):
                if cursor_x != 2:
                    self.left_win.move(2, 2)
                    continue
                if player_started:
                    self.stop_and_remove(p, self.current_song_info['url'])
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
                if cursor_y < (MAX_CHANNEL + 2 )* 2:
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
                if self.dbfm.login(user_email, user_password):
                    self.add_console_output("Log in successful!")
                else:
                    self.add_console_output('Log in failure!')
            else:
                self.stop_and_remove(p, self.current_song_info['url'])
                break
        self.end_curses_app()
        
    def get_lyric_line(self, position_text):
        for (idx, line) in enumerate(self.lyrics):
            if line[0] > position_text:
                return self.lyrics[idx - 1][1][:LYRIC_LENGTH] # Only part of the lyric if too long
        return '' #self.lyric[-1][1][:LYRIC_LENGTH] Bugs???
    
    def send_notification(self, song_info):
        description = '歌手: %s<br/>专辑: %s' %(song_info['artist'], song_info['albumtitle'])
        image = self.download_manager.download_image(song_info['picture'])
        pynotify.init(song_info['title'])
        n = pynotify.Notification(song_info['title'], description, image)
        n.set_hint_string('x-canonical-append','')
        n.show()
        
class DownloadManager(object):
    def download_lyric(self, song_info):
        filename = os.path.join(app_lrc_cache_dir, '%s_%s.lrc' %(song_info['title'], song_info['artist']))
        if not os.path.isfile(filename):
            try:
                ret = requests.get(lyric_api_url_template.format(title=song_info['title'], artist=song_info['artist']), proxies=system_proxies).json()
            except:
                return None
            if ret['count'] == 0:
                return None
            lrc = requests.get(ret['result'][0]['lrc'], proxies=system_proxies)
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
            r = requests.get(image_url, proxies=system_proxies)
            with open(image_abspath, 'wb') as fout:
                fout.write(r.content)
        return image_abspath
    def download_song(self, song_info):
        filename = os.path.join(app_song_download_dir, '%s_%s.mp3' %(song_info['title'], song_info['artist']))
        if not os.path.isfile(filename):
            r = requests.get(url, proxies=system_proxies)
            with open(filename, 'wb') as fout:
                fout.write(r.content)
        return True

class MusicPlayer(object):
    def __init__(self):
        self.http_player = gst.parse_launch('souphttpsrc name=httpsrc ! tee name=t ! queue ! filesink name=filedest t. ! queue ! mad ! audioconvert ! alsasink')
	bus = self.http_player.get_bus()
	bus.add_signal_watch()
	bus.connect("message", self.on_message_http)
        self.local_player = gst.element_factory_make('playbin2', 'local_player')
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.local_player.set_property("video-sink", fakesink)
        self.current_player = None
	bus = self.local_player.get_bus()
	bus.add_signal_watch()
	bus.connect("message", self.on_message_local)
        self.play_state = None
        self.playmode = False
        
    def set_play_state(self, player, state):
        self.play_state = state
        player.set_state(state)
        
    def get_play_state(self):
        return self.play_state

    def play_song(self, song_info):
        uri = song_info['url']
        filepath = make_local_filename(song_info)
        self.set_play_state(self.http_player, gst.STATE_NULL)
        self.set_play_state(self.local_player, gst.STATE_NULL)
        if os.path.isfile(filepath):
            self.local_player.set_property('uri', 'file://' + filepath)
            self.current_player = self.local_player
            self.set_play_state(self.local_player, gst.STATE_PLAYING)
        else:
            self.http_player.get_by_name('httpsrc').set_property('location', uri)
            self.http_player.get_by_name('filedest').set_property('location', filepath)
            self.current_player = self.http_player
            self.set_play_state(self.http_player, gst.STATE_PLAYING)
        self.playmode = True
        
    def stop_song(self):
        self.set_play_state(self.http_player, gst.STATE_NULL)
        self.set_play_state(self.local_player, gst.STATE_NULL)
        self.playmode = False
        
    def is_http_player(self):
        return self.current_player == self.http_player
        
    def toggle_paused_song(self):
        if self.get_play_state() == gst.STATE_PLAYING:
            self.set_play_state(self.current_player, gst.STATE_PAUSED)
        elif self.get_play_state() == gst.STATE_PAUSED:
            self.set_play_state(self.current_player, gst.STATE_PLAYING)
        
    def on_message_local(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.set_play_state(self.local_player, gst.STATE_NULL)
            self.playmode = False
        elif t == gst.MESSAGE_ERROR:
            self.set_play_state(self.local_player, gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.playmode = False

    def on_message_http(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.set_play_state(self.http_player, gst.STATE_NULL)
            self.playmode = False
        elif t == gst.MESSAGE_ERROR:
            self.set_play_state(self.http_player, gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.playmode = False
            
    @property
    def duration(self):
        return self.current_player.query_duration(gst.FORMAT_TIME, None)[0]
    
    @property
    def position(self):
        return self.current_player.query_position(gst.FORMAT_TIME, None)[0]
        
class DoubanFM(object):
    def __init__(self):
        self.current_channel = 1
        self.history = []
        self.playlist = None
        self.logined = False
        self.user_info = {'email': '', 'password': ''}
        
    def is_logined(self):
        return self.logined
    def login(self, email = None, password = None):
        if self.logined:
            return True
        if not self.user_info['email']:
            self.user_info.update({'email': email if email != None else raw_input('Email: ')})
        if not self.user_info['password']:
            self.user_info.update({'password': password if password != None else getpass('Password: ')})
        payload = dict(self.user_info.items() + app_info.items())
        data = requests.post(douban_fm_login_url, data=payload, proxies=system_proxies).json()
        if data['err']!='ok':
            return False
        self.login_info = data
        self.logined = True
        return True
    def get_json_from_api(self, payload):
        return requests.get(douban_fm_api_url, params=payload, proxies=system_proxies).json()
    def get_params(self, channel_id, report):
        params = dict(app_info.items() + [('type', report), ('channel', channel_id)])
        if report != 'n':
            params.update({'sid': self.cur_song['sid']})#, 'h': self.history})
        if self.logined:
            params.update({i: self.login_info[i] for i in ['user_id', 'expire','token']})
        return params

    def get_new_playlist(self, channel_id):
        payload = self.get_params(channel_id, 'n')
        return self.get_json_from_api(payload)['song']
    def get_next_playlist(self, channel_id):
        payload = self.get_params(channel_id, 'p')
        return self.get_json_from_api(payload)['song']
    def rate_song(self, channel_id, to_rate):
        payload = self.get_params(channel_id, 'r' if to_rate else 'u')
        return self.get_json_from_api(payload)
    def skip_song(self, channel_id):
        payload = self.get_params(channel_id, 's')
        return self.get_json_from_api(payload)['r']
    def get_next_song_info(self):
        cid = self.current_channel['channel_id']
        if not self.playlist:
            self.playlist = self.get_new_playlist(cid)
        elif len(self.playlist) < 2:
            self.playlist.extend(self.get_next_playlist(cid))
        song = self.playlist.pop(0)
        self.history.append(song)
        if len(self.history) > 15:
            self.history.pop(0)
        self.cur_song = song
        return song
    
    def change_channel(self, channel):
        self.current_channel = channel
        self.playlist = self.get_new_playlist(channel['channel_id'])
        
    def get_channel_list(self):
        r = requests.get(douban_fm_channel_url, proxies=system_proxies)
        return r.json()['channels']

        for channel in self.channels:
            print('%d\t%s\t%s'%(channel['channel_id'],channel['name'],channel['name_en']))
            
def make_local_filename(song_info):
    return os.path.join(app_song_download_dir, '%s_%s_%s'
                        %(song_info['title'], song_info['artist'], song_info['url'].split('/')[-1]))
    
if __name__ == '__main__':
    CursesUI().run()
    
