#!/usr/bin/env python3
# Copyright (c) 2021-2025 oatsu
"""
light-the-torch を使って pytorch をインストールする。
"""


def ltt_install_torch():
    """
    python -m light_the_torch install torch torchaudio torchvision
    """
    import pip
    import light_the_torch as ltt

    # upgrade ltt
    pip.main(
        [
            "install",
            "--upgrade",
            "light-the-torch",
            "--no-warn-script-location",
            "--disable-pip-version-check",
        ]
    )
    # Install pytorch
    ltt.main(
        [
            "install",
            "--upgrade",
            "torch",
            "torchaudio",
            "torchvision",
            "--no-warn-script-location",
            "--disable-pip-version-check",
        ]
    )


def main():
    """
    インストールを実行する
    """
    if (
        input(
            "インストールされているpytorchを上書きしてもいいですか？(YES/NO): "
        ).upper()
        == "YES"
    ):
        ltt_install_torch()


if __name__ == "__main__":
    main()
