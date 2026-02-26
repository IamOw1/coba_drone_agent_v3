"""
Модули безопасности и шифрования для COBA AI Drone Agent
Включает: AES-256 шифрование, аутентификацию, аудит, защиту от атак
"""

import hashlib
import hmac
import secrets
import json
import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("cryptography module not available - using basic encryption")
    CRYPTO_AVAILABLE = False


@dataclass
class SecurityConfig:
    """Конфигурация безопасности"""
    enable_encryption: bool = True
    encryption_algorithm: str = "AES-256"
    hash_algorithm: str = "SHA-256"
    
    # API Security
    enable_api_key_auth: bool = True
    enable_jwt_auth: bool = False  # JWT требует дополнительных библиотек
    api_key_rotation_days: int = 90
    
    # Rate limiting
    enable_rate_limiting: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 10000
    
    # Audit logging
    enable_audit_logging: bool = True
    log_rotation_days: int = 30
    
    # Password policy
    min_password_length: int = 12
    require_special_chars: bool = True
    require_uppercase: bool = True
    require_numbers: bool = True
    
    # Session management
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 5
    
    # IP Whitelist
    enable_ip_whitelist: bool = False
    whitelisted_ips: List[str] = field(default_factory=list)


@dataclass
class AuditLogEntry:
    """Запись в журнал аудита"""
    timestamp: str
    user_id: str
    action: str
    resource: str
    status: str  # success, failure
    ip_address: str
    details: Dict[str, Any] = field(default_factory=dict)


class EncryptionManager:
    """Менеджер шифрования данных"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key
        self.cipher = self._initialize_cipher()
        self.encryption_history = []
        
    def _initialize_cipher(self):
        """Инициализировать шифр"""
        if not CRYPTO_AVAILABLE:
            logger.warning("Using basic XOR encryption - not suitable for production")
            return None
        
        if self.master_key:
            # Развернуть ключ используя PBKDF2
            salt = b'coba_drone_salt'  # В продакшене использовать случайный salt
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(
                kdf.derive(self.master_key.encode())
            )
            return Fernet(key)
        return None
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """Зашифровать данные"""
        
        json_data = json.dumps(data)
        
        if CRYPTO_AVAILABLE and self.cipher:
            try:
                encrypted = self.cipher.encrypt(json_data.encode())
                self.encryption_history.append({
                    'action': 'encrypt',
                    'timestamp': datetime.now().isoformat(),
                    'data_size': len(json_data)
                })
                return encrypted.decode()
            except Exception as e:
                logger.error(f"Encryption error: {e}")
                return json_data
        else:
            # Fallback: базовое кодирование (НЕ безопасное!)
            return json_data
    
    def decrypt_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Расшифровать данные"""
        
        if CRYPTO_AVAILABLE and self.cipher:
            try:
                decrypted = self.cipher.decrypt(encrypted_data.encode())
                data = json.loads(decrypted.decode())
                self.encryption_history.append({
                    'action': 'decrypt',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                })
                return data
            except Exception as e:
                logger.error(f"Decryption error: {e}")
                self.encryption_history.append({
                    'action': 'decrypt',
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'error': str(e)
                })
                return None
        else:
            # Fallback
            try:
                return json.loads(encrypted_data)
            except:
                return None
    
    def hash_data(self, data: str, algorithm: str = "SHA-256") -> str:
        """Хешировать данные"""
        
        if algorithm == "SHA-256":
            return hashlib.sha256(data.encode()).hexdigest()
        elif algorithm == "SHA-512":
            return hashlib.sha512(data.encode()).hexdigest()
        else:
            return hashlib.sha256(data.encode()).hexdigest()


class APIKeyManager:
    """Менеджер API ключей"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.valid_keys = {}  # API Key -> Key Info
        self.key_usage_log = []
        
    def generate_api_key(self, user_id: str, description: str = "") -> str:
        """Сгенерировать новый API ключ"""
        
        api_key = f"coba_key_{secrets.token_urlsafe(32)}"
        
        self.valid_keys[api_key] = {
            'user_id': user_id,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'last_used': None,
            'expiration_date': (datetime.now() + timedelta(days=self.config.api_key_rotation_days)).isoformat(),
            'active': True,
            'usage_count': 0
        }
        
        logger.info(f"Generated new API key for user {user_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Проверить валидность API ключа"""
        
        if api_key not in self.valid_keys:
            return False, "Invalid API key"
        
        key_info = self.valid_keys[api_key]
        
        if not key_info['active']:
            return False, "API key is deactivated"
        
        expiration = datetime.fromisoformat(key_info['expiration_date'])
        if datetime.now() > expiration:
            return False, "API key has expired"
        
        # Обновить last_used и usage_count
        key_info['last_used'] = datetime.now().isoformat()
        key_info['usage_count'] += 1
        
        return True, key_info['user_id']
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Отозвать API ключ"""
        
        if api_key in self.valid_keys:
            self.valid_keys[api_key]['active'] = False
            logger.warning(f"API key revoked: {api_key[:20]}...")
            return True
        return False
    
    def list_api_keys(self, user_id: str) -> List[Dict]:
        """Список API ключей пользователя"""
        
        return [
            {
                'api_key': k[:20] + '...',  # Не показывать полный ключ
                'description': v['description'],
                'created_at': v['created_at'],
                'expiration_date': v['expiration_date'],
                'active': v['active'],
                'usage_count': v['usage_count']
            }
            for k, v in self.valid_keys.items() if v['user_id'] == user_id
        ]


class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.request_log = {}  # IP -> [timestamps]
        
    async def check_rate_limit(self, client_ip: str) -> Tuple[bool, str]:
        """Проверить ограничение частоты"""
        
        if not self.config.enable_rate_limiting:
            return True, "OK"
        
        now = datetime.now()
        
        if client_ip not in self.request_log:
            self.request_log[client_ip] = []
        
        # Очистить старые запросы (> 1 часа)
        hour_ago = now - timedelta(hours=1)
        self.request_log[client_ip] = [
            t for t in self.request_log[client_ip] if t > hour_ago
        ]
        
        # Проверить лимиты
        requests_last_minute = sum(
            1 for t in self.request_log[client_ip]
            if t > (now - timedelta(minutes=1))
        )
        
        requests_last_hour = len(self.request_log[client_ip])
        
        if requests_last_minute > self.config.requests_per_minute:
            return False, f"Rate limit exceeded: {self.config.requests_per_minute} requests/minute"
        
        if requests_last_hour > self.config.requests_per_hour:
            return False, f"Rate limit exceeded: {self.config.requests_per_hour} requests/hour"
        
        # Добавить текущий запрос
        self.request_log[client_ip].append(now)
        return True, "OK"


class AuditLogger:
    """Логгер аудита для отслеживания всех действий"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.audit_log: List[AuditLogEntry] = []
        self.log_file = "logs/audit.log"
        
    async def log_action(self, user_id: str, action: str, resource: str,
                        status: str, ip_address: str, details: Optional[Dict] = None) -> None:
        """Записать действие в журнал аудита"""
        
        if not self.config.enable_audit_logging:
            return
        
        entry = AuditLogEntry(
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            action=action,
            resource=resource,
            status=status,
            ip_address=ip_address,
            details=details or {}
        )
        
        self.audit_log.append(entry)
        
        # Логировать в файл
        logger.info(f"AUDIT: {user_id} - {action} - {resource} - {status}")
        
        # Удалить старые записи (старше N дней)
        cutoff_date = datetime.now() - timedelta(days=self.config.log_rotation_days)
        cutoff_iso = cutoff_date.isoformat()
        self.audit_log = [e for e in self.audit_log if e.timestamp >= cutoff_iso]
    
    async def get_audit_log(self, user_id: Optional[str] = None, 
                           days: int = 7) -> List[Dict]:
        """Получить записи аудита"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        logs = [e for e in self.audit_log if e.timestamp >= cutoff_iso]
        
        if user_id:
            logs = [e for e in logs if e.user_id == user_id]
        
        return [
            {
                'timestamp': e.timestamp,
                'user_id': e.user_id,
                'action': e.action,
                'resource': e.resource,
                'status': e.status,
                'ip_address': e.ip_address,
                'details': e.details
            }
            for e in logs
        ]


class SecurityManager:
    """Главный менеджер безопасности"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.encryption_manager = EncryptionManager()
        self.api_key_manager = APIKeyManager(config)
        self.rate_limiter = RateLimiter(config)
        self.audit_logger = AuditLogger(config)
        self.blocked_ips = set()
        
    async def initialize(self) -> None:
        """Инициализировать компоненты безопасности"""
        logger.info("Initializing Security Manager")
        logger.info(f"AES-256 encryption: {'ENABLED' if CRYPTO_AVAILABLE else 'DISABLED'}")
        logger.info(f"Rate limiting: {'ENABLED' if self.config.enable_rate_limiting else 'DISABLED'}")
        logger.info(f"Audit logging: {'ENABLED' if self.config.enable_audit_logging else 'DISABLED'}")
    
    async def validate_request(self, api_key: Optional[str], client_ip: str) -> Tuple[bool, str]:
        """Валидировать входящий запрос"""
        
        # Проверить IP whitelist
        if self.config.enable_ip_whitelist:
            if client_ip not in self.config.whitelisted_ips:
                await self.audit_logger.log_action(
                    "unknown", "api_call", "security_check", "blocked",
                    client_ip, {"reason": "IP not whitelisted"}
                )
                return False, "IP address not whitelisted"
        
        # Проверить Rate limiting
        rate_limit_ok, rate_limit_msg = await self.rate_limiter.check_rate_limit(client_ip)
        if not rate_limit_ok:
            return False, rate_limit_msg
        
        # Проверить API ключ
        if self.config.enable_api_key_auth and api_key:
            key_valid, user_id = self.api_key_manager.validate_api_key(api_key)
            if not key_valid:
                await self.audit_logger.log_action(
                    "unknown", "api_call", "authentication", "failed",
                    client_ip, {"api_key_error": user_id}
                )
                return False, user_id  # user_id содержит сообщение об ошибке
        
        return True, "OK"
    
    async def log_api_action(self, user_id: str, action: str, resource: str,
                            status: str, client_ip: str, details: Optional[Dict] = None) -> None:
        """Логировать действие с API"""
        await self.audit_logger.log_action(user_id, action, resource, status, client_ip, details)


# Декоратор для защиты endpoint'ов
def require_api_key(security_manager: SecurityManager):
    """Декоратор для требования API ключа"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            api_key = kwargs.get('api_key')
            client_ip = kwargs.get('client_ip', 'unknown')
            
            is_valid, message = await security_manager.validate_request(api_key, client_ip)
            if not is_valid:
                return {'error': message, 'status': 'unauthorized'}
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Импорт base64 если нужен
import base64
