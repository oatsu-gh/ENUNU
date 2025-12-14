#!/usr/bin/env python3
# Copyright (c) 2021-2025 oatsu
"""
light-the-torch を使って pytorch をインストールする。
"""

import subprocess


def ltt_install_torch(python_exe):
    """
    python -m pip install --upgrade light_the_torch
    python -m light_the_torch install --upgrade torch torchaudio torchvision
    """
    # Upgrade ltt
    command_1 = [
        python_exe,
        '-m',
        'pip',
        'install',
        '--upgrade',
        'light_the_torch',
        '--no-warn-script-location',
        '--disable-pip-version-check',
    ]
    subprocess.run(command_1, check=True)  # noqa: S603

    # Install PyTorch
    command_2 = [
        python_exe,
        '-m',
        'light_the_torch',
        'install',
        '--upgrade',
        'torch',
        'torchaudio',
        'torchvision',
        '--no-warn-script-location',
        '--disable-pip-version-check',
    ]
    subprocess.run(command_2, check=True)  # noqa: S603


def main():
    """
    インストールを実行する
    """
    import sys

    if input('インストールされているpytorchを上書きしてもいいですか？(YES/NO): ').upper() == 'YES':
        ltt_install_torch(sys.executable)


if __name__ == '__main__':
    main()
