#!/usr/bin/env python3
# Copyright (c) 2024 oatsu
"""
UTAU上のピッチベンドをENUNUのWAV出力に反映する。
acousticモデルが出力したf0のCSVファイルを書き換えることで反映する。
ENUNU v0.6.0 における拡張機能のうち acoustic_editor として起動する。
"""

from argparse import ArgumentParser
from copy import copy
from math import cos, log10, pi
from pprint import pprint
import pathlib
import sys
from glob import glob
from os import chdir, getcwd
from os.path import abspath, dirname, join
from pprint import pprint
from tempfile import TemporaryDirectory
from time import sleep
from tkinter.filedialog import asksaveasfilename

import colored_traceback.always
import utaupy
from natsort import natsorted
from PyUtauCli.projects.Render import Render
from PyUtauCli.projects.Ust import Ust
from PyUtauCli.voicebank import VoiceBank



def get_ust_pitches(ust):
    """USTファイル中のf0列を取得する。
    """
    # utaupyで音源フォルダのパスを取得
    voice_dir = ust.voicedir
    # PyUtauCli で音源の内容を読み取る
    voicebank = VoiceBank(voice_dir)
    # 

    # ust_path = ust.setting.get('Project')    
    # cache_dir = plugin.setting.get('CacheDir', 'cache')
