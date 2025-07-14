#!/bin/bash

# Функция для вывода сообщения об ошибке и завершения
error_exit() {
    echo "❌ Ошибка: $1"
    exit 1
}

# Проверка соединения с интернетом
check_internet() {
    echo "🔍 Проверка интернет-соединения..."
    if ! ping -c 1 google.com >/dev/null 2>&1; then
        error_exit "Проблема с интернетом! Пожалуйста, проверьте соединение."
    fi
    echo "✅ Интернет-соединение активно"
}

# Установка пакетов
install_packages() {
    echo "🛠 Установка необходимых пакетов..."
    for i in {1..3}; do
        if apt update -y && apt install -y git python3 python3-pip; then
            echo "✅ Пакеты успешно установлены"
            return 0
        fi
        echo "⚠ Попытка $i/3 не удалась. Повторяем через 5 сек..."
        sleep 5
    done
    error_exit "Не удалось установить пакеты! Попробуйте вручную: apt update -y && apt install -y git python3 python3-pip"
}

# Клонирование репозитория
clone_repo() {
    echo "📥 Клонирование репозитория..."
    if [ -d "AcrokaUB" ]; then
        echo "⚠ Папка AcrokaUB уже существует. Пропускаем клонирование."
        return 0
    fi
    
    if git clone https://github.com/theLuni/AcrokaUB.git; then
        echo "✅ Репозиторий успешно клонирован"
        return 0
    fi
    error_exit "Ошибка клонирования! Проверьте ссылку или интернет."
}

# Установка зависимостей Python
install_dependencies() {
    echo "🐍 Установка Python-зависимостей..."
    cd AcrokaUB || error_exit "Не удалось перейти в папку AcrokaUB"
    
    if [ ! -f "dops.txt" ]; then
        error_exit "Файл зависимостей dops.txt не найден!"
    fi
    
    if pip3 install -r dops.txt; then
        echo "✅ Зависимости успешно установлены"
        return 0
    fi
    error_exit "Ошибка установки зависимостей Python!"
}

# Основной скрипт
main() {
    check_internet
    install_packages
    clone_repo
    install_dependencies
    
    # Запуск приложения
    clear
    echo "🚀 Запуск приложения..."
    python3 main.py || error_exit "Не удалось запустить main.py"
}

# Вызов основной функции
main
