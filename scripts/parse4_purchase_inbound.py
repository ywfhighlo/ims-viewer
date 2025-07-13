#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析进货入库明细表 - 增强版
集成了增强的日期解析器、日志系统和改进的字段映射处理
"""

import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional
from field_mapping_utils import FieldMappingUtils
from enhanced_date_parser import EnhancedDateParser
from enhanced_logger import EnhancedLogger
# 新增导入
from material_manager import get_db_client

def parse_purchase_inbound(excel_file_path: str, 
                             sheet_name: str = "进货入库明细表",
                             logger: Optional[EnhancedLogger] = None) -> List[Dict[str, Any]]:
    """
    解析进货入库明细表 - 增强版
    
    Args:
        excel_file_path: Excel文件路径
        sheet_name: 工作表名称，默认为"进货入库明细表"
        logger: 日志记录器，如果为None则创建新的记录器
    
    Returns:
        解析后的数据列表
    """
    if logger is None:
        logger = EnhancedLogger("Parse_Purchase_Inbound")
    
    operation_index = logger.start_operation(f"解析{sheet_name}", 
                                           excel_file=excel_file_path,
                                           sheet=sheet_name,
                                           table="purchase_inbound")
    
    # 新增：数据库客户端初始化
    db_client = get_db_client()
    db = None
    if db_client:
        db_name = os.environ.get('IMS_DB_NAME', 'ims_database')
        db = db_client.get_database(db_name)
        logger.info("数据库连接成功", database=db_name)
    else:
        logger.error("无法连接到数据库，物料编码匹配功能将受限")
    
    try:
        logger.set_context(sheet=sheet_name, table="purchase_inbound")
        
        # 1. 验证文件存在
        if not os.path.exists(excel_file_path):
            logger.error(f"Excel文件不存在", file_path=excel_file_path)
            raise FileNotFoundError(f"Excel文件不存在: {excel_file_path}")
        
        logger.info(f"开始解析进货入库明细表", file_path=excel_file_path)
        
        # 2. 读取Excel文件
        try:
            # 跳过第0行（表名），使用第1行作为列名
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=1)
            logger.info(f"成功读取Excel工作表", 
                       sheet=sheet_name,
                       rows=len(df),
                       columns=len(df.columns),
                       is_success=True)
        except Exception as e:
            logger.error(f"读取Excel工作表失败", 
                        sheet=sheet_name,
                        error=str(e))
            raise
        
        # 3. 处理表头
        original_columns = df.columns.tolist()
        logger.info(f"原始表头", headers=original_columns, count=len(original_columns))
        
        # 获取列名并过滤掉空列名
        columns = [col for col in original_columns if col and not str(col).startswith('Unnamed')]
        
        if len(columns) != len(original_columns):
            removed_count = len(original_columns) - len(columns)
            logger.warning(f"移除无效表头", 
                          removed_count=removed_count,
                          valid_headers=columns)
        
        logger.info(f"有效表头", headers=columns, count=len(columns))
        
        # 只保留有效列的数据
        df = df[columns]
        
        # 4. 字段映射处理
        field_utils = FieldMappingUtils()
        
        # 检查缺失的字段映射
        missing_mappings = []
        for header in columns:
            if not field_utils.get_english_field(header):
                missing_mappings.append(header)
                logger.log_field_mapping_issue(header, "purchase_inbound", "missing_mapping")
        
        if missing_mappings:
            logger.warning(f"发现缺失的字段映射", 
                          missing_fields=missing_mappings,
                          count=len(missing_mappings),
                          suggestion="请在字段映射字典中添加这些字段的英文映射")
        
        # 5. 数据转换
        logger.info(f"开始数据转换", total_rows=len(df))
        
        data = []
        conversion_errors = 0
        
        for index, row in df.iterrows():
            try:
                # 移除空值
                row_dict = row.dropna().to_dict()
                
                if row_dict:  # 只添加非空记录
                    # 转换为英文字段名
                    english_dict = field_utils.translate_dict(row_dict)
                    
                    # --- 新增：物料编码匹配逻辑 ---
                    if db is not None and english_dict: # 修正：显式与None比较
                        material_code = english_dict.get("material_code")
                        material_name = english_dict.get("material_name")
                        specification = english_dict.get("specification")
                        
                        if material_code:
                            # 优先使用Excel中提供的material_code
                            if not db.materials.find_one({"material_code": material_code}):
                                logger.warning(f"Excel提供的物料编码在数据库中不存在",
                                               row_index=index, material_code=material_code)
                        elif material_name and specification:
                            # 其次，通过名称和规格查找
                            found_material = db.materials.find_one({
                                "material_name": material_name,
                                "material_model": specification # 假设规格型号对应material_model
                            })
                            if found_material:
                                english_dict["material_code"] = found_material["material_code"]
                            else:
                                logger.warning(f"物料未在数据库中定义，无法匹配编码",
                                               row_index=index,
                                               material_name=material_name,
                                               specification=specification)
                    # --- 物料编码匹配逻辑结束 ---

                    if english_dict:
                        data.append(english_dict)
                    else:
                        logger.debug(f"字段映射后为空记录", row_index=index)
                else:
                    logger.debug(f"跳过空记录", row_index=index)
                    
            except Exception as e:
                conversion_errors += 1
                logger.warning(f"数据转换失败", 
                              row_index=index,
                              error=str(e))
        
        logger.info(f"数据转换完成", 
                   total_rows=len(df),
                   converted_rows=len(data),
                   conversion_errors=conversion_errors,
                   success_rate=f"{(len(data)/len(df)*100):.1f}%" if len(df) > 0 else "0%",
                   is_success=True)
        
        # 6. 日期字段处理
        if data:
            date_parser = EnhancedDateParser()
            # 进货入库明细表的日期字段
            date_fields = ['inbound_date', 'purchase_date', 'invoice_date']
            
            logger.info(f"开始处理日期字段", date_fields=date_fields)
            
            date_processing_errors = 0
            date_processing_success = 0
            
            for record in data:
                for field in date_fields:
                    if field in record and record[field]:
                        try:
                            original_value = record[field]
                            parsed_date = date_parser.parse_date(str(original_value))
                            
                            if parsed_date is not None:
                                record[field] = parsed_date.isoformat()
                                date_processing_success += 1
                            else:
                                logger.log_date_parsing_issue(field, str(original_value), "purchase_inbound")
                                date_processing_errors += 1
                                
                        except Exception as e:
                            logger.warning(f"日期字段处理异常", 
                                          field=field,
                                          value=str(record[field]),
                                          error=str(e))
                            date_processing_errors += 1
            
            logger.info(f"日期字段处理完成", 
                       processed=date_processing_success,
                       failed=date_processing_errors,
                       is_success=True)
        
        # 7. 记录处理统计
        logger.log_data_processing("purchase_inbound", len(df), len(data), conversion_errors)
        
        logger.info(f"进货入库明细表解析成功完成", 
                   input_rows=len(df),
                   output_records=len(data),
                   is_success=True)
        
        logger.end_operation(operation_index, 
                           success=True, 
                           records=len(data),
                           conversion_errors=conversion_errors)
        
        logger.clear_context()
        return data
        
    except Exception as e:
        logger.error(f"进货入库明细表解析失败", 
                    error=str(e),
                    include_traceback=True)
        logger.end_operation(operation_index, success=False, error=str(e))
        logger.clear_context()
        raise
    finally:
        # 新增：关闭数据库连接
        if db_client:
            db_client.close()
            logger.info("数据库连接已关闭")


def save_purchase_inbound_data(purchase_inbound_data: List[Dict[str, Any]], output_file: str = "docs/purchase_inbound.json"):
    """
    保存进货入库明细数据为JSON文件
    
    Args:
        purchase_inbound_data: 进货入库明细数据列表
        output_file: 输出文件路径
    """
    try:
        # 添加元数据
        output_data = {
            "metadata": {
                "table_name": "purchase_inbound",
                "table_chinese_name": "进货入库明细表",
                "total_records": len(purchase_inbound_data),
                "generated_by": "parse4_purchase_inbound.py"
            },
            "data": purchase_inbound_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"进货入库明细数据已保存到: {output_file}")
        
    except Exception as e:
        print(f"保存进货入库明细数据时出错: {str(e)}")
        raise

def main():
    """
    测试函数 - 增强版
    """
    logger = EnhancedLogger("Parse_Purchase_Inbound_Test", "DEBUG")
    
    excel_file = "docs/imsviewer.xlsx" # 修正了文件路径
    
    try:
        # 简化日志调用以进行调试
        logger.info("--- 开始进货入库明细表解析测试 ---")
        
        if not os.path.exists(excel_file):
            logger.error(f"测试文件不存在", file_path=excel_file)
            return
        
        data = parse_purchase_inbound(excel_file, logger=logger)
        
        logger.info(f"解析测试完成", 
                   records=len(data),
                   sample_record=data[0] if data else None,
                   is_success=True)
        
        print(f"\n=== 保存进货入库明细数据到docs目录 ===")
        save_purchase_inbound_data(data)
        
        print(f"\n解析到 {len(data)} 条记录")
        if data:
            print("\n=== 前两条记录 ===")
            print(json.dumps(data[:2], ensure_ascii=False, indent=2, default=str))
        
        # 打印摘要
        logger.print_summary()
        
        # 导出报告
        report_path = logger.export_report()
        print(f"\n详细报告已保存到: {report_path}")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误", 
                    error=str(e),
                    include_traceback=True)
        logger.print_summary()

if __name__ == "__main__":
    main()