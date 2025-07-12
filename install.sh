#!/data/data/com.termux/files/usr/bin/bash

# Обновляем репозитории (если нужно — меняем зеркало)
termux-change-repo <<< "1
1
Y
"

# Устанавливаем пакеты (с проверкой ошибок)
pkg update -y && pkg install -y git python || {
    echo "⚠ Ошибка установки пакетов! Попробуй вручную:"
    echo "pkg update -y && pkg install -y git python"
    exit 1
}

# Клонируем репозиторий
git clone https://github.com/theLuni/AcrokaUB.git || {
    echo "⚠ Ошибка клонирования! Проверь ссылку или интернет."
    exit 1
}

# Устанавливаем зависимости Python
cd AcrokaUB
if [ -f "dops.txt" ]; then
    pip install -r dops.txt || {
        echo "⚠ Ошибка установки зависимостей Python!"
        exit 1
    }
else
    echo "⚠ Файл dops.txt не найден!"
    exit 1
fi

# Настраиваем автозагрузку
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/run_acrokadb << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/AcrokaUB
python3 main.py
EOF
chmod +x ~/.termux/boot/run_acrokadb

# Запускаем

clear
python3 main.py
