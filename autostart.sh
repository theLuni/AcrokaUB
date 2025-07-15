#!/bin/bash

# Цвета
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
CYAN='\033[1;36m'
NC='\033[0m'

setup_autostart() {
    echo -e "${YELLOW}[*] Настройка автозапуска...${NC}"

    # Создаем start.sh
    cat > ~/AcrokaUB/start.sh << 'EOF'
#!/bin/bash

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
    echo "1. Перезапустите ваш терминал"
    echo "2. Бот запустится автоматически"
    echo -e "\nНажмите Enter для выхода..."
    read -n 1 -s
    exit 0
}

main() {
    setup_autostart
    success_message
}

main