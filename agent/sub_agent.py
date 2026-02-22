"""
Субагент GPT-4o для контроля, советов и анализа
"""
import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SubAgentConfig:
    """Конфигурация субагента"""
    api_key: str = ""
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    enabled: bool = True
    monitoring_frequency: int = 5  # секунды
    backup_enabled: bool = True
    backup_interval: int = 3600  # секунды
    max_context_length: int = 8000
    roles: List[str] = field(default_factory=lambda: [
        "control_tool_integration",
        "performance_monitoring",
        "mission_supervision",
        "learning_analysis",
        "safety_oversight",
        "report_generation",
        "advice_provision",
        "backup_management"
    ])


class SubAgent:
    """
    Субагент на базе GPT-4o для комплексного контроля системы.
    """
    
    def __init__(self, config: Dict[str, Any], main_agent=None):
        """
        Инициализация субагента.
        
        Args:
            config (Dict[str, Any]): Конфигурация субагента.
            main_agent: Ссылка на основной агент.
        """
        sub_agent_config = config.get('sub_agent', {})
        self.config = SubAgentConfig(**sub_agent_config)
        self.main_agent = main_agent
        
        # Инициализация OpenAI клиента
        self.openai_client = None
        if OPENAI_AVAILABLE and self.config.api_key:
            try:
                self.openai_client = AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url
                )
            except Exception as e:
                logger.error(f"Ошибка инициализации OpenAI клиента: {e}")
        
        # Система мониторинга
        self.monitoring_data = {}
        self.alerts = []
        self.recommendations = []
        
        # Система отчетности
        self.reports = []
        
        # Контекст диалога
        self.conversation_history = []
        self.max_history_length = 20
        
        # Статус
        self.status = "initializing"
        self.last_heartbeat = datetime.now()
        
        # Системный промпт
        self.system_prompt = self._create_system_prompt()
        
        logger.info("Субагент GPT-4o инициализирован")
    
    def _create_system_prompt(self) -> str:
        """Создание системного промпта"""
        agent_id = getattr(self.main_agent, 'agent_id', 'Неизвестно') if self.main_agent else 'Неизвестно'
        
        return f"""Ты - субагент (помощник) системы управления дроном COBA AI Drone Agent 2.

Твои основные обязанности:

1. КОНТРОЛЬ ИНТЕГРАЦИИ ИНСТРУМЕНТОВ:
- Мониторинг взаимодействия между инструментами
- Выявление конфликтов и проблем совместимости
- Оптимизация workflow между инструментами

2. МОНИТОРИНГ ПРОИЗВОДИТЕЛЬНОСТИ:
- Отслеживание всех параметров системы в реальном времени
- Выявление аномалий и отклонений
- Прогнозирование потенциальных проблем

3. КОНТРОЛЬ ВЫПОЛНЕНИЯ МИССИЙ:
- Слежение за выполнением инструкций миссии
- Анализ отклонений от плана
- Оценка эффективности выполнения
- Отслеживание обучения дрона

4. АНАЛИЗ ОБУЧЕНИЯ:
- Мониторинг процесса обучения
- Анализ прогресса и эффективности
- Рекомендации по улучшению моделей
- Выявление переобучения

5. КОНТРОЛЬ БЕЗОПАСНОСТИ:
- Мониторинг критических параметров
- Проверка соблюдения протоколов безопасности
- Анализ рисков

6. ГЕНЕРАЦИЯ ОТЧЕТОВ:
- Формирование детальных отчетов по миссиям
- Анализ производительности
- Рекомендации по улучшению

7. ПРЕДОСТАВЛЕНИЕ СОВЕТОВ:
- Консультации по использованию инструментов
- Рекомендации по настройке параметров
- Советы по планированию миссий

8. УПРАВЛЕНИЕ РЕЗЕРВНЫМИ КОПИЯМИ:
- Контроль системы бэкапов
- Верификация целостности копий
- Управление версиями

Важные правила:
- Всегда отвечай на русском языке
- Будь проактивным - предупреждай о проблемах до их возникновения
- Предлагай конкретные решения с пошаговыми инструкциями
- Обосновывай все рекомендации
- Следи за контекстом всей системы
- Сохраняй все важные данные в журнал

Текущий агент: {agent_id}
"""
    
    async def initialize(self):
        """Инициализация субагента"""
        try:
            # Проверка подключения к OpenAI
            if self.openai_client:
                await self._test_openai_connection()
            
            # Загрузка предыдущего состояния
            await self._load_previous_state()
            
            # Запуск фоновых задач
            asyncio.create_task(self._background_monitoring())
            
            self.status = "ready"
            logger.info("Субагент GPT-4o готов к работе")
        except Exception as e:
            logger.error(f"Ошибка инициализации субагента: {e}")
            self.status = "error"
    
    async def _test_openai_connection(self):
        """Тест подключения к OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logger.info("Подключение к OpenAI API успешно")
        except Exception as e:
            logger.error(f"Ошибка подключения к OpenAI: {e}")
            self.openai_client = None
    
    async def _load_previous_state(self):
        """Загрузка предыдущего состояния"""
        state_path = Path("data/state/sub_agent_state.json")
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    state = json.load(f)
                self.reports = state.get("reports", [])
                logger.info("Предыдущее состояние субагента загружено")
            except Exception as e:
                logger.error(f"Ошибка загрузки состояния: {e}")
    
    async def _background_monitoring(self):
        """Фоновый мониторинг системы"""
        while self.status == "ready":
            try:
                await self.monitor_system()
                await asyncio.sleep(self.config.monitoring_frequency)
            except Exception as e:
                logger.error(f"Ошибка фонового мониторинга: {e}")
                await asyncio.sleep(10)
    
    async def monitor_system(self) -> Dict[str, Any]:
        """
        Комплексный мониторинг системы.
        
        Returns:
            Dict[str, Any]: Результаты мониторинга.
        """
        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "alerts": [],
            "recommendations": [],
            "metrics": {}
        }
        
        try:
            # Мониторинг основного агента
            if self.main_agent:
                agent_status = await self.main_agent.get_status()
                monitoring_results["metrics"]["agent"] = agent_status
                
                # Проверка критических параметров
                telemetry = agent_status.get("telemetry", {})
                battery = telemetry.get("battery", 100)
                if battery < 25:
                    alert = {
                        "type": "low_battery",
                        "severity": "warning",
                        "message": f"Низкий заряд батареи: {battery}%",
                        "timestamp": datetime.now().isoformat()
                    }
                    monitoring_results["alerts"].append(alert)
                    self.alerts.append(alert)
                
                # Проверка инструментов
                tools_status = agent_status.get("tools_status", {})
                for tool_name, tool_status in tools_status.items():
                    if tool_status != "active" and tool_status != "ready":
                        alert = {
                            "type": "tool_issue",
                            "severity": "warning",
                            "message": f"Инструмент {tool_name} имеет статус: {tool_status}",
                            "timestamp": datetime.now().isoformat()
                        }
                        monitoring_results["alerts"].append(alert)
            
            self.monitoring_data = monitoring_results
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
            return monitoring_results
    
    async def review_decision(self, decision: Dict[str, Any], 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Рецензирование решения основного агента.
        
        Args:
            decision (Dict[str, Any]): Решение агента.
            context (Dict[str, Any]): Контекст.
            
        Returns:
            Dict[str, Any]: Рекомендации.
        """
        if not self.openai_client:
            return {"suggest_change": False}
        
        try:
            prompt = f"""
Проанализируй решение агента:

Решение: {json.dumps(decision, indent=2, ensure_ascii=False)}
Контекст: {json.dumps(context, indent=2, ensure_ascii=False)}

Оцени:
1. Безопасность решения
2. Эффективность
3. Соответствие миссии
4. Возможные риски

Ответ в формате JSON:
{{
    "suggest_change": true/false,
    "suggested_command": "команда если нужно изменить",
    "reason": "обоснование",
    "risk_level": "low/medium/high",
    "confidence": 0.95
}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Ошибка рецензирования решения: {e}")
            return {"suggest_change": False}
    
    async def notify_mission_start(self, mission: Any):
        """
        Уведомление о начале миссии.
        
        Args:
            mission: Миссия.
        """
        mission_data = mission.to_dict() if hasattr(mission, 'to_dict') else mission
        logger.info(f"Субагент: начало миссии {mission_data.get('name', 'Unknown')}")
        
        # Создание бэкапа перед миссией
        if self.config.backup_enabled and self.main_agent:
            await self.main_agent.save_state()
        
        # Анализ миссии
        if self.openai_client:
            try:
                prompt = f"""
Проанализируй миссию перед запуском:
{json.dumps(mission_data, indent=2, ensure_ascii=False)}

Проверь:
1. Полноту данных
2. Безопасность параметров
3. Эффективность маршрута
4. Потенциальные риски

Дай краткий анализ и рекомендации.
"""
                response = await self.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                
                analysis = response.choices[0].message.content
                logger.info(f"Анализ миссии: {analysis}")
                
            except Exception as e:
                logger.error(f"Ошибка анализа миссии: {e}")
    
    async def notify_mission_complete(self, report: Dict[str, Any]):
        """
        Уведомление о завершении миссии.
        
        Args:
            report (Dict[str, Any]): Отчет о миссии.
        """
        logger.info(f"Субагент: миссия завершена {report.get('mission_name', 'Unknown')}")
        
        # Сохранение отчета
        self.reports.append(report)
        
        # Генерация итогового отчета
        if self.openai_client:
            try:
                prompt = f"""
Сформируй итоговый отчет по миссии:
{json.dumps(report, indent=2, ensure_ascii=False)}

Включи:
1. Краткое описание выполнения
2. Ключевые события
3. Проблемы и их решение
4. Рекомендации по улучшению
5. Оценку эффективности (0-1)

Ответ в формате JSON.
"""
                response = await self.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800,
                    response_format={"type": "json_object"}
                )
                
                final_report = json.loads(response.choices[0].message.content)
                
                # Сохранение отчета
                report_path = f"data/reports/{report.get('mission_id', 'unknown')}_subagent.json"
                Path(report_path).parent.mkdir(parents=True, exist_ok=True)
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(final_report, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Итоговый отчет сохранен: {report_path}")
                
            except Exception as e:
                logger.error(f"Ошибка генерации отчета: {e}")
    
    async def notify_action(self, action: str, result: Dict[str, Any]):
        """
        Уведомление о выполнении действия.
        
        Args:
            action (str): Действие.
            result (Dict[str, Any]): Результат.
        """
        if not result.get("success", False):
            alert = {
                "type": "action_failed",
                "severity": "warning",
                "message": f"Действие {action} не выполнено: {result.get('error', 'Unknown error')}",
                "timestamp": datetime.now().isoformat()
            }
            self.alerts.append(alert)
    
    async def analyze_experience(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ опыта для обучения.
        
        Args:
            experience (Dict[str, Any]): Опыт.
            
        Returns:
            Dict[str, Any]: Уроки и рекомендации.
        """
        if not self.openai_client:
            return {"improvements": []}
        
        try:
            prompt = f"""
Проанализируй опыт и извлеки уроки:
{json.dumps(experience, indent=2, ensure_ascii=False)}

Определи:
1. Что сработало хорошо
2. Что можно улучшить
3. Новые паттерны
4. Конкретные рекомендации

Ответ в формате JSON.
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            lessons = json.loads(response.choices[0].message.content)
            return lessons
            
        except Exception as e:
            logger.error(f"Ошибка анализа опыта: {e}")
            return {"improvements": []}
    
    async def ask(self, question: str) -> str:
        """
        Задать вопрос субагенту.
        
        Args:
            question (str): Вопрос.
            
        Returns:
            str: Ответ.
        """
        if not self.openai_client:
            return "OpenAI API недоступен"
        
        try:
            # Добавление в историю
            self.conversation_history.append({"role": "user", "content": question})
            
            # Ограничение истории
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
            
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            response = await self.openai_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            # Добавление ответа в историю
            self.conversation_history.append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка запроса к субагенту: {e}")
            return f"Ошибка: {str(e)}"
    
    async def get_system_summary(self) -> Dict[str, Any]:
        """
        Получение сводки о состоянии системы.
        
        Returns:
            Dict[str, Any]: Сводка.
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "sub_agent_status": self.status,
            "monitoring_data": self.monitoring_data,
            "alerts_count": len(self.alerts),
            "recent_alerts": self.alerts[-5:] if self.alerts else [],
            "reports_count": len(self.reports)
        }
        
        if self.main_agent:
            summary["agent_status"] = await self.main_agent.get_status()
        
        return summary
    
    async def shutdown(self):
        """Корректное завершение работы субагента"""
        logger.info("Завершение работы субагента...")
        
        # Сохранение состояния
        state = {
            "reports": self.reports,
            "alerts": self.alerts,
            "timestamp": datetime.now().isoformat()
        }
        
        state_path = Path("data/state/sub_agent_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        self.status = "shutdown"
        logger.info("Субагент завершил работу")
