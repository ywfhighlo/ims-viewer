#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接公共模块
提供统一的数据库连接接口，供所有业务视图脚本使用
"""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from database_config import get_database_config, build_mongo_uri
from config_manager import get_database_config as get_new_database_config
from enhanced_logger import get_logger
from error_handler import retry_on_failure, DatabaseError


class DatabaseConnection:
    """数据库连接管理类"""
    
    _instance = None
    _client = None
    _database = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance
    
    def get_client(self) -> Optional[MongoClient]:
        """获取MongoDB客户端"""
        if self._client is None:
            try:
                config = get_database_config()
                mongo_uri = build_mongo_uri(config)
                self._client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
                # 测试连接
                self._client.admin.command('ping')
            except Exception as e:
                raise Exception(f"数据库连接失败: {str(e)}")
        return self._client
    
    def get_database(self) -> Database:
        """获取数据库对象"""
        if self._database is None:
            client = self.get_client()
            config = get_database_config()
            self._database = client[config['database_name']]
        return self._database
    
    def close(self):
        """关闭数据库连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None


# 全局数据库连接实例
_db_connection = DatabaseConnection()


@retry_on_failure(max_retries=2, delay=0.5, retry_on=(ConnectionError, DatabaseError))
def get_database_connection() -> Database:
    """
    获取MongoDB数据库连接（优化版）
    
    Returns:
        Database: MongoDB数据库对象
        
    Raises:
        Exception: 当数据库连接失败时抛出异常
    """
    logger = get_logger("db_connection")
    
    try:
        # 首先尝试使用优化的连接器
        from db_connection_optimizer import get_fast_database_connection
        db = get_fast_database_connection()
        logger.info("使用优化连接器连接数据库成功")
        return db
        
    except Exception as optimizer_error:
        logger.warning("优化连接器失败，尝试配置管理器", error=str(optimizer_error))
        
        try:
            # 尝试使用新的配置管理器（快速失败）
            db_config = get_new_database_config()
            logger.info("使用配置管理器连接数据库", 
                       host=db_config.host, 
                       port=db_config.port,
                       database=db_config.database_name)
            
            # 创建MongoDB客户端，使用更短的超时时间
            client = MongoClient(
                host=db_config.host,
                port=db_config.port,
                username=db_config.username,
                password=db_config.password,
                serverSelectionTimeoutMS=3000,  # 3秒超时
                connectTimeoutMS=2000,  # 连接超时2秒
                socketTimeoutMS=3000,   # Socket超时3秒
                maxPoolSize=db_config.max_pool_size,
                retryWrites=db_config.retry_writes
            )
            
            # 测试连接
            client.admin.command('ping')
            
            # 获取数据库
            db = client[db_config.database_name]
            
            logger.info("配置管理器连接成功", database=db_config.database_name)
            return db
            
        except Exception as config_error:
            logger.warning("配置管理器连接失败，尝试原有方法", error=str(config_error))
            
            try:
                # 回退到原有的连接方法
                db = _db_connection.get_database()
                logger.info("使用原有配置连接数据库成功")
                return db
            except Exception as fallback_error:
                logger.error("所有数据库连接方法都失败", 
                            optimizer_error=str(optimizer_error),
                            config_error=str(config_error),
                            fallback_error=str(fallback_error))
                raise DatabaseError(
                    "数据库连接失败",
                    operation="get_connection",
                    details={
                        "optimizer_error": str(optimizer_error),
                        "config_error": str(config_error),
                        "fallback_error": str(fallback_error)
                    }
                )


def close_database_connection():
    """关闭数据库连接"""
    _db_connection.close()


def test_database_connection() -> bool:
    """
    测试数据库连接
    
    Returns:
        bool: 连接成功返回True，失败返回False
    """
    try:
        db = get_database_connection()
        # 尝试执行一个简单的操作
        db.list_collection_names()
        return True
    except Exception:
        return False


if __name__ == '__main__':
    print("=== 数据库连接测试 ===")
    try:
        db = get_database_connection()
        collections = db.list_collection_names()
        print(f"✅ 连接成功！数据库: {db.name}")
        print(f"📊 找到 {len(collections)} 个集合: {', '.join(collections[:5])}{'...' if len(collections) > 5 else ''}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    finally:
        close_database_connection()