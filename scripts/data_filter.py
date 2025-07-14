#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据过滤工具类
提供统一的数据过滤功能，用于过滤空记录和无效数据
"""

from typing import Dict, List, Any, Optional, Callable
import pandas as pd

class DataFilter:
    """
    数据过滤器类，提供多种数据过滤功能
    """
    
    @staticmethod
    def is_empty_value(value: Any) -> bool:
        """
        判断值是否为空
        
        Args:
            value: 要检查的值
            
        Returns:
            bool: 如果值为空则返回True
        """
        if value is None:
            return True
        if pd.isna(value):
            return True
        if isinstance(value, str) and value.strip() == '':
            return True
        return False
    
    @staticmethod
    def is_valid_string(value: Any, min_length: int = 1) -> bool:
        """
        判断值是否为有效字符串
        
        Args:
            value: 要检查的值
            min_length: 最小长度要求
            
        Returns:
            bool: 如果是有效字符串则返回True
        """
        if DataFilter.is_empty_value(value):
            return False
        if not isinstance(value, str):
            return False
        return len(value.strip()) >= min_length
    
    @staticmethod
    def has_valid_data(record: Dict[str, Any], exclude_fields: Optional[List[str]] = None) -> bool:
        """
        检查记录是否包含有效数据
        
        Args:
            record: 要检查的记录字典
            exclude_fields: 要排除检查的字段列表
            
        Returns:
            bool: 如果记录包含至少一个有效字段则返回True
        """
        exclude_fields = exclude_fields or []
        
        for key, value in record.items():
            if key in exclude_fields:
                continue
            if not DataFilter.is_empty_value(value):
                return True
        return False
    
    @staticmethod
    def filter_empty_records(data_list: List[Dict[str, Any]], 
                           required_fields: Optional[List[str]] = None,
                           exclude_fields: Optional[List[str]] = None) -> tuple[List[Dict[str, Any]], int]:
        """
        过滤空记录
        
        Args:
            data_list: 数据记录列表
            required_fields: 必须有效的字段列表
            exclude_fields: 检查时要排除的字段列表
            
        Returns:
            tuple: (过滤后的数据列表, 过滤掉的记录数)
        """
        filtered_data = []
        filtered_count = 0
        
        for record in data_list:
            is_valid = True
            
            # 检查必填字段
            if required_fields:
                for field in required_fields:
                    if field in record and DataFilter.is_empty_value(record[field]):
                        is_valid = False
                        break
            
            # 检查是否有有效数据
            if is_valid and not DataFilter.has_valid_data(record, exclude_fields):
                is_valid = False
            
            if is_valid:
                filtered_data.append(record)
            else:
                filtered_count += 1
        
        return filtered_data, filtered_count
    
    @staticmethod
    def filter_by_key_field(data_list: List[Dict[str, Any]], 
                          key_field: str,
                          validator: Optional[Callable[[Any], bool]] = None) -> tuple[List[Dict[str, Any]], int]:
        """
        根据关键字段过滤记录
        
        Args:
            data_list: 数据记录列表
            key_field: 关键字段名
            validator: 自定义验证函数，如果不提供则使用默认的字符串验证
            
        Returns:
            tuple: (过滤后的数据列表, 过滤掉的记录数)
        """
        if validator is None:
            validator = DataFilter.is_valid_string
        
        filtered_data = []
        filtered_count = 0
        
        for record in data_list:
            key_value = record.get(key_field)
            if validator(key_value):
                filtered_data.append(record)
            else:
                filtered_count += 1
        
        return filtered_data, filtered_count
    
    @staticmethod
    def clean_and_filter_supplier_data(data_list: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
        """
        专门用于供应商数据的清理和过滤
        
        Args:
            data_list: 供应商数据列表
            
        Returns:
            tuple: (过滤后的数据列表, 过滤掉的记录数)
        """
        def is_valid_supplier_name(value: Any) -> bool:
            return (
                value is not None and 
                isinstance(value, str) and 
                value.strip() != ''
            )
        
        return DataFilter.filter_by_key_field(data_list, 'supplier_name', is_valid_supplier_name)
    
    @staticmethod
    def clean_and_filter_customer_data(data_list: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
        """
        专门用于客户数据的清理和过滤
        
        Args:
            data_list: 客户数据列表
            
        Returns:
            tuple: (过滤后的数据列表, 过滤掉的记录数)
        """
        def is_valid_customer_name(value: Any) -> bool:
            return (
                value is not None and 
                isinstance(value, str) and 
                value.strip() != ''
            )
        
        return DataFilter.filter_by_key_field(data_list, 'customer_name', is_valid_customer_name)
    
    @staticmethod
    def assign_sequential_codes(data_list: List[Dict[str, Any]], 
                              code_field: str = 'code',
                              start_num: int = 1,
                              code_format: str = "{:02d}") -> List[Dict[str, Any]]:
        """
        为数据列表分配顺序编码
        
        Args:
            data_list: 数据列表
            code_field: 编码字段名
            start_num: 起始编号
            code_format: 编码格式字符串
            
        Returns:
            List[Dict[str, Any]]: 添加了编码的数据列表
        """
        for i, record in enumerate(data_list, start_num):
            record[code_field] = code_format.format(i)
        return data_list
    
    @staticmethod
    def print_filter_summary(original_count: int, filtered_count: int, data_type: str = "记录"):
        """
        打印过滤结果摘要
        
        Args:
            original_count: 原始记录数
            filtered_count: 过滤掉的记录数
            data_type: 数据类型描述
        """
        valid_count = original_count - filtered_count
        if filtered_count > 0:
            print(f"已过滤掉 {filtered_count} 条空{data_type}")
        print(f"成功处理 {valid_count} 条有效{data_type}")