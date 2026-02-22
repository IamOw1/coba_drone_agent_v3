"""
Модуль обучения агента с использованием Reinforcement Learning
"""
import json
import pickle
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque

from utils.logger import setup_logger

logger = setup_logger(__name__)


class DQNNetwork(nn.Module):
    """Нейронная сеть для DQN"""
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super(DQNNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc4 = nn.Linear(hidden_size // 2, action_size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.relu(self.fc3(x))
        return self.fc4(x)


class ReplayBuffer:
    """Буфер воспроизведения опыта"""
    
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """Добавление опыта в буфер"""
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size: int):
        """Сэмплирование батча"""
        indices = np.random.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )
    
    def __len__(self):
        return len(self.buffer)


class Learner:
    """
    Модуль обучения агента с использованием Deep Q-Learning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация модуля обучения.
        
        Args:
            config (Dict[str, Any]): Конфигурация обучения.
        """
        self.config = config
        learning_config = config.get('learning', {})
        
        # Параметры RL
        self.state_size = learning_config.get('state_size', 24)
        self.action_size = learning_config.get('action_size', 8)
        self.learning_rate = learning_config.get('learning_rate', 0.001)
        self.gamma = learning_config.get('gamma', 0.99)
        self.epsilon = learning_config.get('epsilon', 1.0)
        self.epsilon_min = learning_config.get('epsilon_min', 0.01)
        self.epsilon_decay = learning_config.get('epsilon_decay', 0.995)
        self.batch_size = learning_config.get('batch_size', 64)
        self.buffer_size = learning_config.get('buffer_size', 10000)
        self.target_update = learning_config.get('target_update', 100)
        
        # Устройство (CPU/GPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Нейронные сети
        self.policy_net = DQNNetwork(self.state_size, self.action_size).to(self.device)
        self.target_net = DQNNetwork(self.state_size, self.action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # Оптимизатор
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        
        # Буфер воспроизведения
        self.replay_buffer = ReplayBuffer(self.buffer_size)
        
        # Счетчики
        self.step_count = 0
        self.episode_count = 0
        self.total_reward = 0
        
        # История обучения
        self.training_history = []
        
        # Загрузка предобученной модели если есть
        self._load_model()
        
        logger.info(f"Модуль обучения инициализирован (device: {self.device})")
    
    def _load_model(self):
        """Загрузка сохраненной модели"""
        model_dir = Path("data/models")
        if model_dir.exists():
            model_files = list(model_dir.glob("*.pt"))
            if model_files:
                latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
                try:
                    self.policy_net.load_state_dict(torch.load(latest_model, map_location=self.device))
                    self.target_net.load_state_dict(self.policy_net.state_dict())
                    logger.info(f"Загружена модель: {latest_model.name}")
                except Exception as e:
                    logger.error(f"Ошибка загрузки модели: {e}")
    
    async def learn_from_experience(self, experience: Dict[str, Any]):
        """
        Обучение на основе опыта.
        
        Args:
            experience (Dict[str, Any]): Опыт (state, action, reward, next_state, done).
        """
        try:
            state = self._extract_state(experience.get("state", {}))
            action = experience.get("action", {}).get("command_id", 0)
            reward = self._calculate_reward(experience)
            next_state = self._extract_state(experience.get("next_state", {}))
            done = experience.get("done", False)
            
            # Добавление в буфер
            self.replay_buffer.push(state, action, reward, next_state, done)
            
            # Обучение если достаточно данных
            if len(self.replay_buffer) >= self.batch_size:
                await self._train_step()
            
            # Обновление epsilon
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
            
            self.step_count += 1
            self.total_reward += reward
            
            # Обновление target network
            if self.step_count % self.target_update == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())
            
        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
    
    def _extract_state(self, state_data: Dict[str, Any]) -> np.ndarray:
        """
        Извлечение вектора состояния из данных.
        
        Args:
            state_data (Dict[str, Any]): Данные состояния.
            
        Returns:
            np.ndarray: Вектор состояния.
        """
        telemetry = state_data.get("telemetry", {})
        position = telemetry.get("position", {"x": 0, "y": 0, "z": 0})
        velocity = telemetry.get("velocity", {"vx": 0, "vy": 0, "vz": 0})
        attitude = telemetry.get("attitude", {"roll": 0, "pitch": 0, "yaw": 0})
        
        state = [
            position.get("x", 0),
            position.get("y", 0),
            position.get("z", 0),
            velocity.get("vx", 0),
            velocity.get("vy", 0),
            velocity.get("vz", 0),
            attitude.get("roll", 0),
            attitude.get("pitch", 0),
            attitude.get("yaw", 0),
            telemetry.get("battery", 100) / 100,
            telemetry.get("signal_strength", 100) / 100,
            telemetry.get("temperature", 25) / 100,
        ]
        
        # Дополняем до нужного размера
        while len(state) < self.state_size:
            state.append(0.0)
        
        return np.array(state[:self.state_size], dtype=np.float32)
    
    def _calculate_reward(self, experience: Dict[str, Any]) -> float:
        """
        Вычисление награды для обучения.
        
        Args:
            experience (Dict[str, Any]): Опыт.
            
        Returns:
            float: Награда.
        """
        reward = 0.0
        
        # Награда за выполнение миссии
        if experience.get("mission_completed", False):
            reward += 100.0
        
        # Награда за достижение точки
        if experience.get("waypoint_reached", False):
            reward += 10.0
        
        # Штраф за аварийную ситуацию
        if experience.get("emergency", False):
            reward -= 50.0
        
        # Штраф за низкий заряд
        battery = experience.get("state", {}).get("telemetry", {}).get("battery", 100)
        if battery < 20:
            reward -= 10.0
        
        # Награда за эффективность (меньше действий = лучше)
        reward -= 0.1
        
        return reward
    
    async def _train_step(self):
        """Шаг обучения"""
        try:
            # Сэмплирование батча
            states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)
            
            # Конвертация в тензоры
            states = torch.FloatTensor(states).to(self.device)
            actions = torch.LongTensor(actions).to(self.device)
            rewards = torch.FloatTensor(rewards).to(self.device)
            next_states = torch.FloatTensor(next_states).to(self.device)
            dones = torch.FloatTensor(dones).to(self.device)
            
            # Текущие Q-значения
            current_q = self.policy_net(states).gather(1, actions.unsqueeze(1))
            
            # Целевые Q-значения
            with torch.no_grad():
                next_q = self.target_net(next_states).max(1)[0]
                target_q = rewards + (1 - dones) * self.gamma * next_q
            
            # Loss
            loss = nn.MSELoss()(current_q.squeeze(), target_q)
            
            # Оптимизация
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            # Логирование
            if self.step_count % 100 == 0:
                logger.info(f"Шаг {self.step_count}, Loss: {loss.item():.4f}, Epsilon: {self.epsilon:.4f}")
            
        except Exception as e:
            logger.error(f"Ошибка шага обучения: {e}")
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Выбор действия (epsilon-greedy).
        
        Args:
            state (np.ndarray): Состояние.
            training (bool): Режим обучения.
            
        Returns:
            int: ID действия.
        """
        if training and np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()
    
    def get_progress(self) -> Dict[str, Any]:
        """
        Получение прогресса обучения.
        
        Returns:
            Dict[str, Any]: Прогресс обучения.
        """
        return {
            "step_count": self.step_count,
            "episode_count": self.episode_count,
            "total_reward": self.total_reward,
            "epsilon": self.epsilon,
            "buffer_size": len(self.replay_buffer),
            "average_reward": self.total_reward / max(self.step_count, 1)
        }
    
    def save_model(self, path: str = None):
        """
        Сохранение модели.
        
        Args:
            path (str): Путь для сохранения.
        """
        if path is None:
            path = f"data/models/dqn_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.policy_net.state_dict(), path)
        
        # Сохранение метаданных
        metadata = {
            "step_count": self.step_count,
            "episode_count": self.episode_count,
            "epsilon": self.epsilon,
            "config": self.config.get('learning', {})
        }
        
        metadata_path = path.replace('.pt', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Модель сохранена: {path}")
    
    def start_episode(self):
        """Начало нового эпизода обучения"""
        self.episode_count += 1
        logger.info(f"Начало эпизода {self.episode_count}")
    
    def end_episode(self, total_reward: float):
        """
        Завершение эпизода.
        
        Args:
            total_reward (float): Общая награда за эпизод.
        """
        self.training_history.append({
            "episode": self.episode_count,
            "reward": total_reward,
            "epsilon": self.epsilon,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Эпизод {self.episode_count} завершен. Награда: {total_reward:.2f}")
        
        # Сохранение модели периодически
        if self.episode_count % 10 == 0:
            self.save_model()


class PPOLearner(Learner):
    """
    Обучение с использованием PPO (Proximal Policy Optimization).
    Расширенная версия для более сложных сценариев.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Дополнительные параметры PPO
        self.clip_epsilon = config.get('learning', {}).get('clip_epsilon', 0.2)
        self.value_coef = config.get('learning', {}).get('value_coef', 0.5)
        self.entropy_coef = config.get('learning', {}).get('entropy_coef', 0.01)
        
        logger.info("PPO Learner инициализирован")
    
    async def learn_from_experience(self, experience: Dict[str, Any]):
        """PPO обучение (заглушка для будущей реализации)"""
        # TODO: Реализовать PPO
        await super().learn_from_experience(experience)
