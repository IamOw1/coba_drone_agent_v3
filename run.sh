#!/bin/bash
# 🚁 COBA AI Drone Agent 2.0 - Скрипт быстрого запуска
# Используйте: ./run.sh [mode] [options]

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Показать справку
show_help() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🚁 COBA AI Drone Agent 2.0 - Быстрый запуск${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Использование:${NC}"
    echo "  ./run.sh [mode] [options]"
    echo ""
    echo -e "${YELLOW}Режимы (mode):${NC}"
    echo "  check      Проверка целостности системы"
    echo "  demo       Интерактивная демонстрация"
    echo "  agent      Запуск только агента"
    echo "  api        Запуск API сервера (по умолчанию на порту 8000)"
    echo "  dashboard  Запуск веб-дашборда (по умолчанию на порту 8501)"
    echo "  all        Запуск всего (агент + API + дашборд)"
    echo "  help       Показать эту справку"
    echo ""
    echo -e "${YELLOW}Примеры:${NC}"
    echo "  ./run.sh check              # Проверить систему"
    echo "  ./run.sh demo               # Запустить демонстрацию"
    echo "  ./run.sh agent              # Запустить агента"
    echo "  ./run.sh api --port 9000    # API на порту 9000"
    echo "  ./run.sh dashboard          # Запустить дашборд"
    echo "  ./run.sh all                # Все сразу"
    echo ""
}

# Проверка что Python установлен
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 не найден!${NC}"
        echo "Установите Python 3.8+ и попробуйте снова"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"
}

# Проверка что зависимости установлены
check_dependencies() {
    echo -e "${BLUE}Проверка зависимостей...${NC}"
    python3 -c "import yaml" 2>/dev/null || {
        echo -e "${RED}✗ pyyaml не установлен${NC}"
        echo "Установите зависимости: pip install -r requirements.txt"
        exit 1
    }
    python3 -c "import fastapi" 2>/dev/null || {
        echo -e "${RED}✗ fastapi не установлен${NC}"
        echo "Установите зависимости: pip install -r requirements.txt"
        exit 1
    }
    echo -e "${GREEN}✓ Зависимости установлены${NC}"
}

# Основной скрипт
main() {
    MODE=${1:-help}
    shift || true  # Оставшиеся аргументы для передачи в Python
    
    case "$MODE" in
        check)
            echo -e "${BLUE}Проверка целостности системы...${NC}"
            python3 check_system.py
            ;;
        demo)
            echo -e "${BLUE}Запуск интерактивной демонстрации...${NC}"
            python3 demo.py
            ;;
        agent)
            check_python
            check_dependencies
            echo -e "${GREEN}🚁 Запуск агента...${NC}"
            python3 main.py agent
            ;;
        api)
            check_python
            check_dependencies
            echo -e "${GREEN}🚁 Запуск API сервера...${NC}"
            python3 main.py api "$@"
            ;;
        dashboard)
            check_python
            check_dependencies
            echo -e "${GREEN}🚁 Запуск дашборда...${NC}"
            python3 main.py dashboard
            ;;
        all)
            check_python
            check_dependencies
            echo -e "${GREEN}🚁 Запуск всех компонентов...${NC}"
            python3 main.py all
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}✗ Неизвестный режим: $MODE${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
