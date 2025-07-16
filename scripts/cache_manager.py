#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理器
实现基于内存的缓存机制，支持TTL和键值存储，提升业务视图查询性能
"""

import sys
import os
import json
import hashlib
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import OrderedDict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger


@dataclass
class CachedReport:
    """缓存报表数据模型"""
    cache_key: str
    view_name: str
    params: Dict[str, Any]
    data: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        # 处理datetime对象的序列化
        result['created_at'] = self.created_at.isoformat()
        result['expires_at'] = self.expires_at.isoformat()
        if self.last_accessed:
            result['last_accessed'] = self.last_accessed.isoformat()
        return result


class CacheManager:
    """缓存管理器类"""
    
    def __init__(self, 
                 max_size: int = 1000,
                 default_ttl: int = 300,
                 cleanup_interval: int = 60,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
            cleanup_interval: 清理间隔（秒）
            logger: 日志记录器
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.logger = logger or EnhancedLogger("cache_manager")
        
        # 使用OrderedDict实现LRU缓存
        self._cache: OrderedDict[str, CachedReport] = OrderedDict()
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'total_requests': 0
        }
        
        # 启动后台清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        
        self.logger.info(f"缓存管理器初始化完成，最大容量: {max_size}, 默认TTL: {default_ttl}秒")
    
    def generate_cache_key(self, view_name: str, params: Dict[str, Any]) -> str:
        """
        生成缓存键
        
        Args:
            view_name: 视图名称
            params: 查询参数
            
        Returns:
            缓存键字符串
        """
        # 创建参数的标准化字符串
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        
        # 生成MD5哈希
        key_string = f"{view_name}:{sorted_params}"
        cache_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        self.logger.debug(f"生成缓存键: {view_name} -> {cache_key}")
        return cache_key
    
    def get_cached_report(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取缓存的报表数据
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或过期则返回None
        """
        with self._lock:
            self._stats['total_requests'] += 1
            
            if cache_key not in self._cache:
                self._stats['misses'] += 1
                self.logger.debug(f"缓存未命中: {cache_key}")
                return None
            
            cached_report = self._cache[cache_key]
            
            # 检查是否过期
            if cached_report.is_expired():
                self.logger.debug(f"缓存已过期: {cache_key}")
                del self._cache[cache_key]
                self._stats['misses'] += 1
                self._stats['expirations'] += 1
                return None
            
            # 更新访问统计
            cached_report.hit_count += 1
            cached_report.last_accessed = datetime.now()
            self._stats['hits'] += 1
            
            # 移动到末尾（LRU）
            self._cache.move_to_end(cache_key)
            
            self.logger.debug(f"缓存命中: {cache_key}, 命中次数: {cached_report.hit_count}")
            return cached_report.data.copy()  # 返回数据副本
    
    def set_cached_report(self, 
                         cache_key: str, 
                         view_name: str,
                         params: Dict[str, Any],
                         data: List[Dict[str, Any]], 
                         ttl: Optional[int] = None) -> bool:
        """
        设置缓存报表数据
        
        Args:
            cache_key: 缓存键
            view_name: 视图名称
            params: 查询参数
            data: 要缓存的数据
            ttl: 生存时间（秒），为None时使用默认TTL
            
        Returns:
            是否成功设置缓存
        """
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            with self._lock:
                # 检查缓存大小，如果超过限制则清理最旧的条目
                while len(self._cache) >= self.max_size:
                    oldest_key, _ = self._cache.popitem(last=False)
                    self._stats['evictions'] += 1
                    self.logger.debug(f"缓存容量已满，清理最旧条目: {oldest_key}")
                
                # 创建缓存条目
                now = datetime.now()
                expires_at = now + timedelta(seconds=ttl)
                
                cached_report = CachedReport(
                    cache_key=cache_key,
                    view_name=view_name,
                    params=params.copy(),
                    data=data.copy(),  # 存储数据副本
                    created_at=now,
                    expires_at=expires_at,
                    hit_count=0,
                    last_accessed=now
                )
                
                self._cache[cache_key] = cached_report
                
                self.logger.debug(f"缓存设置成功: {cache_key}, TTL: {ttl}秒, 数据量: {len(data)} 条")
                return True
                
        except Exception as e:
            self.logger.error(f"设置缓存失败: {cache_key}, 错误: {str(e)}")
            return False
    
    def invalidate_cache(self, pattern: str) -> int:
        """
        失效匹配模式的缓存
        
        Args:
            pattern: 匹配模式（支持通配符*）
            
        Returns:
            失效的缓存条目数量
        """
        import fnmatch
        
        with self._lock:
            keys_to_remove = []
            
            for cache_key, cached_report in self._cache.items():
                # 检查缓存键或视图名称是否匹配模式
                if (fnmatch.fnmatch(cache_key, pattern) or 
                    fnmatch.fnmatch(cached_report.view_name, pattern)):
                    keys_to_remove.append(cache_key)
            
            # 删除匹配的缓存条目
            for key in keys_to_remove:
                del self._cache[key]
            
            self.logger.info(f"缓存失效完成，模式: {pattern}, 失效条目数: {len(keys_to_remove)}")
            return len(keys_to_remove)
    
    def clear_cache(self) -> int:
        """
        清空所有缓存
        
        Returns:
            清理的缓存条目数量
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"缓存已清空，清理条目数: {count}")
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        with self._lock:
            hit_rate = 0.0
            if self._stats['total_requests'] > 0:
                hit_rate = self._stats['hits'] / self._stats['total_requests']
            
            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate * 100, 2),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'total_requests': self._stats['total_requests'],
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'memory_usage_estimate': self._estimate_memory_usage()
            }
    
    def get_cache_info(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取缓存条目信息
        
        Args:
            limit: 返回条目数量限制
            
        Returns:
            缓存条目信息列表
        """
        with self._lock:
            cache_info = []
            
            # 按最后访问时间排序
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed or x[1].created_at,
                reverse=True
            )
            
            for cache_key, cached_report in sorted_items[:limit]:
                info = {
                    'cache_key': cache_key,
                    'view_name': cached_report.view_name,
                    'params': cached_report.params,
                    'data_count': len(cached_report.data),
                    'created_at': cached_report.created_at.isoformat(),
                    'expires_at': cached_report.expires_at.isoformat(),
                    'hit_count': cached_report.hit_count,
                    'last_accessed': cached_report.last_accessed.isoformat() if cached_report.last_accessed else None,
                    'is_expired': cached_report.is_expired()
                }
                cache_info.append(info)
            
            return cache_info
    
    def _cleanup_expired(self):
        """后台清理过期缓存的线程函数"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                
                with self._lock:
                    expired_keys = []
                    
                    for cache_key, cached_report in self._cache.items():
                        if cached_report.is_expired():
                            expired_keys.append(cache_key)
                    
                    # 删除过期的缓存条目
                    for key in expired_keys:
                        del self._cache[key]
                        self._stats['expirations'] += 1
                    
                    if expired_keys:
                        self.logger.debug(f"后台清理过期缓存: {len(expired_keys)} 个条目")
                        
            except Exception as e:
                self.logger.error(f"后台清理缓存失败: {str(e)}")
    
    def _estimate_memory_usage(self) -> str:
        """估算内存使用量"""
        try:
            total_size = 0
            for cached_report in self._cache.values():
                # 粗略估算每个缓存条目的内存使用
                data_size = len(json.dumps(cached_report.data, ensure_ascii=False).encode('utf-8'))
                params_size = len(json.dumps(cached_report.params, ensure_ascii=False).encode('utf-8'))
                total_size += data_size + params_size + 1024  # 加上对象开销
            
            # 转换为可读格式
            if total_size < 1024:
                return f"{total_size} B"
            elif total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size / (1024 * 1024):.1f} MB"
                
        except Exception:
            return "未知"


# 全局缓存管理器实例
_global_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例（单例模式）
    
    Returns:
        缓存管理器实例
    """
    global _global_cache_manager
    
    if _global_cache_manager is None:
        with _cache_lock:
            if _global_cache_manager is None:
                _global_cache_manager = CacheManager()
    
    return _global_cache_manager


def cache_report_data(view_name: str, 
                     params: Dict[str, Any], 
                     data_generator: Callable[[], List[Dict[str, Any]]],
                     ttl: Optional[int] = None,
                     cache_manager: Optional[CacheManager] = None) -> List[Dict[str, Any]]:
    """
    缓存装饰器函数，用于缓存报表数据
    
    Args:
        view_name: 视图名称
        params: 查询参数
        data_generator: 数据生成函数
        ttl: 缓存TTL（秒）
        cache_manager: 缓存管理器实例
        
    Returns:
        报表数据
    """
    if cache_manager is None:
        cache_manager = get_cache_manager()
    
    # 生成缓存键
    cache_key = cache_manager.generate_cache_key(view_name, params)
    
    # 尝试从缓存获取数据
    cached_data = cache_manager.get_cached_report(cache_key)
    if cached_data is not None:
        return cached_data
    
    # 缓存未命中，生成新数据
    try:
        data = data_generator()
        
        # 将数据存入缓存
        cache_manager.set_cached_report(cache_key, view_name, params, data, ttl)
        
        return data
        
    except Exception as e:
        cache_manager.logger.error(f"数据生成失败: {view_name}, 错误: {str(e)}")
        raise


def main():
    """测试缓存管理器功能"""
    logger = EnhancedLogger("cache_manager_test")
    
    try:
        # 创建缓存管理器
        cache_manager = CacheManager(max_size=5, default_ttl=10, logger=logger)
        
        print("=== 缓存管理器测试 ===")
        
        # 测试缓存设置和获取
        print("\n1. 测试缓存设置和获取")
        test_data = [
            {'id': 1, 'name': '测试数据1'},
            {'id': 2, 'name': '测试数据2'}
        ]
        
        cache_key = cache_manager.generate_cache_key('test_view', {'param1': 'value1'})
        success = cache_manager.set_cached_report(cache_key, 'test_view', {'param1': 'value1'}, test_data, 5)
        print(f"缓存设置结果: {success}")
        
        cached_data = cache_manager.get_cached_report(cache_key)
        print(f"缓存获取结果: {len(cached_data) if cached_data else 0} 条数据")
        
        # 测试缓存统计
        print("\n2. 测试缓存统计")
        stats = cache_manager.get_cache_stats()
        print(f"缓存统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
        
        # 测试缓存信息
        print("\n3. 测试缓存信息")
        cache_info = cache_manager.get_cache_info()
        print(f"缓存条目数: {len(cache_info)}")
        
        # 测试缓存装饰器
        print("\n4. 测试缓存装饰器")
        def generate_test_data():
            return [{'id': 3, 'name': '装饰器测试数据'}]
        
        result = cache_report_data('decorator_test', {'test': True}, generate_test_data, cache_manager=cache_manager)
        print(f"装饰器测试结果: {len(result)} 条数据")
        
        # 再次调用，应该从缓存获取
        result2 = cache_report_data('decorator_test', {'test': True}, generate_test_data, cache_manager=cache_manager)
        print(f"第二次调用结果: {len(result2)} 条数据")
        
        # 测试缓存失效
        print("\n5. 测试缓存失效")
        invalidated = cache_manager.invalidate_cache('test_*')
        print(f"失效缓存条目数: {invalidated}")
        
        # 最终统计
        print("\n6. 最终缓存统计")
        final_stats = cache_manager.get_cache_stats()
        print(f"最终统计: {json.dumps(final_stats, ensure_ascii=False, indent=2)}")
        
        print("\n缓存管理器测试完成！")
        
    except Exception as e:
        logger.error(f"缓存管理器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()