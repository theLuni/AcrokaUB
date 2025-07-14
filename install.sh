#!/data/data/com.termux/files/usr/bin/bash

# Цвета
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
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

install() {
    # 1. Обновление пакетов
    echo -e "${YELLOW}[*] Обновление пакетов...${NC}"
    pkg update -y || {
        echo -e "${RED}[✗] Ошибка обновления пакетов${NC}"
        return 1
    }

    # 2. Установка зависимостей
    echo -e "${YELLOW}[*] Установка зависимостей...${NC}"
    pkg install -y git python python-pip tmux || {
        echo -e "${RED}[✗] Ошибка установки зависимостей${NC}"
        return 1
    }

    # 3. Клонирование репозитория
    echo -e "${YELLOW}[*] Клонирование репозитория...${NC}"
    if [ -d "AcrokaUB" ]; then
        cd AcrokaUB
        git pull || {
            echo -e "${RED}[✗] Ошибка обновления репозитория${NC}"
            return 1
        }
    else
        git clone https://github.com/theLuni/AcrokaUB.git || {
            echo -e "${RED}[✗] Ошибка клонирования репозитория${NC}"
            return 1
        }
        cd AcrokaUB || {
            echo -e "${RED}[✗] Не удалось перейти в директорию${NC}"
            return 1
        }
    fi

    # 4. Установка Python-зависимостей
    echo -e "${YELLOW}[*] Установка Python-зависимостей...${NC}"
    pip install -r dops.txt || {
        echo -e "${RED}[✗] Ошибка установки Python-зависимостей${NC}"
        return 1
    }

    # 5. Настройка хранилища
    echo -e "${YELLOW}[*] Настройка хранилища...${NC}"
    mkdir -p storage/{sessions,cache,logs}
    chmod -R 700 storage

    # 6. Настройка автозапуска
    echo -e "${YELLOW}[*] Настройка автозапуска...${NC}"
    
    # Команда для автозапуска
    AUTOSTART_CMD='clear && cd ~/AcrokaUB && python3 main.py'

    # Проверка, есть ли уже эта команда в ~/.bash_profile
    if ! grep -qF "$AUTOSTART_CMD" ~/.bash_profile; then
        echo "$AUTOSTART_CMD" >> ~/.bash_profile
        echo -e "${GREEN}[✓] Команда автозапуска добавлена в ~/.bash_profile.${NC}"
    else
        echo -e "${YELLOW}[i] Команда автозапуска уже добавлена в ~/.bash_profile.${NC}"
    fi

    return 0
}

main() {
    show_logo
    
    # Проверка интернет-соединения
    echo -e "${YELLOW}[*] Проверка интернет-соединения...${NC}"
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        echo -e "${RED}[✗] Нет интернет-соединения!${NC}"
        exit 1
    fi
    
    if install; then
        echo -e "\n${GREEN}[✓] Установка успешно завершена!${NC}"
        echo -e "${BLUE}"
        echo " Запуск бота..."
        clear
        cd ~/AcrokaUB
        python3 main.py
    else
        echo -e "\n${RED}[✗] Установка не удалась${NC}"
        exit 1
    fi
}

main
