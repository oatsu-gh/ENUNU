.\python-3.8.10-embed-amd64\python.exe -m pip install --upgrade pip
.\python-3.8.10-embed-amd64\python.exe -m pip install --upgrade wheel
.\python-3.8.10-embed-amd64\python.exe -m pip install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio===0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
.\python-3.8.10-embed-amd64\python.exe -m pip install "hydra-core<1.1"

PAUSE
