"""
Продвинутые алгоритмы машинного обучения для COBA AI Drone Agent
Включает: Meta-learning, Transfer learning, Multi-agent RL, Imitation learning, Curriculum learning
"""

import asyncio
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class MetaLearningState:
    """Состояние для Meta-learning"""
    inner_lr: float = 0.01
    outer_lr: float = 0.001
    inner_steps: int = 5
    meta_batch_size: int = 4
    task_distribution: Dict[str, float] = field(default_factory=dict)
    

@dataclass
class TransferLearningConfig:
    """Конфигурация для Transfer learning"""
    source_domain: str = "simulation"
    target_domain: str = "real_world"
    adaptation_steps: int = 100
    domain_adaptation_weight: float = 0.5
    source_model_path: str = ""
    freeze_early_layers: bool = True


@dataclass
class MultiAgentRLConfig:
    """Конфигурация для Multi-agent RL"""
    num_agents: int = 5
    communication_enabled: bool = True
    shared_experience_buffer: bool = True
    cooperative_reward: float = 0.3
    competitive_reward: float = 0.1


@dataclass
class ImitationLearningConfig:
    """Конфигурация для Imitation learning"""
    expert_trajectories_path: str = "data/expert_trajectories/"
    behavioral_cloning: bool = True
    dagger_enabled: bool = True
    dagger_iterations: int = 10
    expert_policy_weight: float = 0.5


@dataclass
class CurriculumLearningTask:
    """Задача в curriculum learning"""
    task_id: str
    name: str
    difficulty: float  # 0.0-1.0
    prerequisites: List[str] = field(default_factory=list)
    success_threshold: float = 0.8
    completed: bool = False
    training_iterations: int = 0


class MetaLearner(ABC):
    """Базовый класс для Meta-learning алгоритмов"""
    
    def __init__(self, config: MetaLearningState):
        self.config = config
        self.meta_loss_history = []
        
    @abstractmethod
    async def learn_from_tasks(self, tasks: List[Dict]) -> float:
        """Обучение на нескольких задачах для быстрой адаптации"""
        pass
    
    @abstractmethod
    async def adapt_to_new_task(self, task: Dict, steps: int) -> None:
        """Быстрая адаптация к новой задаче"""
        pass


class MAMLLearner(MetaLearner):
    """Model-Agnostic Meta-Learning (MAML) реализация"""
    
    def __init__(self, model: nn.Module, config: MetaLearningState):
        super().__init__(config)
        self.model = model
        self.meta_optimizer = torch.optim.Adam(model.parameters(), lr=config.outer_lr)
        
    async def learn_from_tasks(self, tasks: List[Dict]) -> float:
        """Обучение MAML на batch задач"""
        meta_loss = 0.0
        
        for task in tasks:
            # Создать копию модели для inner loop
            inner_model = self._clone_model()
            inner_optimizer = torch.optim.SGD(inner_model.parameters(), 
                                             lr=self.config.inner_lr)
            
            # Inner loop: быстрая адаптация
            for _ in range(self.config.inner_steps):
                predictions = inner_model(task['support_data'])
                loss = torch.nn.functional.mse_loss(predictions, task['support_labels'])
                inner_optimizer.zero_grad()
                loss.backward()
                inner_optimizer.step()
            
            # OuterL loop: обновление мета-параметров
            query_predictions = inner_model(task['query_data'])
            meta_loss += torch.nn.functional.mse_loss(query_predictions, task['query_labels'])
        
        # Обновить мета-параметры
        meta_loss /= len(tasks)
        self.meta_optimizer.zero_grad()
        meta_loss.backward()
        self.meta_optimizer.step()
        
        self.meta_loss_history.append(meta_loss.item())
        logger.info(f"MAML Meta loss: {meta_loss.item():.4f}")
        
        return meta_loss.item()
    
    async def adapt_to_new_task(self, task: Dict, steps: int = 5) -> None:
        """Быстрая адаптация к новой задаче"""
        optimizer = torch.optim.SGD(self.model.parameters(), lr=self.config.inner_lr)
        
        for step in range(steps):
            predictions = self.model(task['data'])
            loss = torch.nn.functional.mse_loss(predictions, task['labels'])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if step % 2 == 0:
                logger.info(f"Task adaptation step {step+1}/{steps}, loss: {loss.item():.4f}")
    
    def _clone_model(self) -> nn.Module:
        """Создать копию модели"""
        import copy
        return copy.deepcopy(self.model)


class TransferLearner:
    """Transfer Learning для доменной адаптации"""
    
    def __init__(self, source_model: nn.Module, config: TransferLearningConfig):
        self.source_model = source_model
        self.config = config
        self.target_model = self._create_target_model(source_model)
        self.adaptation_history = []
        
    def _create_target_model(self, source_model: nn.Module) -> nn.Module:
        """Создать целевую модель на основе исходной"""
        import copy
        target_model = copy.deepcopy(source_model)
        
        # Заморозить ранние слои
        if self.config.freeze_early_layers:
            layer_count = 0
            for param in target_model.parameters():
                param.requires_grad = layer_count > 2
                layer_count += 1
        
        return target_model
    
    async def adapt_domain(self, source_data: torch.Tensor, target_data: torch.Tensor) -> Dict:
        """Доменная адаптация между исходным и целевым доменами"""
        optimizer = torch.optim.Adam(self.target_model.parameters(), lr=0.001)
        
        adaptation_metrics = {
            'source_loss': [],
            'target_loss': [],
            'domain_loss': [],
            'total_loss': []
        }
        
        for step in range(self.config.adaptation_steps):
            # Forward pass на исходном домене
            source_output = self.target_model(source_data)
            source_loss = torch.nn.functional.mse_loss(
                source_output, 
                self.source_model(source_data)
            )
            
            # Forward pass на целевом домене
            target_output = self.target_model(target_data)
            # Минимизировать дивергенцию распределений
            target_loss = self._compute_domain_loss(
                self.source_model(source_data),
                target_output
            )
            
            # Общая потеря
            total_loss = (1 - self.config.domain_adaptation_weight) * source_loss + \
                        self.config.domain_adaptation_weight * target_loss
            
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            
            # Отслеживать метрики
            adaptation_metrics['source_loss'].append(source_loss.item())
            adaptation_metrics['target_loss'].append(target_loss.item())
            adaptation_metrics['total_loss'].append(total_loss.item())
            
            if (step + 1) % 20 == 0:
                logger.info(f"Domain adaptation step {step+1}/{self.config.adaptation_steps}, "
                           f"Loss: {total_loss.item():.4f}")
        
        self.adaptation_history.append(adaptation_metrics)
        return adaptation_metrics
    
    def _compute_domain_loss(self, source_features: torch.Tensor, 
                            target_features: torch.Tensor) -> torch.Tensor:
        """Вычислить domain divergence loss (Maximum Mean Discrepancy)"""
        # Упрощенная версия MMD
        source_mean = source_features.mean(dim=0)
        target_mean = target_features.mean(dim=0)
        return torch.nn.functional.mse_loss(source_mean, target_mean)


class MultiAgentRLCoordinator:
    """Координатор для Multi-agent Reinforcement Learning"""
    
    def __init__(self, config: MultiAgentRLConfig):
        self.config = config
        self.agents = []
        self.shared_experience_buffer = [] if config.shared_experience_buffer else None
        self.communication_graph = self._initialize_communication()
        
    def _initialize_communication(self) -> Dict[int, List[int]]:
        """Инициализировать граф коммуникации между агентами"""
        # Полносвязная топология
        graph = {}
        for i in range(self.config.num_agents):
            graph[i] = [j for j in range(self.config.num_agents) if j != i]
        return graph
    
    async def coordinate_agents(self, agent_states: List[Dict]) -> Dict[int, Dict]:
        """Координировать действия множества агентов"""
        
        actions = {}
        
        for agent_id, state in enumerate(agent_states):
            # Получить соседей в communication graph
            neighbors = self.communication_graph[agent_id]
            neighbor_states = [agent_states[n] for n in neighbors]
            
            #计算действие с учетом соседей
            cooperative_signal = self._compute_cooperative_signal(
                state, 
                neighbor_states
            )
            
            # Комбинировать индивидуальные и кооративные вознаграждения
            actions[agent_id] = {
                'individual_action': state.get('action', None),
                'cooperative_signal': cooperative_signal,
                'combined_reward_weight': {
                    'individual': 1.0 - self.config.cooperative_reward,
                    'cooperative': self.config.cooperative_reward
                }
            }
        
        return actions
    
    def _compute_cooperative_signal(self, agent_state: Dict, 
                                   neighbor_states: List[Dict]) -> Dict:
        """Вычислить кооперативный сигнал для агента"""
        
        if not neighbor_states:
            return {}
        
        # Усреднить состояния соседей
        cooperative_signal = {
            'avg_position': np.mean([s.get('position', [0, 0]) 
                                     for s in neighbor_states], axis=0),
            'group_heading': np.mean([s.get('heading', 0) 
                                     for s in neighbor_states]),
            'neighbor_count': len(neighbor_states)
        }
        
        return cooperative_signal
    
    async def add_experience(self, agent_id: int, experience: Dict) -> None:
        """Добавить опыт в shared buffer"""
        if self.shared_experience_buffer is not None:
            self.shared_experience_buffer.append({
                'agent_id': agent_id,
                'experience': experience,
                'timestamp': datetime.now().isoformat()
            })
            
            # Очистить если буфер слишком большой
            if len(self.shared_experience_buffer) > 10000:
                self.shared_experience_buffer = self.shared_experience_buffer[-5000:]


class ImitationLearner:
    """Обучение через подражание экспертным траекториям"""
    
    def __init__(self, model: nn.Module, config: ImitationLearningConfig):
        self.model = model
        self.config = config
        self.expert_trajectories = []
        self.training_history = []
        
    async def load_expert_trajectories(self) -> int:
        """Загрузить экспертные траектории"""
        try:
            # Попытаться загрузить из файла
            import os
            if os.path.exists(self.config.expert_trajectories_path):
                files = os.listdir(self.config.expert_trajectories_path)
                for file in files:
                    if file.endswith('.json'):
                        with open(os.path.join(self.config.expert_trajectories_path, file)) as f:
                            traj = json.load(f)
                            self.expert_trajectories.append(traj)
            
            logger.info(f"Loaded {len(self.expert_trajectories)} expert trajectories")
            return len(self.expert_trajectories)
        except Exception as e:
            logger.error(f"Error loading expert trajectories: {e}")
            return 0
    
    async def behavioral_cloning(self, epochs: int = 10) -> Dict[str, List[float]]:
        """Обучение путем подражания поведению эксперта (Behavioral Cloning)"""
        
        if not self.expert_trajectories:
            logger.warning("No expert trajectories available for behavioral cloning")
            return {}
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        history = {'loss': [], 'accuracy': []}
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_accuracy = 0.0
            
            for traj in self.expert_trajectories:
                states = torch.tensor(traj['states'], dtype=torch.float32)
                actions = torch.tensor(traj['actions'], dtype=torch.long)
                
                # Forward pass
                predictions = self.model(states)
                loss = torch.nn.functional.cross_entropy(predictions, actions)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                # Вычислить точчност
                accuracy = (predictions.argmax(dim=1) == actions).float().mean()
                
                epoch_loss += loss.item()
                epoch_accuracy += accuracy.item()
            
            avg_loss = epoch_loss / len(self.expert_trajectories)
            avg_accuracy = epoch_accuracy / len(self.expert_trajectories)
            
            history['loss'].append(avg_loss)
            history['accuracy'].append(avg_accuracy)
            
            if (epoch + 1) % 2 == 0:
                logger.info(f"BC Epoch {epoch+1}/{epochs} - "
                           f"Loss: {avg_loss:.4f}, Accuracy: {avg_accuracy:.4f}")
        
        self.training_history.append(history)
        return history
    
    async def dagger_learning(self) -> Dict[str, Any]:
        """Dataset Aggregation (DAgger) для итеративного обучения"""
        
        if not self.expert_trajectories:
            logger.warning("No expert trajectories available for DAgger")
            return {}
        
        aggregated_dataset = []
        dagger_history = {'success_rate': [], 'expert_queries': []}
        
        for iteration in range(self.config.dagger_iterations):
            logger.info(f"DAgger iteration {iteration+1}/{self.config.dagger_iterations}")
            
            # Фаза 1: Дорогирующее обучение
            await self.behavioral_cloning(epochs=5)
            
            # Фаза 2: Выполнить политику и получить умение эксперта
            expert_queries = 0
            for traj_idx, traj in enumerate(self.expert_trajectories):
                states = torch.tensor(traj['states'], dtype=torch.float32)
                
                # Получить предсказания модели
                with torch.no_grad():
                    predictions = self.model(states).argmax(dim=1).cpu().numpy()
                
                # Получить истинные действия эксперта
                expert_actions = traj['actions']
                
                # Проверить расхождение
                divergence = (predictions != expert_actions).sum()
                if divergence > len(states) * 0.3:  # Если расхождение > 30%
                    expert_queries += 1
                    # Агрегировать экспертные данные
                    aggregated_dataset.append({
                        'states': traj['states'],
                        'expert_actions': expert_actions,
                        'iteration': iteration
                    })
            
            dagger_history['expert_queries'].append(expert_queries)
            
            # Фаза 3: Переобучить на агрегированном набороре
            if aggregated_dataset:
                logger.info(f"Retraining on {len(aggregated_dataset)} aggregated trajectories")
        
        return dagger_history


class CurriculumLearner:
    """Curriculum Learning - постепенное обучение от простого к сложному"""
    
    def __init__(self, model: nn.Module):
        self.model = model
        self.curriculum = []
        self.current_task_idx = 0
        self.completion_history = []
        
    def add_task(self, task: CurriculumLearningTask) -> None:
        """Добавить задачу в curriculum"""
        self.curriculum.append(task)
        logger.info(f"Added task '{task.name}' with difficulty {task.difficulty:.2f}")
    
    def create_default_curriculum(self) -> List[CurriculumLearningTask]:
        """Создать curriculum по умолчанию для управления дроном"""
        
        tasks = [
            CurriculumLearningTask(
                task_id="hover",
                name="Зависание на месте",
                difficulty=0.1,
                success_threshold=0.95
            ),
            CurriculumLearningTask(
                task_id="straight_flight",
                name="Прямой полёт",
                difficulty=0.2,
                prerequisites=["hover"]
            ),
            CurriculumLearningTask(
                task_id="waypoint_navigation",
                name="Навигация по точкам",
                difficulty=0.4,
                prerequisites=["straight_flight"]
            ),
            CurriculumLearningTask(
                task_id="obstacle_avoidance",
                name="Избегание препятствий",
                difficulty=0.6,
                prerequisites=["waypoint_navigation"]
            ),
            CurriculumLearningTask(
                task_id="complex_maneuvers",
                name="Сложные маневры",
                difficulty=0.8,
                prerequisites=["obstacle_avoidance"]
            ),
            CurriculumLearningTask(
                task_id="swarm_coordination",
                name="Координация роя",
                difficulty=1.0,
                prerequisites=["complex_maneuvers"]
            ),
        ]
        
        self.curriculum = tasks
        return tasks
    
    async def get_current_task(self) -> Optional[CurriculumLearningTask]:
        """Получить текущую задачу"""
        
        if self.current_task_idx >= len(self.curriculum):
            logger.info("All curriculum tasks completed!")
            return None
        
        current_task = self.curriculum[self.current_task_idx]
        
        # Проверить prerequisities
        for prereq in current_task.prerequisites:
            task = next((t for t in self.curriculum if t.task_id == prereq), None)
            if task and not task.completed:
                logger.warning(f"Prerequisite task '{prereq}' not completed yet")
                return None
        
        return current_task
    
    async def complete_task(self, task_id: str, success_rate: float) -> bool:
        """Отметить задачу как выполненную"""
        
        task = next((t for t in self.curriculum if t.task_id == task_id), None)
        if not task:
            return False
        
        if success_rate >= task.success_threshold:
            task.completed = True
            task.training_iterations += 1
            self.current_task_idx += 1
            
            self.completion_history.append({
                'task_id': task_id,
                'task_name': task.name,
                'success_rate': success_rate,
                'completed_at': datetime.now().isoformat()
            })
            
            logger.info(f"Task '{task.name}' completed with success rate {success_rate:.2%}")
            return True
        else:
            task.training_iterations += 1
            logger.info(f"Task '{task.name}' incomplete. Success: {success_rate:.2%}, "
                       f"Required: {task.success_threshold:.2%}")
            return False
    
    async def get_learning_progress(self) -> Dict[str, Any]:
        """Получить прогресс обучения"""
        
        total_tasks = len(self.curriculum)
        completed_tasks = sum(1 for t in self.curriculum if t.completed)
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'progress_percent': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'current_task': self.curriculum[self.current_task_idx].name if self.current_task_idx < total_tasks else "Completed",
            'task_details': [
                {
                    'task_id': task.task_id,
                    'name': task.name,
                    'difficulty': task.difficulty,
                    'completed': task.completed,
                    'training_iterations': task.training_iterations
                }
                for task in self.curriculum
            ],
            'completion_history': self.completion_history
        }


class AdvancedLearningOrchestrator:
    """Главный оркестратор для управления всеми продвинутыми техниками обучения"""
    
    def __init__(self):
        self.meta_learner = None
        self.transfer_learner = None
        self.multi_agent_coordinator = None
        self.imitation_learner = None
        self.curriculum_learner = None
        self.active_learning_strategies = []
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Инициализировать все техники обучения"""
        
        logger.info("Initializing Advanced Learning Orchestrator")
        
        # Инициализировать Meta-learning if enabled
        if config.get('enable_meta_learning', False):
            pass  # Инициализация будет выполнена с моделью
        
        # Инициализировать Multi-agent RL if enabled
        if config.get('enable_multi_agent_rl', False):
            ma_config = MultiAgentRLConfig(
                num_agents=config.get('num_agents', 5)
            )
            self.multi_agent_coordinator = MultiAgentRLCoordinator(ma_config)
            logger.info("Multi-agent RL coordinator initialized")
        
        # Создать curriculum Learning
        self.curriculum_learner = CurriculumLearner(None)
        self.curriculum_learner.create_default_curriculum()
        logger.info("Curriculum learner initialized")
        
        self.active_learning_strategies = config.get('active_learning_strategies', [])
    
    async def get_learning_status(self) -> Dict[str, Any]:
        """Получить статус всех техник обучения"""
        
        status = {
            'meta_learning': 'initialized' if self.meta_learner else 'disabled',
            'transfer_learning': 'initialized' if self.transfer_learner else 'disabled',
            'multi_agent_rl': 'initialized' if self.multi_agent_coordinator else 'disabled',
            'imitation_learning': 'initialized' if self.imitation_learner else 'disabled',
            'curriculum_learning': await self.curriculum_learner.get_learning_progress() if self.curriculum_learner else 'disabled'
        }
        
        return status
