#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置模块
从VSCode设置或环境变量中读取数据库连接配置
"""

import os
import sys
import json
from typing import Dict, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# 默认配置
DEFAULT_CONFIG = {
    'mongo_uri': 'mongodb://localhost:27017/',
    'database_name': 'ims_viewer',
    'username': '',
    'password': '',
    'auth_database': 'admin'
}

def get_vscode_settings() -> Dict[str, str]:
    """
    从VSCode设置文件中读取配置
    """
    settings = {}
    
    # 尝试从多个可能的设置文件位置读取
    possible_settings_paths = [
        os.path.join(os.getcwd(), '.vscode', 'settings.json'),
        os.path.expanduser('~/.vscode/settings.json'),
        os.path.expanduser('~/AppData/Roaming/Code/User/settings.json'),  # Windows
        os.path.expanduser('~/Library/Application Support/Code/User/settings.json'),  # macOS
        os.path.expanduser('~/.config/Code/User/settings.json')  # Linux
    ]
    
    for settings_path in possible_settings_paths:
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    vscode_settings = json.load(f)
                    
                # 提取IMS Viewer相关设置
                if 'imsViewer.mongoUri' in vscode_settings:
                    settings['mongo_uri'] = vscode_settings['imsViewer.mongoUri']
                if 'imsViewer.databaseName' in vscode_settings:
                    settings['database_name'] = vscode_settings['imsViewer.databaseName']
                if 'imsViewer.mongoUsername' in vscode_settings:
                    settings['username'] = vscode_settings['imsViewer.mongoUsername']
                if 'imsViewer.mongoPassword' in vscode_settings:
                    settings['password'] = vscode_settings['imsViewer.mongoPassword']
                if 'imsViewer.mongoAuthDatabase' in vscode_settings:
                    settings['auth_database'] = vscode_settings['imsViewer.mongoAuthDatabase']
                    
                break
            except (json.JSONDecodeError, IOError):
                continue
                
    return settings

def get_database_config() -> Dict[str, str]:
    """
    获取数据库配置，优先级：环境变量 > VSCode设置 > 默认值
    """
    config = DEFAULT_CONFIG.copy()
    
    # 1. 从VSCode设置读取
    vscode_settings = get_vscode_settings()
    config.update(vscode_settings)
    
    # 2. 从环境变量读取（优先级最高）
    if os.environ.get('IMS_MONGO_URI'):
        config['mongo_uri'] = os.environ.get('IMS_MONGO_URI')
    if os.environ.get('IMS_DB_NAME'):
        config['database_name'] = os.environ.get('IMS_DB_NAME')
    if os.environ.get('IMS_MONGO_USERNAME'):
        config['username'] = os.environ.get('IMS_MONGO_USERNAME')
    if os.environ.get('IMS_MONGO_PASSWORD'):
        config['password'] = os.environ.get('IMS_MONGO_PASSWORD')
    if os.environ.get('IMS_MONGO_AUTH_DB'):
        config['auth_database'] = os.environ.get('IMS_MONGO_AUTH_DB')
    
    # 确保database_name不为空
    if not config['database_name']:
        config['database_name'] = 'ims_viewer'
    
    return config

def build_mongo_uri(config: Dict[str, str]) -> str:
    """
    根据配置构建MongoDB连接URI
    """
    base_uri = config['mongo_uri']
    username = config.get('username', '')
    password = config.get('password', '')
    auth_database = config.get('auth_database', 'admin')
    
    # 如果有用户名和密码，构建认证URI
    if username and password:
        # 解析原始URI
        if '://' in base_uri:
            protocol, rest = base_uri.split('://', 1)
            # 构建带认证的URI
            auth_uri = f"{protocol}://{username}:{password}@{rest}"
            
            # 添加认证数据库参数
            if '?' in auth_uri:
                auth_uri += f"&authSource={auth_database}"
            else:
                auth_uri += f"?authSource={auth_database}"
            
            return auth_uri
    
    return base_uri

def get_db_client() -> Optional[MongoClient]:
    """
    获取MongoDB数据库客户端（使用配置）
    """
    try:
        config = get_database_config()
        mongo_uri = build_mongo_uri(config)
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except (ConnectionFailure, Exception) as e:
        print(f"❌ 数据库连接失败: {e}", file=sys.stderr)
        return None

def get_database_name() -> str:
    """
    获取数据库名称
    """
    config = get_database_config()
    return config['database_name']

def get_database() -> Optional[object]:
    """
    获取数据库对象
    """
    client = get_db_client()
    if client:
        return client[get_database_name()]
    return None

def test_connection() -> bool:
    """
    测试数据库连接
    """
    try:
        config = get_database_config()
        print(f"测试数据库连接...")
        print(f"URI: {config['mongo_uri']}")
        print(f"数据库: {config['database_name']}")
        if config['username']:
            print(f"用户名: {config['username']}")
            print(f"认证数据库: {config['auth_database']}")
        
        client = get_db_client()
        if client:
            db = client[config['database_name']]
            # 测试数据库访问
            collections = db.list_collection_names()
            print(f"✅ 连接成功！找到 {len(collections)} 个集合")
            client.close()
            return True
        else:
            print("❌ 连接失败")
            return False
    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False

if __name__ == '__main__':
    print("=== 数据库配置测试 ===")
    config = get_database_config()
    print("当前配置:")
    for key, value in config.items():
        if key == 'password' and value:
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
    
    print("\n=== 连接测试 ===")
    test_connection()