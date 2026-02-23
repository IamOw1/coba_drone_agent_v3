"""
Модули мониторинга и аналитики для COBA AI Drone Agent
Включает: Обнаружение аномалий, оптимизацию энергопотребления, метрики системы
"""

import asyncio
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class AnomalyThresholds:
    """Пороги для обнаружения аномалий"""
    battery_drop_rate: float = 0.5  # % в минуту
    altitude_sudden_drop: float = 5.0  # метров
    speed_spike: float = 15.0  # % от нормального
    temperature_spike: float = 15.0  # градусов Цельсия
    signal_loss_duration: float = 5.0  # секунд
    wind_gust_threshold: float = 10.0  # м/с
    vibration_threshold: float = 0.3  # m/s^2
    cpu_usage_critical: float = 90.0  # %


@dataclass
class EnergyOptimazationConfig:
    """Конфигурация для оптимизации энергопотребления"""
    target_efficiency: float = 0.85  # 85%
    speed_optimization_enabled: bool = True
    altitude_optimization_enabled: bool = True
    route_optimization_enabled: bool = True
    wind_adjustment_enabled: bool = True
    predictive_landing_enabled: bool = True
    battery_reserve_percent: float = 15.0
    max_mission_battery_usage: float = 70.0  # %


class AnomalyDetector(ABC):
    """Базовый класс для детекторов аномалий"""
    
    def __init__(self, thresholds: AnomalyThresholds):
        self.thresholds = thresholds
        self.detection_history = deque(maxlen=1000)
        self.false_positive_rate = 0.0
        
    @abstractmethod
    async def detect(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Обнаружить аномалии в телеметрии"""
        pass
    
    @abstractmethod
    async def get_anomalies(self) -> List[Dict[str, Any]]:
        """Получить список обнаруженных аномалий"""
        pass


class StatisticalAnomalyDetector(AnomalyDetector):
    """Детектор аномалий на основе статистических методов"""
    
    def __init__(self, thresholds: AnomalyThresholds, window_size: int = 100):
        super().__init__(thresholds)
        self.window_size = window_size
        self.telemetry_buffer = deque(maxlen=window_size)
        self.baseline_stats = {}
        self.anomalies = []
        
    async def detect(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Обнаружить аномалии используя статистический анализ"""
        
        self.telemetry_buffer.append(telemetry)
        anomalies = {
            'detected': False,
            'anomalies': [],
            'timestamp': telemetry.get('timestamp', datetime.now().isoformat()),
            'severity': 'none'
        }
        
        # Обновить baseline статистику
        if len(self.telemetry_buffer) > self.window_size // 2:
            await self._update_baseline_statistics()
        
        # Проверить различные параметры
        
        # 1. Режим батареи
        if 'battery_percent' in telemetry and len(self.telemetry_buffer) > 1:
            prev_battery = self.telemetry_buffer[-2].get('battery_percent', telemetry['battery_percent'])
            battery_drop_rate = (prev_battery - telemetry['battery_percent']) / 1.0  # % per second
            
            if battery_drop_rate > self.thresholds.battery_drop_rate:
                anomalies['anomalies'].append({
                    'type': 'rapid_battery_drain',
                    'value': battery_drop_rate,
                    'threshold': self.thresholds.battery_drop_rate,
                    'severity': 'high'
                })
                anomalies['severity'] = 'high'
        
        # 2. Высота
        if 'altitude' in telemetry and len(self.telemetry_buffer) > 1:
            prev_altitude = self.telemetry_buffer[-2].get('altitude', telemetry['altitude'])
            altitude_drop = prev_altitude - telemetry['altitude']
            
            if altitude_drop > self.thresholds.altitude_sudden_drop:
                if 'speed_vertical' in telemetry and telemetry['speed_vertical'] > 0:
                    pass  # Это контролируемое снижение
                else:
                    anomalies['anomalies'].append({
                        'type': 'sudden_altitude_drop',
                        'value': altitude_drop,
                        'threshold': self.thresholds.altitude_sudden_drop,
                        'severity': 'critical'
                    })
                    anomalies['severity'] = 'critical'
        
        # 3. Скорость
        if 'speed' in telemetry:
            if self.baseline_stats.get('avg_speed'):
                speed_variance = abs(telemetry['speed'] - self.baseline_stats['avg_speed']) / \
                               (self.baseline_stats.get('std_speed', 1) + 1e-6)
                
                if speed_variance > self.thresholds.speed_spike:
                    anomalies['anomalies'].append({
                        'type': 'speed_anomaly',
                        'value': telemetry['speed'],
                        'baseline': self.baseline_stats['avg_speed'],
                        'z_score': speed_variance,
                        'severity': 'medium'
                    })
                    if anomalies['severity'] != 'critical':
                        anomalies['severity'] = 'medium'
        
        # 4. Температура
        if 'temperature_cpu' in telemetry:
            if telemetry['temperature_cpu'] > self.thresholds.temperature_spike:
                anomalies['anomalies'].append({
                    'type': 'temperature_spike',
                    'value': telemetry['temperature_cpu'],
                    'threshold': self.thresholds.temperature_spike,
                    'severity': 'high'
                })
                if anomalies['severity'] != 'critical':
                    anomalies['severity'] = 'high'
        
        # 5. Ветер
        if 'wind_speed' in telemetry:
            if telemetry['wind_speed'] > self.thresholds.wind_gust_threshold:
                anomalies['anomalies'].append({
                    'type': 'wind_gust',
                    'value': telemetry['wind_speed'],
                    ' threshold': self.thresholds.wind_gust_threshold,
                    'severity': 'medium'
                })
                if anomalies['severity'] not in ['critical', 'high']:
                    anomalies['severity'] = 'medium'
        
        # 6. CPU использование
        if 'cpu_usage' in telemetry:
            if telemetry['cpu_usage'] > self.thresholds.cpu_usage_critical:
                anomalies['anomalies'].append({
                    'type': 'high_cpu_usage',
                    'value': telemetry['cpu_usage'],
                    'threshold': self.thresholds.cpu_usage_critical,
                    'severity': 'high'
                })
        
        if anomalies['anomalies']:
            anomalies['detected'] = True
            self.anomalies.append(anomalies)
            self.detection_history.append(anomalies)
            logger.warning(f"Anomalies detected: {[a['type'] for a in anomalies['anomalies']]}")
        
        return anomalies
    
    async def _update_baseline_statistics(self) -> None:
        """Обновить базовую статистику из буфера телеметрии"""
        
        if len(self.telemetry_buffer) < 10:
            return
        
        # Извлечь числовые значения
        speeds = [t.get('speed', 0) for t in self.telemetry_buffer if 'speed' in t]
        altitudes = [t.get('altitude', 0) for t in self.telemetry_buffer if 'altitude' in t]
        batteries = [t.get('battery_percent', 0) for t in self.telemetry_buffer if 'battery_percent' in t]
        
        # Вычислить статистику
        if speeds:
            self.baseline_stats['avg_speed'] = float(np.mean(speeds))
            self.baseline_stats['std_speed'] = float(np.std(speeds))
        else:
            self.baseline_stats['avg_speed'] = 0
            self.baseline_stats['std_speed'] = 0
        
        if altitudes:
            self.baseline_stats['avg_altitude'] = float(np.mean(altitudes))
            self.baseline_stats['std_altitude'] = float(np.std(altitudes))
        
        if batteries:
            self.baseline_stats['avg_battery'] = float(np.mean(batteries))
            self.baseline_stats['avg_battery_drop'] = float(np.mean(
                [batteries[i-1] - batteries[i] for i in range(1, len(batteries))]
            ))
    
    async def get_anomalies(self) -> List[Dict[str, Any]]:
        """Получить список обнаруженных аномалий"""
        return self.anomalies[-100:]  # Последние 100 аномалий


class EnergyOptimizer:
    """Оптимизатор энергопотребления для максимизации времени миссии"""
    
    def __init__(self, config: EnergyOptimazationConfig):
        self.config = config
        self.optimization_history = []
        self.current_efficiency = 0.0
        self.energy_predictions = deque(maxlen=1000)
        
    async def optimize_mission_energy(self, mission_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Оптимизировать энергопотребление миссии"""
        
        optimized_profile = mission_profile.copy()
        optimizations_applied = []
        
        # 1. Оптимизация скорости
        if self.config.speed_optimization_enabled and 'speed' in mission_profile:
            optimized_speed = await self._optimize_speed(
                mission_profile['speed'],
                mission_profile.get('distance_km', 0)
            )
            if optimized_speed != mission_profile['speed']:
                optimizations_applied.append({
                    'type': 'speed_optimization',
                    'original': mission_profile['speed'],
                    'optimized': optimized_speed,
                    'energy_saving_percent': ((mission_profile['speed'] - optimized_speed) / mission_profile['speed'] * 100)
                })
                optimized_profile['speed'] = optimized_speed
        
        # 2. Оптимизация высоты
        if self.config.altitude_optimization_enabled and 'altitude' in mission_profile:
            optimized_altitude = await self._optimize_altitude(
                mission_profile['altitude'],
                mission_profile.get('wind_speed', 0)
            )
            if optimized_altitude != mission_profile['altitude']:
                optimizations_applied.append({
                    'type': 'altitude_optimization',
                    'original': mission_profile['altitude'],
                    'optimized': optimized_altitude,
                    'reason': 'Wind adjustment for stability'
                })
                optimized_profile['altitude'] = optimized_altitude
        
        # 3. Оптимизация маршрута
        if self.config.route_optimization_enabled and 'waypoints' in mission_profile:
            optimized_waypoints = await self._optimize_route(mission_profile['waypoints'])
            if len(optimized_waypoints) < len(mission_profile['waypoints']):
                optimizations_applied.append({
                    'type': 'route_optimization',
                    'original_waypoints': len(mission_profile['waypoints']),
                    'optimized_waypoints': len(optimized_waypoints),
                    'distance_saving_percent': 
                        ((len(mission_profile['waypoints']) - len(optimized_waypoints)) / 
                         len(mission_profile['waypoints']) * 100) if mission_profile['waypoints'] else 0
                })
                optimized_profile['waypoints'] = optimized_waypoints
        
        # 4. Предполагаемый расход энергии
        predicted_energy = await self._predict_energy_usage(optimized_profile)
        optimized_profile['predicted_battery_usage'] = predicted_energy
        optimized_profile['estimated_mission_time_minutes'] = \
            await self._estimate_mission_duration(optimized_profile)
        
        return {
            'optimized_profile': optimized_profile,
            'optimizations_applied': optimizations_applied,
            'improvement_percent': sum(o.get('energy_saving_percent', 0) for o in optimizations_applied)
        }
    
    async def _optimize_speed(self, original_speed: float, distance_km: float) -> float:
        """Оптимизировать скорость для минимизации энергопотребления"""
        # Обычно оптимальная скорость 60-70% от максимума
        optimal_ratio = 0.65
        optimized = original_speed * optimal_ratio
        return optimized
    
    async def _optimize_altitude(self, original_altitude: float, wind_speed: float) -> float:
        """Оптимизировать высоту на основе ветра"""
        if wind_speed > 5:
            # При сильном ветре снизить высоту для большей стабильности
            return original_altitude * 0.8
        return original_altitude
    
    async def _optimize_route(self, waypoints: List[Dict]) -> List[Dict]:
        """Оптимизировать маршрут для минимизации расстояния (упрощенная версия)"""
        if len(waypoints) <= 2:
            return waypoints
        
        # Простая эвристика: удалить точки, которые слишком близко друг к другу
        optimized = [waypoints[0]]
        min_distance = 10  # метров
        
        for wp in waypoints[1:]:
            last_wp = optimized[-1]
            distance = np.sqrt(
                (wp.get('latitude', 0) - last_wp.get('latitude', 0))**2 +
                (wp.get('longitude', 0) - last_wp.get('longitude', 0))**2
            ) * 111000  # приблизительное преобразование градусов в метры
            
            if distance >= min_distance:
                optimized.append(wp)
        
        return optimized
    
    async def _predict_energy_usage(self, mission_profile: Dict[str, Any]) -> float:
        """Предсказать энергопотребление для миссии"""
        
        # Упрощенная модель:
        # Energy = distance * hover_power + time * cruise_power + altitude_penalty
        
        distance_km = mission_profile.get('distance_km', 0)
        speed = mission_profile.get('speed', 10)
        altitude = mission_profile.get('altitude', 50)
        
        # Параметры энергопотребления
        hover_efficiency = 1.5  # W/kg (для стандартного дрона 2кг)
        cruise_efficiency = 0.8
        altitude_factor = altitude / 50  # нормализация на 50м
        
        # Вычислить время полета
        mission_time_hours = (distance_km / speed) if speed > 0 else 1
        
        # Приблизительное энергопотребление (в % батареи в час)
        energy_per_hour = (hover_efficiency + cruise_efficiency * altitude_factor) * 10
        estimated_usage = energy_per_hour * mission_time_hours
        
        return min(estimated_usage, 90)  # Max 90% батареи на миссию
    
    async def _estimate_mission_duration(self, mission_profile: Dict[str, Any]) -> float:
        """Оценить длительность миссии в минутах"""
        
        distance_km = mission_profile.get('distance_km', 0)
        speed = mission_profile.get('speed', 10)
        
        duration_hours = (distance_km / speed) if speed > 0 else 1
        return duration_hours * 60  # Вернуть в минутах
    
    async def predict_battery_level(self, 
                                   battery_now: float, 
                                   current_drain_rate: float,
                                   mission_duration_minutes: float) -> Tuple[float, bool]:
        """Предсказать уровень батареи в конце миссии"""
        
        predicted_battery = battery_now - (current_drain_rate * mission_duration_minutes)
        
        safe = predicted_battery > self.config.battery_reserve_percent
        
        self.energy_predictions.append({
            'timestamp': datetime.now().isoformat(),
            'predicted_battery': predicted_battery,
            'safe': safe
        })
        
        return predicted_battery, safe


class SystemMetricsCollector:
    """Сборщик метрик системы для анализа производительности"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=10000)
        self.aggregated_metrics = {}
        self.performance_reports = []
        
    async def collect_metrics(self, telemetry: Dict[str, Any], 
                            mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Собрать метрики системы"""
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'telemetry': telemetry,
            'mission_data': mission_data,
            'computed_metrics': await self._compute_metrics(telemetry, mission_data)
        }
        
        self.metrics_history.append(metrics)
        return metrics
    
    async def _compute_metrics(self, telemetry: Dict[str, Any], 
                              mission_data: Dict[str, Any]) -> Dict[str, float]:
        """Вычислить дополнительные метрики из телеметрии"""
        
        computed = {}
        
        # Эффективность использования батареи
        if 'battery_percent' in telemetry and mission_data.get('mission_time_seconds'):
            battery_drain_rate = (100 - telemetry['battery_percent']) / \
                               (mission_data['mission_time_seconds'] / 60)
            computed['battery_drain_rate_percent_per_minute'] = battery_drain_rate
        
        # Стабильность (на основе дельты высоты)
        if 'altitude' in telemetry:
            computed['altitude'] = telemetry['altitude']
        
        # Точность GPS
        if 'gps_hdop' in telemetry:
            computed['gps_accuracy_estimate'] = 5 * telemetry.get('gps_hdop', 1)  # в метрах
        
        # Утилизация CPU
        if 'cpu_usage' in telemetry:
            computed['cpu_efficiency'] = 100 - telemetry['cpu_usage']
        
        # Уровень сигнала
        if 'signal_strength_dbm' in telemetry:
            computed['signal_quality'] = telemetry['signal_strength_dbm'] + 120  # normalize to 0-120
        
        return computed
    
    async def generate_performance_report(self, 
                                        duration_minutes: int = 60) -> Dict[str, Any]:
        """Сгенерировать отчёт производительности"""
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        relevant_metrics = [m for m in self.metrics_history 
                          if datetime.fromisoformat(m['timestamp']) > cutoff_time]
        
        if not relevant_metrics:
            return {}
        
        report = {
            'period_minutes': duration_minutes,
            'metrics_collected': len(relevant_metrics),
            'average_altitude': float(np.mean([m['telemetry'].get('altitude', 0) 
                                              for m in relevant_metrics])),
            'average_battery_drain': float(np.mean([m['computed_metrics'].get('battery_drain_rate_percent_per_minute', 0)
                                                   for m in relevant_metrics])),
            'average_cpu_usage': float(np.mean([100 - m['computed_metrics'].get('cpu_efficiency', 50)
                                               for m in relevant_metrics])),
            'average_signal_quality': float(np.mean([m['computed_metrics'].get('signal_quality', 50)
                                                    for m in relevant_metrics])),
            'generated_at': datetime.now().isoformat()
        }
        
        self.performance_reports.append(report)
        return report


class MonitoringOrchestrator:
    """Главный оркестратор мониторинга и аналитики"""
    
    def __init__(self):
        self.anomaly_detector = None
        self.energy_optimizer = None
        self.metrics_collector = None
        self.alert_handlers: Dict[str, Callable] = {}
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Инициализировать компоненты мониторинга"""
        
        logger.info("Initializing Monitoring Orchestrator")
        
        # Инициализировать детектор аномалий
        anomaly_thresholds = AnomalyThresholds(
            **{k.replace('anomaly_threshold_', ''): v 
               for k, v in config.items() if k.startswith('anomaly_threshold_')}
        )
        self.anomaly_detector = StatisticalAnomalyDetector(anomaly_thresholds)
        
        # Инициализировать оптимизатор энергии
        energy_config = EnergyOptimazationConfig(
            **{k.replace('energy_', ''): v 
               for k, v in config.items() if k.startswith('energy_')}
        )
        self.energy_optimizer = EnergyOptimizer(energy_config)
        
        # Инициализировать сборщик метрик
        self.metrics_collector = SystemMetricsCollector()
        
        logger.info("Monitoring Orchestrator initialized successfully")
    
    def register_alert_handler(self, alert_type: str, handler: Callable) -> None:
        """Зарегистрировать обработчик для типа алерта"""
        self.alert_handlers[alert_type] = handler
        logger.info(f"Registered alert handler for {alert_type}")
    
    async def process_monitor_cycle(self, telemetry: Dict[str, Any], 
                                   mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнить один цикл мониторинга"""
        
        cycle_result = {
            'timestamp': datetime.now().isoformat(),
            'anomalies': None,
            'energy_status': None,
            'metrics': None,
            'alerts': []
        }
        
        # Обнаружить аномалии
        if self.anomaly_detector:
            anomalies = await self.anomaly_detector.detect(telemetry)
            cycle_result['anomalies'] = anomalies
            
            # Обработать аномалии
            if anomalies['detected'] and anomalies['severity'] in ['high', 'critical']:
                alert = {
                    'type': 'anomaly_detected',
                    'severity': anomalies['severity'],
                    'anomalies': [a['type'] for a in anomalies['anomalies']]
                }
                cycle_result['alerts'].append(alert)
                
                # Вызвать обработчик если зарегистрирован
                if 'anomaly_detected' in self.alert_handlers:
                    await self.alert_handlers['anomaly_detected'](alert)
        
        # Собрать метрики
        if self.metrics_collector:
            metrics = await self.metrics_collector.collect_metrics(telemetry, mission_data)
            cycle_result['metrics'] = metrics
        
        return cycle_result
