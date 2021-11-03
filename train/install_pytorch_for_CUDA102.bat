.\python-3.8.10-embed-amd64\python.exe -m pip install --upgrade pip
.\python-3.8.10-embed-amd64\python.exe -m pip install --upgrade wheel
.\python-3.8.10-embed-amd64\python.exe -m pip install torch==1.10.0+cu102 torchvision==0.11.1+cu102 torchaudio===0.10.0+cu102 -f https://download.pytorch.org/whl/cu102/torch_stable.html
.\python-3.8.10-embed-amd64\python.exe -m pip install "hydra-core<1.1"

PAUSE
