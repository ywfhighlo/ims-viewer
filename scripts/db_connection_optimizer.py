#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接优化器
智能选择最快的数据库连接方式，避免长时间等待
"""

import os
import time
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from enhanced_logger import get_logger

class DatabaseConnectionOptimizer:
    """数据库连接优化器"""
    
    def __init__(self):
        self.logger = get_logger("db_connection_optimizer")
        self._connection_cache = {}
        self._last_successful_config = None
        
    def get_optimized_connection(self) -> Database:
        """
        获取优化的数据库连接
        优先使用上次成功的连接配置，避免重复尝试失败的连接
        """
        # 如果有上次成功的配置，优先使用
        if self._last_successful_config:
            try:
                return self._connect_with_config(self._last_successful_config)
            except Exception as e:
                self.logger.warning(f"上次成功的配置现在失败了: {str(e)}")
                self._last_successful_config = None
        
        # 尝试多种连接配置，按优先级排序
        connection_configs = self._get_connection_configs()
        
        for config_name, config in connection_configs.items():
            try:
                self.logger.info(f"尝试连接配置: {config_name}")
                start_time = time.time()
                
                db = self._connect_with_config(config)
                
                connection_time = time.time() - start_time
                self.logger.info(f"连接成功: {config_name}, 耗时: {connection_time:.3f}秒")
                
                # 记录成功的配置
                self._last_successful_config = config
                return db
                
            except Exception as e:
                connection_time = time.time() - start_time
                self.logger.warning(f"连接失败: {config_name}, 耗时: {connection_time:.3f}秒, 错误: {str(e)}")
                continue
        
        # 所有配置都失败了
        raise Exception("所有数据库连接配置都失败")
    
    def _get_connection_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取连接配置列表，按优先级排序"""
        configs = {}
        
        # 1. 本地MongoDB (最快)
        configs['local_default'] = {
            'host': 'localhost',
            'port': 27017,
            'database_name': 'ims_database',
            'timeout': 2
        }
        
        # 2. 本地MongoDB (备用端口)
        configs['local_alt'] = {
            'host': '127.0.0.1',
            'port': 27017,
            'database_name': 'ims_database',
            'timeout': 2
        }
        
        # 3. 配置文件中的远程服务器 (较慢，但可能有数据)
        configs['remote_config'] = {
            'host': '192.168.1.100',
            'port': 27018,
            'database_name': 'ims_database',
            'timeout': 3
        }
        
        # 4. 其他可能的本地端口
        configs['local_alt_port'] = {
            'host': 'localhost',
            'port': 27018,
            'database_name': 'ims_database',
            'timeout': 2
        }
        
        return configs
    
    def _connect_with_config(self, config: Dict[str, Any]) -> Database:
        """使用指定配置连接数据库"""
        client = MongoClient(
            host=config['host'],
            port=config['port'],
            serverSelectionTimeoutMS=config['timeout'] * 1000,
            connectTimeoutMS=config['timeout'] * 1000,
            socketTimeoutMS=config['timeout'] * 1000,
            maxPoolSize=10,
            retryWrites=True
        )
        
        # 测试连接
        client.admin.command('ping')
        
        # 获取数据库
        db = client[config['database_name']]
        
        # 验证数据库是否有数据
        collections = db.list_collection_names()
        if not collections:
            self.logger.warning(f"数据库 {config['database_name']} 没有集合")
        else:
            self.logger.info(f"数据库验证成功，找到 {len(collections)} 个集合")
        
        return db

# 全局优化器实例
_optimizer = DatabaseConnectionOptimizer()

def get_fast_database_connection() -> Database:
    """
    获取快速数据库连接
    这是一个优化的连接函数，会智能选择最快的连接方式
    """
    return _optimizer.get_optimized_connection()

def main():
    """测试数据库连接优化器"""
    print("=== 数据库连接优化器测试 ===")
    
    try:
        start_time = time.time()
        db = get_fast_database_connection()
        total_time = time.time() - start_time
        
        collections = db.list_collection_names()
        print(f"✅ 连接成功！")
        print(f"📊 数据库: {db.name}")
        print(f"📁 集合数量: {len(collections)}")
        print(f"⏱️  总耗时: {total_time:.3f}秒")
        
        if collections:
            print(f"📋 集合列表: {', '.join(collections[:5])}{'...' if len(collections) > 5 else ''}")
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    main()