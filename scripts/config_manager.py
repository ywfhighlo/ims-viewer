#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
统一管理应用配置、数据库设置和业务参数
"""

import os
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enhanced_logger import get_logger


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = "localhost"
    port: int = 27017
    database_name: str = "ims_database"
    username: Optional[str] = None
    password: Optional[str] = None
    connection_timeout: int = 30
    max_pool_size: int = 100
    retry_writes: bool = True
    
    def to_uri(self) -> str:
        """生成MongoDB连接URI"""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""
        
        return f"mongodb://{auth}{self.host}:{self.port}/{self.database_name}"


@dataclass
class ReportConfig:
    """报告配置"""
    default_page_size: int = 100
    max_records_per_report: int = 10000
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    currency_symbol: str = "¥"
    decimal_places: int = 2
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = False
    log_dir: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    performance_threshold: float = 1.0  # 秒


@dataclass
class ValidationConfig:
    """验证配置"""
    strict_mode: bool = False
    allow_empty_strings: bool = True
    max_string_length: int = 1000
    date_formats: list = None
    required_fields_by_table: Dict[str, list] = None
    
    def __post_init__(self):
        if self.date_formats is None:
            self.date_formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y/%m/%d %H:%M:%S"
            ]
        
        if self.required_fields_by_table is None:
            self.required_fields_by_table = {
                "inventory": ["product_name", "quantity"],
                "sales": ["order_id", "amount"],
                "purchases": ["purchase_id", "amount"],
                "customers": ["customer_name"],
                "suppliers": ["supplier_name"]
            }


@dataclass
class AppConfig:
    """应用配置"""
    database: DatabaseConfig
    report: ReportConfig
    logging: LoggingConfig
    validation: ValidationConfig
    debug_mode: bool = False
    environment: str = "development"
    version: str = "1.0.0"
    custom_output_path: Optional[str] = None


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = None):
        self.logger = get_logger("config_manager")
        self.config_file = config_file or self._get_default_config_path()
        self._config: Optional[AppConfig] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        script_dir = Path(__file__).parent
        return str(script_dir / "config.json")
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._config = self._dict_to_config(config_data)
                self.logger.info("配置文件加载成功", config_file=self.config_file)
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                self._config = self._create_default_config()
                self.save_config()  # 保存默认配置
        except Exception as e:
            self.logger.error("加载配置文件失败，使用默认配置", error=str(e))
            self._config = self._create_default_config()
    
    def _create_default_config(self) -> AppConfig:
        """创建默认配置"""
        return AppConfig(
            database=DatabaseConfig(),
            report=ReportConfig(),
            logging=LoggingConfig(),
            validation=ValidationConfig()
        )
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> AppConfig:
        """将字典转换为配置对象"""
        return AppConfig(
            database=DatabaseConfig(**config_dict.get('database', {})),
            report=ReportConfig(**config_dict.get('report', {})),
            logging=LoggingConfig(**config_dict.get('logging', {})),
            validation=ValidationConfig(**config_dict.get('validation', {})),
            debug_mode=config_dict.get('debug_mode', False),
            environment=config_dict.get('environment', 'development'),
            version=config_dict.get('version', '1.0.0'),
            custom_output_path=config_dict.get('customOutputPath')
        )
    
    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            'customOutputPath': config.custom_output_path,
            'database': asdict(config.database),
            'report': asdict(config.report),
            'logging': asdict(config.logging),
            'validation': asdict(config.validation),
            'debug_mode': config.debug_mode,
            'environment': config.environment,
            'version': config.version
        }
    
    def get_config(self) -> AppConfig:
        """获取配置"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def get_database_config(self) -> DatabaseConfig:
        """获取数据库配置"""
        return self.get_config().database
    
    def get_report_config(self) -> ReportConfig:
        """获取报告配置"""
        return self.get_config().report
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        return self.get_config().logging
    
    def get_validation_config(self) -> ValidationConfig:
        """获取验证配置"""
        return self.get_config().validation
    
    def update_config(self, **kwargs):
        """更新配置"""
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif key == 'customOutputPath':
                config.custom_output_path = value
            else:
                self.logger.warning(f"未知的配置项: {key}")
        
        self._config = config
        self.logger.info("配置已更新", updated_keys=list(kwargs.keys()))
    
    def update_database_config(self, **kwargs):
        """更新数据库配置"""
        config = self.get_config()
        db_config = config.database
        
        for key, value in kwargs.items():
            if hasattr(db_config, key):
                setattr(db_config, key, value)
            else:
                self.logger.warning(f"未知的数据库配置项: {key}")
        
        self.logger.info("数据库配置已更新", updated_keys=list(kwargs.keys()))
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_dict = self._config_to_dict(self.get_config())
            
            # 确保配置目录存在
            config_dir = Path(self.config_file).parent
            config_dir.mkdir(exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            self.logger.info("配置已保存", config_file=self.config_file)
        except Exception as e:
            self.logger.error("保存配置文件失败", error=str(e))
    
    def get_env_override(self, key: str, default: Any = None) -> Any:
        """从环境变量获取配置覆盖"""
        env_key = f"IMS_{key.upper()}"
        return os.getenv(env_key, default)
    
    def apply_env_overrides(self):
        """应用环境变量覆盖"""
        config = self.get_config()
        
        # 数据库配置覆盖
        db_host = self.get_env_override('db_host')
        if db_host:
            config.database.host = db_host
        
        db_port = self.get_env_override('db_port')
        if db_port:
            try:
                config.database.port = int(db_port)
            except ValueError:
                self.logger.warning(f"无效的数据库端口: {db_port}")
        
        db_name = self.get_env_override('db_name')
        if db_name:
            config.database.database_name = db_name
        
        db_user = self.get_env_override('db_user')
        if db_user:
            config.database.username = db_user
        
        db_pass = self.get_env_override('db_password')
        if db_pass:
            config.database.password = db_pass
        
        # 日志级别覆盖
        log_level = self.get_env_override('log_level')
        if log_level:
            config.logging.level = log_level.upper()
        
        # 调试模式覆盖
        debug_mode = self.get_env_override('debug_mode')
        if debug_mode:
            config.debug_mode = debug_mode.lower() in ('true', '1', 'yes')
        
        self.logger.info("环境变量覆盖已应用")
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        config = self.get_config()
        errors = []
        
        # 验证数据库配置
        if not config.database.host:
            errors.append("数据库主机不能为空")
        
        if not (1 <= config.database.port <= 65535):
            errors.append("数据库端口必须在1-65535范围内")
        
        if not config.database.database_name:
            errors.append("数据库名称不能为空")
        
        # 验证报告配置
        if config.report.default_page_size <= 0:
            errors.append("默认页面大小必须大于0")
        
        if config.report.max_records_per_report <= 0:
            errors.append("最大记录数必须大于0")
        
        # 验证日志配置
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if config.logging.level not in valid_log_levels:
            errors.append(f"日志级别必须是: {', '.join(valid_log_levels)}")
        
        if errors:
            for error in errors:
                self.logger.error(f"配置验证失败: {error}")
            return False
        
        self.logger.info("配置验证通过")
        return True

    def get_custom_output_path(self) -> Optional[str]:
        """获取自定义输出路径"""
        return self.get_config().custom_output_path

    def set_custom_output_path(self, path: str):
        """设置自定义输出路径"""
        config = self.get_config()
        config.custom_output_path = path
        self._config = config
        self.logger.info("自定义输出路径已更新", custom_output_path=path)


# 全局配置管理器实例
_config_manager = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.apply_env_overrides()
    return _config_manager


def get_config() -> AppConfig:
    """获取应用配置"""
    return get_config_manager().get_config()


def get_database_config() -> DatabaseConfig:
    """获取数据库配置"""
    return get_config_manager().get_database_config()


def get_report_config() -> ReportConfig:
    """获取报告配置"""
    return get_config_manager().get_report_config()


def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    return get_config_manager().get_logging_config()


def get_validation_config() -> ValidationConfig:
    """获取验证配置"""
    return get_config_manager().get_validation_config()


if __name__ == '__main__':
    # 测试代码
    print("=== 配置管理模块测试 ===")
    
    # 创建配置管理器
    config_mgr = ConfigManager()
    
    # 获取配置
    config = config_mgr.get_config()
    print(f"数据库主机: {config.database.host}")
    print(f"数据库端口: {config.database.port}")
    print(f"日志级别: {config.logging.level}")
    print(f"调试模式: {config.debug_mode}")
    
    # 更新配置
    config_mgr.update_database_config(host="192.168.1.100", port=27018)
    
    # 验证配置
    is_valid = config_mgr.validate_config()
    print(f"配置验证结果: {is_valid}")
    
    # 保存配置
    config_mgr.save_config()
    
    print("配置管理测试完成")