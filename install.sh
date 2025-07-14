#!/data/data/com.termux/files/usr/bin/bash

# Цвета
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

# Анимация
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

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
    echo -e "${GREEN}[✓] Интернет-соединение активно${NC}"
}

install_packages() {
    echo -e "${YELLOW}[*] Обновление пакетов...${NC}"
    pkg update -y & spinner $!
    if [ $? -ne 0 ]; then
        echo -e "\r${RED}[✗] Ошибка обновления пакетов${NC}"
        return 1
    fi
    echo -e "\r${GREEN}[✓] Пакеты успешно обновлены${NC}"

    echo -e "${YELLOW}[*] Установка зависимостей...${NC}"
    pkg install -y git python python-pip tmux & spinner $!
    if [ $? -ne 0 ]; then
        echo -e "\r${RED}[✗] Ошибка установки зависимостей${NC}"
        return 1
    fi
    echo -e "\r${GREEN}[✓] Зависимости успешно установлены${NC}"
}

clone_repo() {
    echo -e "${YELLOW}[*] Клонирование репозитория...${NC}"
    if [ -d "AcrokaUB" ]; then
        cd AcrokaUB
        git pull & spinner $!
        if [ $? -ne 0 ]; then
            echo -e "\r${RED}[✗] Ошибка обновления репозитория${NC}"
            return 1
        fi
        echo -e "\r${GREEN}[✓] Репозиторий успешно обновлен${NC}"
    else
        git clone https://github.com/theLuni/AcrokaUB.git & spinner $!
        if [ $? -ne 0 ]; then
            echo -e "\r${RED}[✗] Ошибка клонирования репозитория${NC}"
            return 1
        fi
        cd AcrokaUB || {
            echo -e "${RED}[✗] Не удалось перейти в директорию${NC}"
            return 1
        }
        echo -e "\r${GREEN}[✓] Репозиторий успешно клонирован${NC}"
    fi
}

install_dependencies() {
    echo -e "${YELLOW}[*] Установка Python-зависимостей...${NC}"
    pip install -r dops.txt & spinner $!
    if [ $? -ne 0 ]; then
        echo -e "\r${RED}[✗] Ошибка установки Python-зависимостей${NC}"
        return 1
    fi
    echo -e "\r${GREEN}[✓] Python-зависимости успешно установлены${NC}"
}

setup_storage() {
    echo -e "${YELLOW}[*] Настройка хранилища...${NC}"
    mkdir -p storage/{sessions,cache,logs} &> /dev/null
    chmod -R 700 storage &> /dev/null
    echo -e "${GREEN}[✓] Хранилище настроено${NC}"
}

setup_autostart() {
    echo -e "${YELLOW}[*] Настройка автозапуска...${NC}"
    AUTOSTART_CMD='cd ~/AcrokaUB && ./start.sh'
    
    if ! grep -qF "$AUTOSTART_CMD" ~/.bash_profile; then
        echo "$AUTOSTART_CMD" >> ~/.bash_profile
        echo -e "${GREEN}[✓] Автозапуск через start.sh настроен${NC}"
    else
        echo -e "${CYAN}[i] Автозапуск уже настроен${NC}"
    fi
}

success_message() {
    clear
    echo -e "${BLUE}"
    echo "   █████╗  ██████╗██████╗  ██████╗ ██╗  ██╗ █████╗ "
    echo "  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗"
    echo "  ███████║██║     ██████╔╝██║   ██║█████╔╝ ███████║"
    echo "  ██╔══██║██║     ██╔══██╗██║   ██║██╔═██╗ ██╔══██║"
    echo "  ██║  ██║╚██████╗██║  ██║╚██████╔╝██║  ██╗██║  ██║"
    echo "  ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${GREEN}          Установка успешно завершена!${NC}"
    echo -e "${YELLOW}--------------------------------------------${NC}"
    echo
    echo -e "${CYAN}Для запуска бота:${NC}"
    echo -e "1. Закройте Termux"
    echo -e "2. Откройте Termux снова"
    echo -e "3. Бот запустится автоматически"
    echo
    read -p "Нажмите Enter, чтобы закрыть Termux..."
    exit 0
}

main() {
    show_logo
    check_internet
    install_packages || exit 1
    clone_repo || exit 1
    install_dependencies || exit 1
    setup_storage
    setup_autostart
    success_message
}

main
