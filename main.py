#!/usr/bin/env python3
"""
COBA AI Drone Agent 2.0 - Главный файл запуска
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Добавление пути к проекту
sys.path.insert(0, str(Path(__file__).parent))

from agent.core import DroneIntelligentAgent
from api.rest_api import create_app
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def run_agent_only(config_path: str = "config/config.yaml"):
    """
    Запуск только агента без API.
    
    Args:
        config_path (str): Путь к конфигурации.
    """
    logger.info("Запуск COBA AI Drone Agent 2.0...")
    
    # Создание агента
    agent = DroneIntelligentAgent(config_path)
    
    # Инициализация
    success = await agent.initialize()
    
    if not success:
        logger.error("Ошибка инициализации агента")
        return
    
    logger.info("Агент успешно инициализирован")
    
    # Интерактивный режим
    try:
        while True:
            print("\n" + "="*50)
            print("Команды:")
            print("  1. Статус")
            print("  2. Телеметрия")
            print("  3. Команда")
            print("  4. Миссия")
            print("  5. Субагент")
            print("  6. Выход")
            print("="*50)
            
            choice = input("\nВыберите действие (1-6): ").strip()
            
            if choice == "1":
                status = await agent.get_status()
                print(f"\nСтатус агента:")
                print(f"  ID: {status['agent_id']}")
                print(f"  Состояние: {status['state']}")
                print(f"  Миссия: {status['mission']['name'] if status['mission'] else 'Нет'}")
            
            elif choice == "2":
                telemetry = await agent.perceive()
                print(f"\nТелеметрия:")
                print(f"  Позиция: {telemetry.get('telemetry', {}).get('position', {})}")
                print(f"  Батарея: {telemetry.get('telemetry', {}).get('battery', 0):.1f}%")
            
            elif choice == "3":
                command = input("Введите команду (взлет/посадка/rtl/зависни): ").strip()
                result = await agent.process_command(command)
                print(f"Результат: {result}")
            
            elif choice == "4":
                from agent.core import MissionParams
                
                name = input("Название миссии: ").strip()
                waypoints = []
                
                print("Введите точки маршрута (пустая строка для завершения):")
                while True:
                    wp_input = input("Точка (x,y,z): ").strip()
                    if not wp_input:
                        break
                    try:
                        x, y, z = map(float, wp_input.split(","))
                        waypoints.append({"x": x, "y": y, "z": z})
                    except:
                        print("Неверный формат. Используйте: x,y,z")
                
                if waypoints:
                    mission = MissionParams(
                        name=name,
                        mission_id=f"mission_{asyncio.get_event_loop().time()}",
                        waypoints=waypoints
                    )
                    await agent.run_mission(mission)
                else:
                    print("Нет точек маршрута")
            
            elif choice == "5":
                if agent.sub_agent:
                    question = input("Вопрос субагенту: ").strip()
                    answer = await agent.sub_agent.ask(question)
                    print(f"\nОтвет: {answer}")
                else:
                    print("Субагент не инициализирован")
            
            elif choice == "6":
                break
            
            else:
                print("Неверный выбор")
    
    except KeyboardInterrupt:
        print("\nПрерывание...")
    
    finally:
        await agent.shutdown()
        logger.info("Агент завершил работу")


async def run_api_server(config_path: str = "config/config.yaml", 
                         host: str = "0.0.0.0", 
                         port: int = 8000):
    """
    Запуск API сервера.
    
    Args:
        config_path (str): Путь к конфигурации.
        host (str): Хост для прослушивания.
        port (int): Порт для прослушивания.
    """
    import uvicorn
    
    logger.info("Запуск API сервера...")
    
    # Создание агента
    agent = DroneIntelligentAgent(config_path)
    
    # Создание приложения
    app = create_app(agent)
    
    # Запуск сервера
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info(f"API сервер запущен на http://{host}:{port}")
    
    await server.serve()


def run_dashboard():
    """Запуск дашборда Streamlit"""
    import subprocess
    
    logger.info("Запуск дашборда...")
    
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    
    subprocess.run([
        "streamlit", "run", str(dashboard_path),
        "--server.port", "8501",
        "--server.headless", "true"
    ])


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="COBA AI Drone Agent 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s agent                    # Запуск только агента
  %(prog)s api                      # Запуск API сервера
  %(prog)s api --host 0.0.0.0 --port 8080
  %(prog)s dashboard                # Запуск дашборда
  %(prog)s all                      # Запуск всего
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["agent", "api", "dashboard", "all"],
        help="Режим запуска"
    )
    
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Путь к файлу конфигурации"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Хост для API сервера"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Порт для API сервера"
    )
    
    args = parser.parse_args()
    
    if args.mode == "agent":
        asyncio.run(run_agent_only(args.config))
    
    elif args.mode == "api":
        asyncio.run(run_api_server(args.config, args.host, args.port))
    
    elif args.mode == "dashboard":
        run_dashboard()
    
    elif args.mode == "all":
        # Запуск API и дашборда
        import threading
        
        # API в отдельном потоке
        api_thread = threading.Thread(
            target=lambda: asyncio.run(run_api_server(args.config, args.host, args.port))
        )
        api_thread.daemon = True
        api_thread.start()
        
        # Дашборд в основном потоке
        run_dashboard()


if __name__ == "__main__":
    main()
