#!/data/data/com.termux/files/usr/bin/bash

# Принудительно выбираем рабочее зеркало (Grimler или BFSU)
echo -e "1\n2\nY\n" | termux-change-repo >/dev/null 2>&1 || {
    echo "⚠ Не удалось сменить репозиторий! Попробуй вручную:"
    echo "termux-change-repo"
    exit 1
}

# Устанавливаем пакеты (с повтором при ошибке)
for i in {1..3}; do
    pkg update -y && pkg install -y git python && break
    echo "⚠ Попытка $i/3 не удалась. Повторяем через 5 сек..."
    sleep 5
done || {
    echo "❌ Ошибка установки пакетов! Попробуй вручную:"
    echo "pkg update -y && pkg install -y git python"
    exit 1
}

# Клонируем репозиторий
git clone https://github.com/theLuni/AcrokaUB.git || {
    echo "❌ Ошибка клонирования! Проверь ссылку или интернет."
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
    echo "❌ Файл dops.txt не найден!"
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
