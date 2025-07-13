#!/data/data/com.termux/files/usr/bin/bash

# Цвета для вывода
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

# ASCII-арт логотипа
show_logo() {
    clear
    echo -e "${BLUE}"
    echo -e "   █████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ █████╗ "
    echo -e "  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗"
    echo -e "  ███████║██║     ██████╔╝██║   ██║█████╔╝ ███████║"
    echo -e "  ██╔══██║██║     ██╔══██╗██║   ██║██╔═██╗ ██╔══██║"
    echo -e "  ██║  ██║╚██████╗██║  ██║╚██████╔╝██║  ██╗██║  ██║"
    echo -e "  ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${GREEN}          Установщик Acroka UserBot${NC}"
    echo -e "${YELLOW}--------------------------------------------${NC}"
    echo
}

# Проверка интернета
check_internet() {
    echo -e "${YELLOW}[*] Проверка интернет-соединения...${NC}"
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        echo -e "${RED}[✗] Ошибка: нет интернет-соединения!${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓] Интернет доступен${NC}"
}

# Установка пакетов
install_packages() {
    echo -e "\n${YELLOW}[*] Обновление пакетов...${NC}"
    pkg update -y && \
    echo -e "${YELLOW}[*] Установка зависимостей...${NC}" && \
    pkg install -y git python python-pip tmux || {
        echo -e "${RED}[✗] Ошибка установки пакетов!${NC}"
        exit 1
    }
    echo -e "${GREEN}[✓] Пакеты успешно установлены${NC}"
}

# Клонирование репозитория
clone_repo() {
    echo -e "\n${YELLOW}[*] Клонирование репозитория...${NC}"
    if [ -d "AcrokaUB" ]; then
        echo -e "${BLUE}[i] Директория AcrokaUB уже существует, обновляю...${NC}"
        cd AcrokaUB
        git pull || {
            echo -e "${RED}[✗] Ошибка при обновлении репозитория!${NC}"
            exit 1
        }
    else
        git clone https://github.com/theLuni/AcrokaUB.git || {
            echo -e "${RED}[✗] Ошибка клонирования репозитория!${NC}"
            exit 1
        }
        cd AcrokaUB
    fi
    echo -e "${GREEN}[✓] Репозиторий успешно склонирован/обновлён${NC}"
}

# Установка зависимостей Python
install_python_deps() {
    echo -e "\n${YELLOW}[*] Установка Python-зависимостей...${NC}"
    pip install -r requirements.txt || {
        echo -e "${RED}[✗] Ошибка установки зависимостей!${NC}"
        exit 1
    }
    echo -e "${GREEN}[✓] Зависимости успешно установлены${NC}"
}

# Настройка хранилища
setup_storage() {
    echo -e "\n${YELLOW}[*] Настройка хранилища...${NC}"
    mkdir -p storage/{sessions,cache,logs}
    chmod -R 777 storage
    echo -e "${GREEN}[✓] Хранилище настроено${NC}"
}

# Настройка автозапуска
setup_autostart() {
    echo -e "\n${YELLOW}[*] Настройка автозапуска...${NC}"
    
    # Способ 1: через termux-boot
    mkdir -p ~/.termux/boot
    cat > ~/.termux/boot/run_acrokadb <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/AcrokaUB
while true; do
    python3 main.py
    sleep 10
done
EOF
    chmod +x ~/.termux/boot/run_acrokadb
    
    echo -e "${GREEN}[✓] Автозапуск через termux-boot настроен${NC}"
}

# Завершение установки
finish_installation() {
    echo -e "\n${YELLOW}--------------------------------------------${NC}"
    echo -e "${GREEN}[✓] Установка успешно завершена!${NC}"
    echo -e "${BLUE}"
    echo -e "  Для запуска бота:"
    echo -e "  1. Закройте и снова откройте Termux"
    echo -e "  2. Или вручную: ${NC}cd ~/AcrokaUB && python3 main.py"
    echo -e "${BLUE}"
    echo -e "  Для остановки: ${NC}pkill
