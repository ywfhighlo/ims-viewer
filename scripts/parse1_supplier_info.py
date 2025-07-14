#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
供应商信息表解析脚本
使用统一的字段映射词典进行数据转换
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any
from field_mapping_utils import field_mapper, translate_dict_to_english
from vscode_config_reader import get_data_directory

def parse_supplier_info(excel_file_path: str, sheet_name: str = "供应商信息表") -> List[Dict[str, Any]]:
    """
    解析供应商信息表
    
    Args:
        excel_file_path: Excel文件路径
        sheet_name: 工作表名称
        
    Returns:
        解析后的供应商信息列表（英文字段名）
    """
    try:
        # 读取Excel文件，跳过第0行（表名），使用第1行作为列名
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=1)
        
        # 获取表的预期字段
        expected_fields = field_mapper.get_table_fields("suppliers", "chinese")
        print(f"预期字段: {expected_fields}")
        
        # 验证Excel表头
        excel_headers = df.columns.tolist()
        print(f"Excel表头: {excel_headers}")
        
        # 过滤掉空列名和Unnamed列
        excel_headers = [col for col in excel_headers if col and not str(col).startswith('Unnamed')]
        print(f"过滤后的表头: {excel_headers}")
        
        # 只保留有效列的数据
        df = df[excel_headers]
        
        # 验证字段是否存在于词典中
        validation_result = field_mapper.validate_fields(excel_headers)
        print(f"字段验证结果: {validation_result}")
        
        if validation_result["invalid_fields"]:
            print(f"警告: 以下字段不在词典中: {validation_result['invalid_fields']}")
        
        # 创建字段映射
        field_mapping = field_mapper.create_mapping_for_excel(excel_headers, "suppliers")
        print(f"字段映射: {field_mapping}")
        
        # 转换数据
        suppliers_data = []
        for index, row in df.iterrows():
            # 创建中文字段的数据字典
            chinese_data = {}
            for header in excel_headers:
                value = row[header]
                # 处理NaN值
                if pd.isna(value):
                    value = None
                chinese_data[header] = value
            
            # 使用统一词典翻译为英文字段
            english_data = translate_dict_to_english(chinese_data)
            
            suppliers_data.append(english_data)
        
        print(f"成功解析 {len(suppliers_data)} 条供应商信息")
        return suppliers_data
        
    except Exception as e:
        print(f"解析供应商信息时出错: {str(e)}")
        raise

def validate_supplier_data(suppliers_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    验证供应商数据的完整性
    
    Args:
        suppliers_data: 供应商数据列表
        
    Returns:
        验证结果
    """
    validation_result = {
        "total_records": len(suppliers_data),
        "valid_records": 0,
        "invalid_records": 0,
        "errors": []
    }
    
    # 获取必填字段（从词典中获取）
    required_fields = ["supplier_name"]  # 供应商名称是必填的
    
    for i, supplier in enumerate(suppliers_data):
        is_valid = True
        record_errors = []
        
        # 检查必填字段
        for field in required_fields:
            if not supplier.get(field):
                is_valid = False
                record_errors.append(f"缺少必填字段: {field}")
        
        # 检查数据类型（基于词典定义）
        for chinese_field, value in supplier.items():
            if chinese_field.startswith('_'):  # 跳过元数据字段
                continue
                
            # 从词典获取字段信息
            chinese_name = field_mapper.get_chinese_field(chinese_field)
            if chinese_name:
                field_info = field_mapper.get_field_info(chinese_name)
                if field_info and value is not None:
                    expected_type = field_info.get("data_type", "string")
                    if expected_type == "number" and not isinstance(value, (int, float)):
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            is_valid = False
                            record_errors.append(f"字段 {chinese_field} 应为数字类型")
        
        if is_valid:
            validation_result["valid_records"] += 1
        else:
            validation_result["invalid_records"] += 1
            validation_result["errors"].append({
                "row": i + 1,
                "errors": record_errors
            })
    
    return validation_result

def save_suppliers_data(suppliers_data: List[Dict[str, Any]], output_file: str = None):
    """
    保存解析后的供应商数据
    
    Args:
        suppliers_data: 供应商数据列表
        output_file: 输出文件路径
    """
    try:
        if output_file is None:
            data_dir = get_data_directory()
            output_file = os.path.join(data_dir, "suppliers.json")
        # 添加字段映射信息到输出
        output_data = {
            "metadata": {
                "table_name": "suppliers",
                "table_chinese_name": "供应商信息表",
                "total_records": len(suppliers_data),
                "field_mapping": field_mapper.get_table_schema("suppliers"),
                "generated_by": "parse_supplier_info.py",
                "dictionary_version": field_mapper._dictionary.get("metadata", {}).get("version", "unknown")
            },
            "data": suppliers_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    # 配置文件路径（相对于项目根目录）
    data_dir = get_data_directory()
    excel_file = os.path.join(data_dir, "imsviewer.xlsx")  # 根据实际文件路径调整
    
    if not os.path.exists(excel_file):
        print(f"Excel文件不存在: {excel_file}")
        return
    
    try:
        print("=== 开始解析供应商信息表 ===")
        
        # 解析数据
        suppliers_data = parse_supplier_info(excel_file)
        
        # 验证数据
        print("\n=== 数据验证 ===")
        validation_result = validate_supplier_data(suppliers_data)
        print(f"验证结果: {validation_result}")
        
        # 保存数据到docs目录
        print("\n=== 保存数据到docs目录 ===")
        save_suppliers_data(suppliers_data)
        
        # 显示字段映射信息
        print("\n=== 字段映射信息 ===")
        table_schema = field_mapper.get_table_schema("suppliers")
        print(f"表结构: {json.dumps(table_schema, ensure_ascii=False, indent=2)}")
        
        print("\n=== 解析完成 ===")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()