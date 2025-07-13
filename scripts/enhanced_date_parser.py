#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的日期解析器
支持多种日期格式和特殊值处理
"""

import re
from datetime import datetime
from typing import Optional, Union, List
import logging

class EnhancedDateParser:
    """增强的日期解析器"""
    
    def __init__(self):
        # 支持的日期格式列表（按优先级排序）
        self.date_patterns = [
            # ISO格式
            (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '%Y-%m-%d'),
            (r'^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})$', '%Y-%m-%d %H:%M:%S'),
            
            # 点分隔格式
            (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', '%Y.%m.%d'),
            (r'^(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})$', '%Y.%m.%d %H:%M:%S'),
            
            # 斜杠分隔格式
            (r'^(\d{4})/(\d{1,2})/(\d{1,2})$', '%Y/%m/%d'),
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', '%m/%d/%Y'),
            
            # 中文格式
            (r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', '%Y年%m月%d日'),
            
            # 紧凑格式
            (r'^(\d{8})$', '%Y%m%d'),  # 20231201
        ]
        
        # 特殊值映射
        self.special_values = {
            '未开票': None,
            '待开票': None,
            '未确定': None,
            '待定': None,
            '无': None,
            '空': None,
            '': None,
            'NULL': None,
            'null': None,
            'N/A': None,
            'n/a': None,
            '暂无': None,
            '未知': None,
        }
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def parse_date(self, date_value: Union[str, datetime, None], field_name: str = '') -> Optional[datetime]:
        """
        解析日期值
        
        Args:
            date_value: 要解析的日期值
            field_name: 字段名（用于错误日志）
            
        Returns:
            解析后的datetime对象，如果解析失败或为特殊值则返回None
        """
        # 如果已经是datetime对象，直接返回
        if isinstance(date_value, datetime):
            return date_value
        
        # 如果是None或空值，返回None
        if date_value is None:
            return None
        
        # 转换为字符串并去除首尾空格
        date_str = str(date_value).strip()
        
        # 检查特殊值
        if date_str in self.special_values:
            self.logger.info(f"字段 '{field_name}' 的特殊值 '{date_str}' 被处理为 None")
            return self.special_values[date_str]
        
        # 尝试各种日期格式
        for pattern, format_str in self.date_patterns:
            if re.match(pattern, date_str):
                try:
                    # 对于点分隔格式，需要特殊处理单数字月份和日期
                    if '.' in format_str and '.' in date_str:
                        parts = date_str.split('.')
                        if len(parts) == 3:
                            year, month, day = parts
                            # 补零
                            normalized_date = f"{year}.{month.zfill(2)}.{day.zfill(2)}"
                            return datetime.strptime(normalized_date, '%Y.%m.%d')
                    
                    return datetime.strptime(date_str, format_str)
                except ValueError as e:
                    self.logger.debug(f"格式 '{format_str}' 解析失败: {e}")
                    continue
        
        # 如果所有格式都失败，记录警告
        self.logger.warning(f"无法解析日期字段 '{field_name}' 的值 '{date_str}'")
        return None
    
    def parse_date_fields(self, records: List[dict], date_fields: List[str]) -> List[dict]:
        """
        批量处理记录中的日期字段
        
        Args:
            records: 记录列表
            date_fields: 日期字段名列表
            
        Returns:
            处理后的记录列表
        """
        processed_records = []
        parse_stats = {
            'total_fields': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'special_values': 0
        }
        
        for record in records:
            processed_record = record.copy()
            
            for field in date_fields:
                if field in record:
                    parse_stats['total_fields'] += 1
                    original_value = record[field]
                    parsed_value = self.parse_date(original_value, field)
                    
                    if parsed_value is not None:
                        processed_record[field] = parsed_value
                        parse_stats['successful_parses'] += 1
                    elif str(original_value).strip() in self.special_values:
                        processed_record[field] = None
                        parse_stats['special_values'] += 1
                    else:
                        # 保留原值，但记录失败
                        processed_record[field] = original_value
                        parse_stats['failed_parses'] += 1
            
            processed_records.append(processed_record)
        
        # 输出统计信息
        if parse_stats['total_fields'] > 0:
            self.logger.info(f"日期解析统计: 总计 {parse_stats['total_fields']} 个字段, "
                           f"成功 {parse_stats['successful_parses']} 个, "
                           f"特殊值 {parse_stats['special_values']} 个, "
                           f"失败 {parse_stats['failed_parses']} 个")
        
        return processed_records
    
    def add_custom_pattern(self, pattern: str, format_str: str):
        """
        添加自定义日期格式
        
        Args:
            pattern: 正则表达式模式
            format_str: strptime格式字符串
        """
        self.date_patterns.insert(0, (pattern, format_str))
        self.logger.info(f"添加自定义日期格式: {pattern} -> {format_str}")
    
    def add_special_value(self, value: str, replacement: Optional[datetime] = None):
        """
        添加特殊值映射
        
        Args:
            value: 特殊值字符串
            replacement: 替换值（默认为None）
        """
        self.special_values[value] = replacement
        self.logger.info(f"添加特殊值映射: '{value}' -> {replacement}")
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的日期格式列表
        
        Returns:
            格式字符串列表
        """
        return [format_str for _, format_str in self.date_patterns]
    
    def validate_date_format(self, date_str: str) -> dict:
        """
        验证日期格式并返回详细信息
        
        Args:
            date_str: 日期字符串
            
        Returns:
            验证结果字典
        """
        result = {
            'is_valid': False,
            'parsed_date': None,
            'matched_pattern': None,
            'format_used': None,
            'is_special_value': False
        }
        
        # 检查特殊值
        if date_str in self.special_values:
            result['is_special_value'] = True
            result['is_valid'] = True
            return result
        
        # 尝试解析
        for pattern, format_str in self.date_patterns:
            if re.match(pattern, date_str):
                try:
                    parsed_date = self.parse_date(date_str)
                    if parsed_date:
                        result['is_valid'] = True
                        result['parsed_date'] = parsed_date
                        result['matched_pattern'] = pattern
                        result['format_used'] = format_str
                        break
                except:
                    continue
        
        return result

# 全局实例
date_parser = EnhancedDateParser()

# 便捷函数
def parse_date(date_value: Union[str, datetime, None], field_name: str = '') -> Optional[datetime]:
    """便捷函数：解析单个日期值"""
    return date_parser.parse_date(date_value, field_name)

def parse_date_fields(records: List[dict], date_fields: List[str]) -> List[dict]:
    """便捷函数：批量处理日期字段"""
    return date_parser.parse_date_fields(records, date_fields)

if __name__ == "__main__":
    # 测试代码
    import logging
    logging.basicConfig(level=logging.INFO)
    
    parser = EnhancedDateParser()
    
    # 测试各种日期格式
    test_dates = [
        '2023.9.1',
        '2023.10.12',
        '2023-09-01',
        '2023/9/1',
        '2023年9月1日',
        '20230901',
        '未开票',
        '待定',
        '2023.9.1 14:30:00',
        '无效日期'
    ]
    
    print("=== 日期解析测试 ===")
    for date_str in test_dates:
        result = parser.validate_date_format(date_str)
        print(f"'{date_str}' -> {result}")
    
    # 测试批量处理
    print("\n=== 批量处理测试 ===")
    test_records = [
        {'invoice_date': '2023.9.1', 'amount': 100},
        {'invoice_date': '未开票', 'amount': 200},
        {'invoice_date': '2023-10-12', 'amount': 300}
    ]
    
    processed = parser.parse_date_fields(test_records, ['invoice_date'])
    for record in processed:
        print(record)