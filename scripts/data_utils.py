#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理工具模块
提供通用的数据验证、格式化和转换功能
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def is_valid_date(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
        """验证日期格式是否正确"""
        try:
            datetime.strptime(date_str, format_str)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_number(value: Any) -> bool:
        """验证是否为有效数字"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """验证手机号格式（中国大陆）"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone.replace('-', '').replace(' ', '')))
    
    @staticmethod
    def validate_date_format(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
        """验证日期格式是否正确（别名方法）"""
        return DataValidator.is_valid_date(date_str, format_str)
    
    @staticmethod
    def validate_number(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> bool:
        """验证数字是否在指定范围内"""
        try:
            num = float(value)
            if min_value is not None and num < min_value:
                return False
            if max_value is not None and num > max_value:
                return False
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式（别名方法）"""
        return DataValidator.is_valid_email(email)
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式（别名方法）"""
        return DataValidator.is_valid_phone(phone)


class DataFormatter:
    """数据格式化器"""
    
    @staticmethod
    def format_currency(amount: Union[int, float, str], currency: str = '¥') -> str:
        """格式化货币金额"""
        try:
            num = float(amount)
            return f"{currency}{num:,.2f}"
        except (ValueError, TypeError):
            return f"{currency}0.00"
    
    @staticmethod
    def format_percentage(value: Union[int, float, str], decimal_places: int = 2) -> str:
        """格式化百分比"""
        try:
            num = float(value) * 100  # 转换为百分比
            return f"{num:.{decimal_places}f}%"
        except (ValueError, TypeError):
            return "0.00%"
    
    @staticmethod
    def format_date(date_obj: Union[datetime, str], format_str: str = '%Y-%m-%d') -> str:
        """格式化日期"""
        if isinstance(date_obj, datetime):
            return date_obj.strftime(format_str)
        elif isinstance(date_obj, str):
            try:
                # 尝试解析常见的日期格式
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(date_obj, fmt)
                        return dt.strftime(format_str)
                    except ValueError:
                        continue
                return date_obj  # 如果无法解析，返回原字符串
            except:
                return date_obj
        return ''
    
    @staticmethod
    def format_number(value: Union[int, float, str], decimal_places: int = 2) -> str:
        """格式化数字"""
        try:
            num = float(value)
            # 如果是整数且decimal_places为0，则不显示小数位
            if decimal_places == 0 or (num == int(num) and decimal_places == 2):
                return f"{int(num):,}"
            else:
                return f"{num:,.{decimal_places}f}"
        except (ValueError, TypeError):
            return "0.00"


class DataConverter:
    """数据转换器"""
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """安全转换为浮点数"""
        try:
            if value is None or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """安全转换为整数"""
        try:
            if value is None or value == '':
                return default
            return int(float(value))  # 先转float再转int，处理"1.0"这种情况
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_decimal(value: Any, default: Decimal = Decimal('0.00')) -> Decimal:
        """安全转换为Decimal（用于精确计算）"""
        try:
            if value is None or value == '':
                return default
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return default
    
    @staticmethod
    def normalize_string(value: Any) -> str:
        """标准化字符串（去除首尾空格，转换None为空字符串）"""
        if value is None:
            return ''
        return str(value).strip()


class ReportDataProcessor:
    """报表数据处理器"""
    
    @staticmethod
    def calculate_aging_category(date_str: str, reference_date: Optional[datetime] = None) -> str:
        """计算账龄分类"""
        if not date_str:
            return "未知"
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            ref_date = reference_date or datetime.now()
            days_diff = (ref_date - target_date).days
            
            if days_diff <= 30:
                return "30天内"
            elif days_diff <= 60:
                return "31-60天"
            elif days_diff <= 90:
                return "61-90天"
            else:
                return "90天以上"
        except (ValueError, TypeError):
            return "未知"
    
    @staticmethod
    def calculate_risk_level(balance: float, thresholds: Optional[Dict[str, float]] = None) -> str:
        """计算风险等级"""
        if thresholds is None:
            thresholds = {
                'low': 10000,
                'medium': 50000
            }
        
        if balance <= 0:
            return "无风险"
        elif balance <= thresholds['low']:
            return "低风险"
        elif balance <= thresholds['medium']:
            return "中风险"
        else:
            return "高风险"
    
    @staticmethod
    def calculate_trend_category(count: int, thresholds: Optional[Dict[str, int]] = None) -> str:
        """计算趋势分类（基于交易次数）"""
        if thresholds is None:
            thresholds = {
                'high': 10,
                'normal': 5
            }
        
        if count >= thresholds['high']:
            return "高频"
        elif count >= thresholds['normal']:
            return "正常"
        else:
            return "低频"
    
    @staticmethod
    def calculate_price_stability(min_price: float, max_price: float) -> str:
        """计算价格稳定性"""
        if min_price <= 0 or max_price <= 0:
            return "未知"
        
        variance = ((max_price - min_price) / min_price) * 100
        
        if variance <= 5:
            return "稳定"
        elif variance <= 15:
            return "一般"
        else:
            return "波动大"
    
    @staticmethod
    def calculate_inventory_stats(inventory_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算库存统计信息"""
        if not inventory_records:
            return {
                'total_value': 0,
                'avg_price': 0,
                'product_count': 0,
                'total_quantity': 0
            }
        
        total_value = 0
        total_quantity = 0
        prices = []
        
        for record in inventory_records:
            try:
                # 解析格式化的货币值
                unit_price_str = record.get('unit_price', '¥0.00')
                unit_price = float(unit_price_str.replace('¥', '').replace(',', ''))
                
                quantity_str = record.get('quantity', '0')
                quantity = float(str(quantity_str).replace(',', ''))
                
                total_value += unit_price * quantity
                total_quantity += quantity
                
                if unit_price > 0:
                    prices.append(unit_price)
                    
            except (ValueError, TypeError):
                continue
        
        return {
            'total_value': total_value,
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'product_count': len(inventory_records),
            'total_quantity': total_quantity,
            'price_range': {
                'min': min(prices) if prices else 0,
                'max': max(prices) if prices else 0
            }
        }


class TableFormatter:
    """表格格式化器"""
    
    @staticmethod
    def format_table_data(data: List[Dict[str, Any]], 
                         headers: List[str], 
                         field_mapping: Dict[str, str],
                         formatters: Optional[Dict[str, callable]] = None) -> str:
        """格式化表格数据为字符串"""
        if not data:
            return "暂无数据"
        
        formatters = formatters or {}
        
        # 计算列宽
        col_widths = [len(h) for h in headers]
        
        for item in data:
            for i, header in enumerate(headers):
                field_name = field_mapping.get(header, header)
                value = item.get(field_name, '')
                
                # 应用格式化器
                if header in formatters:
                    value = formatters[header](value)
                else:
                    value = str(value)
                
                col_widths[i] = max(col_widths[i], len(value))
        
        # 构建表格
        result = []
        
        # 表头
        header_row = '|'.join(h.ljust(w) for h, w in zip(headers, col_widths))
        result.append(header_row)
        result.append('-' * len(header_row))
        
        # 数据行
        for item in data:
            row_data = []
            for i, header in enumerate(headers):
                field_name = field_mapping.get(header, header)
                value = item.get(field_name, '')
                
                # 应用格式化器
                if header in formatters:
                    value = formatters[header](value)
                else:
                    value = str(value)
                
                row_data.append(value.ljust(col_widths[i]))
            
            result.append('|'.join(row_data))
        
        return '\n'.join(result)
    
    @staticmethod
    def format_table(data: List[Dict[str, Any]], 
                    headers: List[str], 
                    field_mapping: Optional[Dict[str, str]] = None,
                    formatters: Optional[Dict[str, callable]] = None,
                    title: Optional[str] = None) -> str:
        """格式化表格数据为字符串（别名方法）"""
        # 如果没有提供field_mapping，使用headers作为默认映射
        if field_mapping is None:
            field_mapping = {header: header for header in headers}
        
        result = TableFormatter.format_table_data(data, headers, field_mapping, formatters)
        
        # 如果提供了标题，添加到结果前面
        if title:
            result = f"{title}\n{'=' * len(title)}\n{result}"
        
        return result


# 常用格式化器实例
CURRENCY_FORMATTER = lambda x: DataFormatter.format_currency(x)
PERCENTAGE_FORMATTER = lambda x: DataFormatter.format_percentage(x)
DATE_FORMATTER = lambda x: DataFormatter.format_date(x)
NUMBER_FORMATTER = lambda x: DataFormatter.format_number(x)


if __name__ == '__main__':
    # 测试代码
    print("=== 数据工具模块测试 ===")
    
    # 测试数据验证
    print("\n数据验证测试:")
    print(f"日期验证: {DataValidator.is_valid_date('2023-12-01')}")
    print(f"数字验证: {DataValidator.is_valid_number('123.45')}")
    print(f"邮箱验证: {DataValidator.is_valid_email('test@example.com')}")
    
    # 测试数据格式化
    print("\n数据格式化测试:")
    print(f"货币格式化: {DataFormatter.format_currency(1234.56)}")
    print(f"百分比格式化: {DataFormatter.format_percentage(85.67)}")
    print(f"数字格式化: {DataFormatter.format_number(1234567.89)}")
    
    # 测试数据转换
    print("\n数据转换测试:")
    print(f"安全浮点转换: {DataConverter.safe_float('123.45')}")
    print(f"安全整数转换: {DataConverter.safe_int('123.45')}")
    print(f"字符串标准化: '{DataConverter.normalize_string('  test  ')}'")