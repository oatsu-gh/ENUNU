@REM ENUNU Portable Train Kit 用の環境構築バッチファイル
@REM CUDA 10.2 環境向け

pip install --upgrade pip
pip install wheel
pip install numpy cython
pip install hydra-core<1.1
pip install tqdm pydub pyyaml natsort
pip install --upgrade utaupy
pip install --upgrade nnmnkwii
pip install torch==1.9.1+cu102 torchvision==0.10.1+cu102 torchaudio===0.9.1 -f https://download.pytorch.org/whl/torch_stable.html

git clone "https://github.com/r9y9/nnsvs"
pip install ./nnsvs
