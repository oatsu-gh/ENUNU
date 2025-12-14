@echo Re-installing Python packages. Please wait some minutes.

nvcc -V

@set python_exe=%~dp0\python-3.12.10-embed-amd64\python.exe
%python_exe% -m pip uninstall torch torchaudio torchvision --quiet -y

%python_exe% -m pip install --upgrade utaupy --no-warn-script-location --disable-pip-version-check
%python_exe% -m pip install --upgrade light_the_torch --quiet --no-warn-script-location --disable-pip-version-check
%python_exe% -m light_the_torch install torch torchaudio --no-warn-script-location --disable-pip-version-check

PAUSE
