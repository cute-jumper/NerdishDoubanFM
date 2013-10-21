#! /usr/bin/env python
#-*- coding: utf-8 -*-
# Author: qjp
# Date: <2013-04-02 Tue>

import gst
import os

from Utils import make_local_filename

from Settings import DEBUG

if DEBUG:
    import logging

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
        if DEBUG: logging.info("stop song!")
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

