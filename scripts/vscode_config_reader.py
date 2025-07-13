#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDE配置读取工具
支持从多种IDE（Trae、VS Code、Cursor等）的工作区配置中读取IMS Viewer插件的设置
"""

import json
import os
import tempfile
import glob
from pathlib import Path
from typing import Dict, Any, Optional


class IDEConfigReader:
    """IDE配置读取器，支持多种IDE"""
    
    def __init__(self, workspace_path: str = None):
        """
        初始化配置读取器
        
        Args:
            workspace_path: 工作区路径，如果不提供则自动检测
        """
        self.workspace_path = workspace_path or self._detect_workspace_path()
        self.settings_file = os.path.join(self.workspace_path, '.vscode', 'settings.json')
        self._settings_cache = None
        self._detected_ide = None
    
    def _detect_workspace_path(self) -> str:
        """自动检测工作区路径"""
        # 从当前脚本路径向上查找
        current_path = Path(__file__).parent.parent
        
        # 检查是否存在package.json（扩展标识）
        if (current_path / 'package.json').exists():
            return str(current_path)
        
        # 如果找不到，返回当前目录
        return os.getcwd()
    
    def _detect_ide_and_extension_path(self) -> tuple[str, str]:
        """
        检测当前使用的IDE和扩展安装路径
        
        Returns:
            (ide_name, extension_path) 元组
        """
        if self._detected_ide:
            return self._detected_ide
        
        user_home = os.path.expanduser("~")
        
        # 检测各种IDE的扩展目录，使用更灵活的匹配模式
        ide_patterns = [
            ("trae", f"{user_home}/.trae/extensions/*ims-viewer*"),
            ("cursor", f"{user_home}/.cursor/extensions/*ims-viewer*"),
            ("vscode", f"{user_home}/.vscode/extensions/*ims-viewer*"),
            ("vscode-insiders", f"{user_home}/.vscode-insiders/extensions/*ims-viewer*"),
        ]
        
        for ide_name, pattern in ide_patterns:
            matches = glob.glob(pattern)
            if matches:
                # 选择最新的扩展版本
                extension_path = max(matches, key=os.path.getmtime)
                self._detected_ide = (ide_name, extension_path)
                print(f"检测到IDE: {ide_name}, 扩展路径: {extension_path}")
                return self._detected_ide
        
        # 如果标准模式没找到，尝试更宽泛的搜索
        print("标准模式未找到扩展，尝试宽泛搜索...")
        broad_patterns = [
            ("trae", f"{user_home}/.trae/extensions/*/*"),
            ("cursor", f"{user_home}/.cursor/extensions/*/*"),
            ("vscode", f"{user_home}/.vscode/extensions/*/*"),
        ]
        
        for ide_name, pattern in broad_patterns:
            matches = glob.glob(pattern)
            for match in matches:
                if 'ims-viewer' in os.path.basename(match).lower():
                    self._detected_ide = (ide_name, match)
                    print(f"宽泛搜索找到IDE: {ide_name}, 扩展路径: {match}")
                    return self._detected_ide
        
        # 如果仍然没有找到扩展，返回默认值
        print("未找到任何IDE扩展")
        self._detected_ide = ("unknown", "")
        return self._detected_ide
    
    def _get_data_directory_from_extension(self) -> Optional[str]:
        """从扩展目录获取数据目录路径"""
        ide_name, extension_path = self._detect_ide_and_extension_path()
        
        if extension_path and os.path.exists(extension_path):
            docs_path = os.path.join(extension_path, 'docs')
            if os.path.exists(docs_path):
                print(f"使用{ide_name}扩展目录: {docs_path}")
                return docs_path
        
        return None
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载IDE设置"""
        if self._settings_cache is not None:
            return self._settings_cache
        
        settings = {}
        
        # 1. 尝试读取工作区设置
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        # 处理JSON注释（IDE允许注释）
                        lines = content.split('\n')
                        clean_lines = []
                        for line in lines:
                            # 移除行注释
                            if '//' in line:
                                line = line[:line.index('//')]
                            clean_lines.append(line)
                        clean_content = '\n'.join(clean_lines)
                        settings.update(json.loads(clean_content))
                        print(f"已加载工作区设置: {self.settings_file}")
            except (json.JSONDecodeError, Exception) as e:
                print(f"警告: 无法读取工作区设置文件: {e}")
        
        # 2. 尝试读取用户全局设置（支持多种IDE）
        user_home = os.path.expanduser("~")
        user_settings_paths = [
            # Trae IDE
            os.path.join(user_home, ".trae", "User", "settings.json"),
            # Cursor IDE
            os.path.join(user_home, ".cursor", "User", "settings.json"),
            # VS Code
            os.path.join(user_home, "AppData", "Roaming", "Code", "User", "settings.json"),  # Windows
            os.path.join(user_home, ".vscode", "settings.json"),  # Linux/Mac
            os.path.join(user_home, "Library", "Application Support", "Code", "User", "settings.json"),  # Mac
            # VS Code Insiders
            os.path.join(user_home, "AppData", "Roaming", "Code - Insiders", "User", "settings.json"),  # Windows
        ]
        
        for user_settings_path in user_settings_paths:
            if os.path.exists(user_settings_path):
                try:
                    with open(user_settings_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # 处理JSON注释
                            lines = content.split('\n')
                            clean_lines = []
                            for line in lines:
                                if '//' in line:
                                    line = line[:line.index('//')]
                                clean_lines.append(line)
                            clean_content = '\n'.join(clean_lines)
                            user_settings = json.loads(clean_content)
                            
                            # 只添加IMS Viewer相关的设置，工作区设置优先
                            for key, value in user_settings.items():
                                if key.startswith('imsViewer.') and key not in settings:
                                    settings[key] = value
                            
                            print(f"已加载用户设置: {user_settings_path}")
                            break
                except (json.JSONDecodeError, Exception) as e:
                    print(f"警告: 无法读取用户设置文件 {user_settings_path}: {e}")
        
        # 3. 如果仍然没有找到设置，尝试从环境变量或命令行参数读取
        if not any(key.startswith('imsViewer.') for key in settings.keys()):
            print("警告: 未找到IDE设置，使用默认配置")
            # 可以在这里添加从环境变量读取的逻辑
        
        self._settings_cache = settings
        return settings
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取设置值
        
        Args:
            key: 设置键名（如 'imsViewer.databaseName'）
            default: 默认值
            
        Returns:
            设置值或默认值
        """
        settings = self._load_settings()
        return settings.get(key, default)
    
    def get_database_name(self) -> str:
        """获取数据库名称"""
        return self.get_setting('imsViewer.databaseName', 'ims_database')
    
    def get_output_mode(self) -> str:
        """获取输出模式"""
        return self.get_setting('imsViewer.outputMode', 'development')
    
    def get_custom_output_path(self) -> str:
        """获取自定义输出路径"""
        return self.get_setting('imsViewer.customOutputPath', '')
    
    def get_data_directory(self) -> str:
        """
        根据输出模式获取数据目录路径
        优先级：1. 设置中的自定义目录 2. 工作区docs目录 3. 扩展目录
        
        Returns:
            数据目录的绝对路径
        """
        output_mode = self.get_output_mode()
        
        # 1. 优先使用设置中的自定义目录（custom模式或设置了customOutputPath）
        custom_path = self.get_custom_output_path()
        if custom_path and os.path.exists(custom_path):
            print(f"使用设置中的自定义目录: {custom_path}")
            return custom_path
        elif custom_path:
            print(f"警告: 设置中的自定义路径不存在: {custom_path}")
        
        # 2. 使用工作区的docs目录
        workspace_docs_path = os.path.join(self.workspace_path, 'docs')
        if os.path.exists(workspace_docs_path):
            # 检查是否有数据文件（如Excel文件或JSON文件）
            try:
                excel_file = os.path.join(workspace_docs_path, 'imsviewer.xlsx')
                json_files = [f for f in os.listdir(workspace_docs_path) if f.endswith('.json')]
                if os.path.exists(excel_file) or json_files:
                    print(f"使用工作区数据目录: {workspace_docs_path}")
                    return workspace_docs_path
            except Exception as e:
                print(f"检查工作区目录时出错: {e}")
        
        # 3. 最后尝试扩展目录
        extension_data_dir = self._get_data_directory_from_extension()
        if extension_data_dir:
            return extension_data_dir
        
        # 4. 特殊模式处理
        if output_mode == 'temp':
            # 使用系统临时目录
            temp_dir = os.path.join(tempfile.gettempdir(), 'ims-viewer-data')
            os.makedirs(temp_dir, exist_ok=True)
            print(f"使用临时目录: {temp_dir}")
            return temp_dir
        
        # 5. 最终回退：创建工作区docs目录
        os.makedirs(workspace_docs_path, exist_ok=True)
        print(f"创建并使用工作区数据目录: {workspace_docs_path}")
        return workspace_docs_path
    
    def get_excel_file_path(self) -> str:
        """获取Excel文件路径"""
        data_dir = self.get_data_directory()
        return os.path.join(data_dir, 'imsviewer.xlsx')
    
    def get_mongo_config(self) -> Dict[str, Any]:
        """获取MongoDB配置"""
        return {
            'database_name': self.get_database_name(),
            'uri': self.get_setting('imsViewer.mongoUri', 'mongodb://localhost:27017/'),
            'username': self.get_setting('imsViewer.mongoUsername', ''),
            'password': self.get_setting('imsViewer.mongoPassword', ''),
            'auth_database': self.get_setting('imsViewer.mongoAuthDatabase', 'admin')
        }
    
    def print_config_summary(self):
        """打印配置摘要"""
        print("=== IDE IMS Viewer 配置摘要 ===")
        print(f"工作区路径: {self.workspace_path}")
        
        ide_name, extension_path = self._detect_ide_and_extension_path()
        print(f"检测到的IDE: {ide_name}")
        if extension_path:
            print(f"扩展路径: {extension_path}")
        
        print(f"数据库名称: {self.get_database_name()}")
        print(f"输出模式: {self.get_output_mode()}")
        print(f"数据目录: {self.get_data_directory()}")
        print(f"Excel文件: {self.get_excel_file_path()}")
        
        mongo_config = self.get_mongo_config()
        print(f"MongoDB URI: {mongo_config['uri']}")
        if mongo_config['username']:
            print(f"MongoDB用户: {mongo_config['username']}")


# 全局配置读取器实例
_config_reader = None


def get_vscode_config() -> IDEConfigReader:
    """获取全局IDE配置读取器实例"""
    global _config_reader
    if _config_reader is None:
        _config_reader = IDEConfigReader()
    return _config_reader


def get_data_directory() -> str:
    """获取数据目录路径"""
    return get_vscode_config().get_data_directory()


def get_database_name() -> str:
    """获取数据库名称"""
    return get_vscode_config().get_database_name()


def get_mongo_config() -> Dict[str, Any]:
    """获取MongoDB配置"""
    return get_vscode_config().get_mongo_config()


if __name__ == '__main__':
    # 测试代码
    print("=== IDE配置读取测试 ===")
    
    config_reader = IDEConfigReader()
    config_reader.print_config_summary()
    
    print("\n=== 测试完成 ===")