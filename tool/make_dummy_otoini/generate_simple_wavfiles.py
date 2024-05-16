"""
ChatGPTに書いてもらった
"""

import numpy as np
import scipy.io.wavfile as wavfile
from os.path import dirname, join

def generate_sine_wave(frequency, duration, sample_rate=44100):
    """正弦波を合成する
    """
    time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = np.sin(2 * np.pi * frequency * time)
    return wave

def generate_triangle_wave(frequency, duration, sample_rate=44100):
    """三角波を合成する
    """
    time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 2 * np.abs(2 * (time * frequency - np.floor(0.5 + time * frequency))) - 1
    return wave

def generate_square_wave(frequency, duration, duty_cycle=0.5, sample_rate=44100):
    """矩形波を合成する
    """
    time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = np.where(np.mod(time * frequency, 1) < duty_cycle, 1, -1)
    return wave

def generate_sawtooth_wave(frequency, duration, sample_rate=44100):
    """鋸波を合成する
    """
    time = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 2 * (time * frequency - np.floor(0.5 + time * frequency))
    return wave

def save_wave(filename, wave, sample_rate=44100):
    """wavファイル出力する
    """
    scaled = np.int16(wave / 2 * 32767)
    wavfile.write(filename, sample_rate, scaled)


def main():
    # 各波形を生成して保存
    duration = 2  # 2秒間
    sample_rate = 44100  # サンプルレート
    frequency = 440 # 周波数
    out_dir = dirname(__file__)
    save_wave(join(out_dir, "sine_wave.wav"), generate_sine_wave(frequency, duration, sample_rate))
    save_wave(join(out_dir, "triangle_wave.wav"), generate_triangle_wave(frequency, duration, sample_rate))
    save_wave(join(out_dir, "square_wave.wav"), generate_square_wave(frequency, duration, 0.5, sample_rate))  # デューティサイクル0.5
    save_wave(join(out_dir, "sawtooth_wave.wav"), generate_sawtooth_wave(frequency, duration, sample_rate))


if __name__=='__main__':
    main()