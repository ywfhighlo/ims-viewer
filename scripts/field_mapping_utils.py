#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段映射工具类
基于统一的中英文字段映射词典，提供字段翻译和验证功能
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

class FieldMappingUtils:
    """字段映射工具类 - 单一数据源的字段翻译"""
    
    def __init__(self, dictionary_path: Optional[str] = None):
        """
        初始化字段映射工具
        
        Args:
            dictionary_path: 词典文件路径，默认使用项目根目录下的词典
        """
        if dictionary_path is None:
            # 默认词典路径
            project_root = Path(__file__).parent.parent
            dictionary_path = project_root / "field_mapping_dictionary.json"
        
        self.dictionary_path = dictionary_path
        self._dictionary = None
        self._load_dictionary()
    
    def _load_dictionary(self):
        """加载字段映射词典"""
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as f:
                self._dictionary = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"字段映射词典文件不存在: {self.dictionary_path}")
        except json.JSONDecodeError:
            raise ValueError(f"字段映射词典文件格式错误: {self.dictionary_path}")
    
    def get_english_field(self, chinese_field: str) -> Optional[str]:
        """
        获取中文字段对应的英文字段名
        
        Args:
            chinese_field: 中文字段名
            
        Returns:
            英文字段名，如果不存在则返回None
        """
        field_dict = self._dictionary.get("field_dictionary", {})
        field_info = field_dict.get(chinese_field)
        return field_info.get("english") if field_info else None
    
    def get_chinese_field(self, english_field: str) -> Optional[str]:
        """
        获取英文字段对应的中文字段名
        
        Args:
            english_field: 英文字段名
            
        Returns:
            中文字段名，如果不存在则返回None
        """
        field_dict = self._dictionary.get("field_dictionary", {})
        for chinese, info in field_dict.items():
            if info.get("english") == english_field:
                return chinese
        return None
    
    def get_field_info(self, chinese_field: str) -> Optional[Dict[str, Any]]:
        """
        获取字段的完整信息
        
        Args:
            chinese_field: 中文字段名
            
        Returns:
            字段信息字典，包含英文名、数据类型、描述、分类等
        """
        field_dict = self._dictionary.get("field_dictionary", {})
        return field_dict.get(chinese_field)
    
    def translate_dict(self, chinese_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        将包含中文字段名的字典翻译为英文字段名字典
        
        Args:
            chinese_dict: 包含中文字段名的字典
            
        Returns:
            翻译后的英文字段名字典
        """
        english_dict = {}
        for chinese_key, value in chinese_dict.items():
            english_key = self.get_english_field(chinese_key)
            if english_key:
                english_dict[english_key] = value
            else:
                # 如果找不到映射，保留原字段名并记录警告
                english_dict[chinese_key] = value
                print(f"警告: 未找到字段 '{chinese_key}' 的英文映射")
        
        return english_dict
    
    def translate_list_of_dicts(self, chinese_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        翻译字典列表中的字段名
        
        Args:
            chinese_list: 包含中文字段名的字典列表
            
        Returns:
            翻译后的英文字段名字典列表
        """
        return [self.translate_dict(item) for item in chinese_list]
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取表的结构定义
        
        Args:
            table_name: 表名（英文）
            
        Returns:
            表结构信息，包含中文名、字段列表等
        """
        table_schemas = self._dictionary.get("table_schemas", {})
        return table_schemas.get(table_name)
    
    def get_table_fields(self, table_name: str, language: str = "english") -> List[str]:
        """
        获取表的字段列表
        
        Args:
            table_name: 表名（英文）
            language: 返回语言，"chinese" 或 "english"
            
        Returns:
            字段名列表
        """
        table_schema = self.get_table_schema(table_name)
        if not table_schema:
            return []
        
        chinese_fields = table_schema.get("fields", [])
        
        if language == "chinese":
            return chinese_fields
        elif language == "english":
            english_fields = []
            for chinese_field in chinese_fields:
                english_field = self.get_english_field(chinese_field)
                if english_field:
                    english_fields.append(english_field)
            return english_fields
        else:
            raise ValueError("language 参数必须是 'chinese' 或 'english'")
    
    def validate_fields(self, fields: List[str], table_name: str = None) -> Dict[str, List[str]]:
        """
        验证字段名是否在词典中存在
        
        Args:
            fields: 要验证的字段名列表（中文）
            table_name: 表名，用于更精确的验证
            
        Returns:
            验证结果字典，包含 valid_fields 和 invalid_fields
        """
        field_dict = self._dictionary.get("field_dictionary", {})
        valid_fields = []
        invalid_fields = []
        
        for field in fields:
            if field in field_dict:
                valid_fields.append(field)
            else:
                invalid_fields.append(field)
        
        return {
            "valid_fields": valid_fields,
            "invalid_fields": invalid_fields
        }
    
    def get_fields_by_category(self, category: str) -> List[str]:
        """
        根据分类获取字段列表
        
        Args:
            category: 字段分类
            
        Returns:
            该分类下的中文字段名列表
        """
        field_dict = self._dictionary.get("field_dictionary", {})
        fields = []
        
        for chinese_field, info in field_dict.items():
            if info.get("category") == category:
                fields.append(chinese_field)
        
        return fields
    
    def get_all_categories(self) -> Dict[str, str]:
        """
        获取所有字段分类
        
        Returns:
            分类字典，key为分类名，value为分类描述
        """
        return self._dictionary.get("categories", {})
    
    def create_mapping_for_excel(self, excel_headers: List[str], table_name: str) -> Dict[str, str]:
        """
        为Excel表头创建字段映射
        
        Args:
            excel_headers: Excel文件的表头列表（中文）
            table_name: 目标数据库表名
            
        Returns:
            映射字典，key为Excel表头，value为英文字段名
        """
        mapping = {}
        table_fields = self.get_table_fields(table_name, "chinese")
        
        for header in excel_headers:
            if header in table_fields:
                english_field = self.get_english_field(header)
                if english_field:
                    mapping[header] = english_field
            else:
                # 尝试模糊匹配
                fuzzy_match = self._fuzzy_match_field(header, table_fields)
                if fuzzy_match:
                    english_field = self.get_english_field(fuzzy_match)
                    if english_field:
                        mapping[header] = english_field
                        print(f"模糊匹配: '{header}' -> '{fuzzy_match}' -> '{english_field}'")
        
        return mapping
    
    def _fuzzy_match_field(self, header: str, table_fields: List[str]) -> Optional[str]:
        """
        模糊匹配字段名
        
        Args:
            header: 要匹配的表头
            table_fields: 表字段列表
            
        Returns:
            匹配到的字段名，如果没有匹配则返回None
        """
        # 简单的包含匹配
        for field in table_fields:
            if header in field or field in header:
                return field
        return None
    
    def export_table_mapping(self, table_name: str, format: str = "json") -> str:
        """
        导出表的字段映射
        
        Args:
            table_name: 表名
            format: 导出格式，"json" 或 "csv"
            
        Returns:
            导出的内容字符串
        """
        table_schema = self.get_table_schema(table_name)
        if not table_schema:
            raise ValueError(f"表 '{table_name}' 不存在")
        
        chinese_fields = table_schema.get("fields", [])
        mapping_data = []
        
        for chinese_field in chinese_fields:
            field_info = self.get_field_info(chinese_field)
            if field_info:
                mapping_data.append({
                    "chinese_name": chinese_field,
                    "english_name": field_info.get("english"),
                    "data_type": field_info.get("data_type"),
                    "description": field_info.get("description"),
                    "category": field_info.get("category")
                })
        
        if format == "json":
            return json.dumps(mapping_data, ensure_ascii=False, indent=2)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["chinese_name", "english_name", "data_type", "description", "category"])
            writer.writeheader()
            writer.writerows(mapping_data)
            return output.getvalue()
        else:
            raise ValueError("format 参数必须是 'json' 或 'csv'")

# 全局实例，方便其他模块使用
field_mapper = FieldMappingUtils()

# 便捷函数
def translate_to_english(chinese_field: str) -> Optional[str]:
    """便捷函数：将中文字段名翻译为英文"""
    return field_mapper.get_english_field(chinese_field)

def translate_to_chinese(english_field: str) -> Optional[str]:
    """便捷函数：将英文字段名翻译为中文"""
    return field_mapper.get_chinese_field(english_field)

def translate_dict_to_english(chinese_dict: Dict[str, Any]) -> Dict[str, Any]:
    """便捷函数：翻译字典中的字段名"""
    return field_mapper.translate_dict(chinese_dict)

def get_table_english_fields(table_name: str) -> List[str]:
    """便捷函数：获取表的英文字段列表"""
    return field_mapper.get_table_fields(table_name, "english")

def get_table_chinese_fields(table_name: str) -> List[str]:
    """便捷函数：获取表的中文字段列表"""
    return field_mapper.get_table_fields(table_name, "chinese")

if __name__ == "__main__":
    # 测试代码
    mapper = FieldMappingUtils()
    
    # 测试字段翻译
    print("=== 字段翻译测试 ===")
    chinese_field = "供应商名称"
    english_field = mapper.get_english_field(chinese_field)
    print(f"中文: {chinese_field} -> 英文: {english_field}")
    
    # 测试字典翻译
    print("\n=== 字典翻译测试 ===")
    chinese_data = {
        "供应商名称": "测试供应商",
        "联系电话": "13800138000",
        "单位地址": "测试地址"
    }
    english_data = mapper.translate_dict(chinese_data)
    print(f"中文数据: {chinese_data}")
    print(f"英文数据: {english_data}")
    
    # 测试表结构
    print("\n=== 表结构测试 ===")
    table_name = "suppliers"
    chinese_fields = mapper.get_table_fields(table_name, "chinese")
    english_fields = mapper.get_table_fields(table_name, "english")
    print(f"表 {table_name} 中文字段: {chinese_fields}")
    print(f"表 {table_name} 英文字段: {english_fields}")
    
    # 测试字段验证
    print("\n=== 字段验证测试 ===")
    test_fields = ["供应商名称", "联系电话", "不存在的字段"]
    validation_result = mapper.validate_fields(test_fields)
    print(f"验证结果: {validation_result}") 