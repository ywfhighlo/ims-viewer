#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证模块
用于验证数据是否符合预定义的模式
"""

import sys
import os
from typing import Dict, Any, List

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from field_mapping_utils import FieldMappingUtils

class DataValidator:
    def __init__(self):
        self.field_mapper = FieldMappingUtils()

    def validate(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证数据是否符合表模式

        Args:
            table_name: 表名 (例如 'customers', 'suppliers')
            data: 要验证的数据字典

        Returns:
            一个包含验证结果的字典，格式为:
            {'is_valid': bool, 'errors': List[str]}
        """
        schema = self.field_mapper.get_table_schema(table_name)
        if not schema:
            return {'is_valid': False, 'errors': [f"未找到表 '{table_name}' 的模式定义"]}

        errors = []
        required_fields = schema.get('required_fields', [])
        
        # 检查必需字段
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"缺少必需字段: {field}")

        # 检查字段类型
        for field_name, value in data.items():
            if value is None: continue
            
            chinese_field_name = self.field_mapper.get_chinese_field(field_name)
            if not chinese_field_name: continue

            field_info = self.field_mapper.get_field_info(chinese_field_name)
            if not field_info: continue

            expected_type = field_info.get('data_type')
            if expected_type == 'number' and not isinstance(value, (int, float)):
                errors.append(f"字段 '{field_name}' 的值 '{value}' 不是有效的数字类型")
            elif expected_type == 'string' and not isinstance(value, str):
                errors.append(f"字段 '{field_name}' 的值 '{value}' 不是有效的字符串类型")
            elif expected_type == 'date' and not isinstance(value, str): # 假设日期以字符串形式传入
                # 这里可以添加更复杂的日期格式验证
                pass

        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }

if __name__ == '__main__':
    # 这是一个示例，展示如何使用DataValidator
    validator = DataValidator()
    
    # 示例: 验证一个客户数据
    customer_data = {
        'customer_name': '测试客户',
        'contact_person': '张三',
        'phone': '13800138000',
        'credit_limit': 'not a number' # 无效数据
    }
    validation_result = validator.validate('customers', customer_data)
    print(f"客户数据验证结果: {validation_result}")

    # 示例: 验证一个缺少必需字段的供应商数据
    supplier_data = {
        'contact_person': '李四'
    }
    validation_result = validator.validate('suppliers', supplier_data)
    print(f"供应商数据验证结果: {validation_result}")
