#!/data/data/com.termux/files/usr/bin/bash

# Установка
pkg update -y
pkg install git python -y
git clone https://github.com/theLuni/AcrokaUB.git
cd AcrokaUB
pip install -r dops.txt

# Настройка автозагрузки
mkdir -p ~/.termux/boot
echo '#!/data/data/com.termux/files/usr/bin/bash
cd ~/AcrokaUB
python3 main.py' > ~/.termux/boot/run_acrokadb
chmod +x ~/.termux/boot/run_acrokadb

# Первый запуск
clear
python3 main.py