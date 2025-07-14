#!/data/data/com.termux/files/usr/bin/bash

# Цвета
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

show_logo() {
    clear
    echo -e "${BLUE}"
    echo "   █████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ █████╗ "
    echo "  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗"
    echo "  ███████║██║     ██████╔╝██║   ██║█████╔╝ ███████║"
    echo "  ██╔══██║██║     ██╔══██╗██║   ██║██╔═██╗ ██╔══██║"
    echo "  ██║  ██║╚██████╗██║  ██║╚██████╔╝██║  ██╗██║  ██║"
    echo "  ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${GREEN}          Установщик Acroka UserBot${NC}"
    echo -e "${YELLOW}--------------------------------------------${NC}"
    echo
}

check_internet() {
    echo -e "${YELLOW}[*] Проверка интернет-соединения...${NC}"
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        echo -e "${RED}[✗] Нет интернет-соединения!${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓] Интернет подключен${NC}"
}

install_packages() {
    echo -e "${YELLOW}[*] Установка необходимых пакетов...${NC}"
    pkg update -y && pkg install -y git python python-pip tmux || {
        echo -e "${RED}[✗] Ошибка при установке пакетов${NC}"
        exit 1
    }
    echo -e "${GREEN}[✓] Пакеты успешно установлены${NC}"
}

clone_repo() {
    echo -e "${YELLOW}[*] Клонирование репозитория AcrokaUB...${NC}"
    if [ -d "AcrokaUB" ]; then
        cd AcrokaUB
        git pull || {
            echo -e "${RED}[✗] Ошибка при обновлении репозитория${NC}"
            exit 1
        }
    else
        git clone https://github.com/theLuni/AcrokaUB.git || {
            echo -e "${RED}[✗] Ошибка при клонировании${NC}"
            exit 1
        }
        cd AcrokaUB || exit 1
    fi
    echo -e "${GREEN}[✓] Репозиторий готов${NC}"
}

install_dependencies() {
    echo -e "${YELLOW}[*] Установка Python-зависимостей...${NC}"
    pip install -r dops.txt || {
        echo -e "${RED}[✗] Ошибка при установке зависимостей${NC}"
        exit 1
    }
    echo -e "${GREEN}[✓] Зависимости установлены${NC}"
}

setup_autostart() {
    echo -e "${YELLOW}[*] Настройка автозапуска...${NC}"
    
    # Создаем start.sh
    cat > ~/AcrokaUB/start.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Цвета
BLUE='\033[1;34m'
GREEN='\033[1;32m'
NC='\033[0m'

clear
echo -e "${BLUE}"
cat << "EOF2"
   █████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ █████╗
  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗
  ███████║██║     ██████╔╝██║   ██║█████╔╝ ███████║
  ██╔══██║██║     ██╔══██╗██║   ██║██╔═██╗ ██╔══██║
  ██║  ██║╚██████╗██║  ██║╚██████╔╝██║  ██╗██║  ██║
  ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
EOF2
echo -e "${NC}"
echo -e "${GREEN}          Acroka UserBot запускается...${NC}"
echo

cd ~/AcrokaUB
python3 main.py
EOF

    chmod +x ~/AcrokaUB/start.sh

    # Добавляем автозапуск
    if ! grep -q "~/AcrokaUB/start.sh" ~/.bashrc; then
        echo -e "\n# Запуск AcrokaUB\n~/AcrokaUB/start.sh" >> ~/.bashrc
    fi
    echo -e "${GREEN}[✓] Автозапуск настроен${NC}"
}

success_message() {
    clear
    echo -e "${GREEN}"
    echo "Установка завершена успешно!"
    echo -e "${NC}"
    echo "Для запуска бота:"
    echo "1. Перезапустите Termux"
    echo "2. Бот запустится автоматически"
    echo -e "\nНажмите Enter для выхода..."
    read -n 1 -s
    exit 0
}

main() {
    show_logo
    check_internet
    install_packages
    clone_repo
    install_dependencies
    setup_autostart
    success_message
}

main
