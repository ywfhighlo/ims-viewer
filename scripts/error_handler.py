#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一错误处理模块
提供标准化的异常处理、错误记录和用户友好的错误信息
"""

import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union
from functools import wraps
from enhanced_logger import get_logger


class BusinessError(Exception):
    """业务逻辑错误"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'BUSINESS_ERROR'
        self.details = details or {}
        self.timestamp = datetime.now()


class DatabaseError(Exception):
    """数据库操作错误"""
    def __init__(self, message: str, operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.details = details or {}
        self.timestamp = datetime.now()


class ValidationError(Exception):
    """数据验证错误"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.value = value
        self.timestamp = datetime.now()


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, logger_name: str = "error_handler"):
        self.logger = get_logger(logger_name)
        self.error_counts = {}
    
    def handle_error(self, 
                    error: Exception, 
                    context: str = "", 
                    user_message: str = None,
                    log_level: str = "error") -> Dict[str, Any]:
        """统一错误处理"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # 记录错误统计
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 构建错误信息
        error_info = {
            'error_type': error_type,
            'error_message': error_message,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc() if log_level == "error" else None
        }
        
        # 添加特定错误类型的详细信息
        if isinstance(error, BusinessError):
            error_info.update({
                'error_code': error.error_code,
                'details': error.details
            })
        elif isinstance(error, DatabaseError):
            error_info.update({
                'operation': error.operation,
                'details': error.details
            })
        elif isinstance(error, ValidationError):
            error_info.update({
                'field': error.field,
                'value': error.value
            })
        
        # 记录日志
        log_message = f"{context}: {error_message}" if context else error_message
        
        if log_level == "error":
            self.logger.error(log_message, extra=error_info)
        elif log_level == "warning":
            self.logger.warning(log_message, extra=error_info)
        else:
            self.logger.info(log_message, extra=error_info)
        
        # 生成用户友好的错误信息
        if user_message:
            error_info['user_message'] = user_message
        else:
            error_info['user_message'] = self._generate_user_message(error)
        
        return error_info
    
    def _generate_user_message(self, error: Exception) -> str:
        """生成用户友好的错误信息"""
        if isinstance(error, DatabaseError):
            return "数据库操作失败，请检查数据库连接或联系管理员"
        elif isinstance(error, ValidationError):
            return f"数据验证失败：{error.message}"
        elif isinstance(error, BusinessError):
            return error.message
        elif "connection" in str(error).lower():
            return "网络连接失败，请检查网络设置"
        elif "permission" in str(error).lower():
            return "权限不足，请联系管理员"
        elif "not found" in str(error).lower():
            return "请求的资源不存在"
        else:
            return "操作失败，请稍后重试或联系管理员"
    
    def get_error_statistics(self) -> Dict[str, int]:
        """获取错误统计信息"""
        return self.error_counts.copy()
    
    def reset_statistics(self):
        """重置错误统计"""
        self.error_counts.clear()


def error_handler_decorator(logger_name: str = None, 
                          context: str = None,
                          reraise: bool = True,
                          default_return: Any = None):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(logger_name or func.__name__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or f"执行函数 {func.__name__}"
                error_info = handler.handle_error(e, error_context)
                
                if reraise:
                    raise
                else:
                    return default_return
        return wrapper
    return decorator


def safe_execute(func, 
                *args, 
                default_return: Any = None,
                logger_name: str = "safe_execute",
                context: str = None,
                **kwargs) -> Any:
    """安全执行函数，捕获并处理异常"""
    handler = ErrorHandler(logger_name)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_context = context or f"执行函数 {func.__name__ if hasattr(func, '__name__') else 'unknown'}"
        handler.handle_error(e, error_context)
        return default_return


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, 
                 max_retries: int = 3, 
                 delay: float = 1.0, 
                 backoff_factor: float = 2.0,
                 logger_name: str = "retry_handler"):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.logger = get_logger(logger_name)
    
    def execute_with_retry(self, 
                          func, 
                          *args, 
                          retry_on: tuple = (Exception,),
                          context: str = None,
                          **kwargs) -> Any:
        """带重试的函数执行"""
        import time
        
        last_exception = None
        current_delay = self.delay
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"第 {attempt + 1} 次重试执行: {context or 'unknown'}")
                
                return func(*args, **kwargs)
                
            except retry_on as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"执行失败，{current_delay}秒后重试 (第{attempt + 1}次): {str(e)}"
                    )
                    time.sleep(current_delay)
                    current_delay *= self.backoff_factor
                else:
                    self.logger.error(f"重试{self.max_retries}次后仍然失败: {str(e)}")
                    raise
            
            except Exception as e:
                # 不在重试范围内的异常直接抛出
                self.logger.error(f"执行失败（不重试）: {str(e)}")
                raise
        
        # 理论上不会到达这里
        if last_exception:
            raise last_exception


def retry_on_failure(max_retries: int = 3, 
                    delay: float = 1.0, 
                    backoff_factor: float = 2.0,
                    retry_on: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, delay, backoff_factor, func.__name__)
            return retry_handler.execute_with_retry(
                func, *args, 
                retry_on=retry_on, 
                context=func.__name__,
                **kwargs
            )
        return wrapper
    return decorator


# 全局错误处理器实例
global_error_handler = ErrorHandler("global")


if __name__ == '__main__':
    # 测试代码
    print("=== 错误处理模块测试 ===")
    
    # 测试基本错误处理
    handler = ErrorHandler("test")
    
    try:
        raise BusinessError("测试业务错误", "TEST_001", {"param": "value"})
    except Exception as e:
        error_info = handler.handle_error(e, "测试上下文")
        print(f"错误处理结果: {error_info['user_message']}")
    
    # 测试装饰器
    @error_handler_decorator(context="测试函数", reraise=False, default_return="默认值")
    def test_function():
        raise ValueError("测试错误")
    
    result = test_function()
    print(f"装饰器测试结果: {result}")
    
    # 测试重试机制
    @retry_on_failure(max_retries=2, delay=0.1)
    def flaky_function():
        import random
        if random.random() < 0.7:  # 70%概率失败
            raise ConnectionError("模拟连接失败")
        return "成功"
    
    try:
        result = flaky_function()
        print(f"重试测试结果: {result}")
    except Exception as e:
        print(f"重试失败: {e}")
    
    print(f"错误统计: {handler.get_error_statistics()}")