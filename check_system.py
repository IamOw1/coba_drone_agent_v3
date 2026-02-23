#!/usr/bin/env python3
"""
Финальная проверка целостности проекта COBA AI Drone Agent 2.0
"""
import sys
import asyncio
from pathlib import Path

# Добавление пути к проекту
sys.path.insert(0, str(Path(__file__).parent))


def check_imports() -> bool:
    """Проверка импортов основных модулей"""
    print("=" * 60)
    print("🔍 Проверка импортов модулей...")
    print("=" * 60)
    
    imports_to_check = [
        ("agent.core", "DroneIntelligentAgent"),
        ("agent.memory", "ShortTermMemory"),
        ("agent.decision_maker", "DecisionMaker"),
        ("agent.learner", "Learner"),
        ("agent.sub_agent", "SubAgent"),
        ("sim.airsim_client", "AirSimClient"),
        ("hardware.mavlink_handler", "MAVLinkHandler"),
        ("tools.base_tool", "BaseTool"),
        ("api.rest_api", "create_app"),
        ("utils.logger", "setup_logger"),
    ]
    
    failed = []
    for module_name, class_name in imports_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {module_name}.{class_name}")
        except Exception as e:
            print(f"✗ {module_name}.{class_name} - {e}")
            failed.append((module_name, class_name))
    
    if not failed:
        print("\n✓ Все импорты успешны!")
        return True
    else:
        print(f"\n✗ Ошибка: {len(failed)} модулей не загружено")
        return False


def check_directories() -> bool:
    """Проверка структуры директорий"""
    print("\n" + "=" * 60)
    print("📁 Проверка структуры директорий...")
    print("=" * 60)
    
    required_dirs = [
        "agent",
        "api",
        "config",
        "dashboard",
        "sim",
        "hardware",
        "tools",
        "utils",
        "tests",
        "data",
        "data/models",
        "data/state",
        "data/reports",
        "data/memory",
        "data/missions",
        "web_interface"
    ]
    
    failed = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path}")
            failed.append(dir_path)
    
    if not failed:
        print("\n✓ Все директории на месте!")
        return True
    else:
        print(f"\n⚠️  Отсутствует {len(failed)} директорий")
        return False


def check_config() -> bool:
    """Проверка конфигурации"""
    print("\n" + "=" * 60)
    print("⚙️  Проверка конфигурации...")
    print("=" * 60)
    
    try:
        import yaml
        
        config_path = Path("config/config.yaml")
        if not config_path.exists():
            print("✗ config/config.yaml не найден")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        required_keys = ["agent_id", "simulation", "safety", "learning", "tools"]
        for key in required_keys:
            if key in config:
                print(f"✓ {key}")
            else:
                print(f"✗ {key}")
        
        print("\n✓ Конфигурация загружена!")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка конфигурации: {e}")
        return False


def check_tools() -> bool:
    """Проверка инструментов"""
    print("\n" + "=" * 60)
    print("🛠️  Проверка инструментов...")
    print("=" * 60)
    
    try:
        from tools.geospatial_mapping import GeoMapTool
        from tools.mifly import MiFlyTool
        from tools.slom import SlomTool
        from tools.amorfus import AmorfusTool
        from tools.object_detection import ObjectDetectionTool
        from tools.precision_landing import PrecisionLandingTool
        from tools.autonomous_flight import AutonomousFlightTool
        from tools.mission_planner_tool import MissionPlannerTool
        from tools.deployment_manager import DeploymentManagerTool
        from tools.logistics import LogisticsTool
        
        tools = [
            ("GeoMapTool", GeoMapTool),
            ("MiFlyTool", MiFlyTool),
            ("SlomTool", SlomTool),
            ("AmorfusTool", AmorfusTool),
            ("ObjectDetectionTool", ObjectDetectionTool),
            ("PrecisionLandingTool", PrecisionLandingTool),
            ("AutonomousFlightTool", AutonomousFlightTool),
            ("MissionPlannerTool", MissionPlannerTool),
            ("DeploymentManagerTool", DeploymentManagerTool),
            ("LogisticsTool", LogisticsTool),
        ]
        
        for tool_name, tool_class in tools:
            print(f"✓ {tool_name}")
        
        print(f"\n✓ Все инструменты загружены! ({len(tools)} всего)")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка загрузки инструментов: {e}")
        return False


async def check_agent_initialization() -> bool:
    """Проверка инициализации агента"""
    print("\n" + "=" * 60)
    print("🤖 Проверка инициализации агента...")
    print("=" * 60)
    
    try:
        from agent.core import DroneIntelligentAgent
        
        agent = DroneIntelligentAgent("config/config.yaml")
        print(f"✓ Агент создан (ID: {agent.agent_id})")
        print(f"✓ Состояние: {agent.state.value}")
        print(f"✓ Режим: {'Симуляция' if agent.sim_mode else 'Реальный дрон'}")
        print(f"✓ Инструментов загружено: {len(agent.tools)}")
        
        print("\n✓ Агент инициализирован!")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка инициализации агента: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║  🚁 COBA AI Drone Agent 2.0 - Финальная проверка  ║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = {}
    
    # Проверка директорий
    results["directories"] = check_directories()
    
    # Проверка конфигурации
    results["config"] = check_config()
    
    # Проверка импортов
    results["imports"] = check_imports()
    
    # Проверка инструментов
    results["tools"] = check_tools()
    
    # Проверка инициализации агента
    try:
        results["agent"] = asyncio.run(check_agent_initialization())
    except Exception as e:
        print(f"\n✗ Ошибка при проверке агента: {e}")
        results["agent"] = False
    
    # Итоговая информация
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ПРОВЕРКИ")
    print("=" * 60)
    
    checks = [
        ("Директории", results.get("directories", False)),
        ("Конфигурация", results.get("config", False)),
        ("Импорты модулей", results.get("imports", False)),
        ("Инструменты", results.get("tools", False)),
        ("Инициализация агента", results.get("agent", False)),
    ]
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print("\n" + "=" * 60)
    print(f"Результат: {passed}/{total} проверок пройдено")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система готова к работе!")
        print("\nДля запуска используйте:")
        print("  - Агент: python main.py")
        print("  - API сервер: python main.py --api")
        print("  - Дашборд: streamlit run dashboard/app.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} проверок не пройдено")
        print("Проверьте ошибки выше и исправьте их.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
