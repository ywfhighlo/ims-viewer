#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据解析管理器
调用所有表的解析脚本，并将结果汇总到一个文件中
集成增强的日志系统和错误处理
"""

import json
import os
import traceback
from datetime import datetime
import argparse
import sys
from enhanced_logger import EnhancedLogger

# 导入所有解析函数
import importlib

# 直接导入所有解析函数
from parse1_supplier_info import parse_supplier_info
from parse2_customer_info import parse_customer_info
from parse3_purchase_params import parse_purchase_params
from parse4_purchase_inbound import parse_purchase_inbound
from parse5_sales_outbound import parse_sales_outbound
from parse6_payment_details import parse_payment_details
from parse7_receipt_details import parse_receipt_details
from parse8_inventory_stats import parse_inventory_stats

def run_all_parsers(excel_file_path: str, logger: EnhancedLogger) -> dict:
    """
    运行所有解析器并返回汇总数据
    """
    main_operation = logger.start_operation("Excel数据解析主流程", 
                                          excel_file=excel_file_path)
    
    all_data = {}
    parsers = {
        "suppliers": ("供应商信息表", parse_supplier_info),
        "customers": ("客户信息表", parse_customer_info),
        "purchase_params": ("进货参数表", parse_purchase_params),
        "purchase_inbound": ("进货入库明细表", parse_purchase_inbound),
        "sales_outbound": ("销售出库明细表", parse_sales_outbound),
        "payment_details": ("付款明细表", parse_payment_details),
        "receipt_details": ("收款明细表", parse_receipt_details),
        "inventory_stats": ("库存统计表", parse_inventory_stats),
    }
    
    successful_tables = 0
    failed_tables = 0
    total_records = 0

    for table_name, (sheet_name, parser_func) in parsers.items():
        operation_index = logger.start_operation(f"解析工作表", 
                                                table=table_name,
                                                sheet=sheet_name)
        try:
            logger.set_context(table=table_name, sheet=sheet_name)
            logger.info(f"开始解析工作表", sheet=sheet_name)
            
            data = parser_func(excel_file_path, sheet_name)
            
            if data is not None:
                all_data[table_name] = data
                record_count = len(data) if isinstance(data, list) else 0
                total_records += record_count
                
                logger.info(f"工作表解析成功", 
                           sheet=sheet_name,
                           record_count=record_count,
                           is_success=True)
                
                logger.log_data_processing(table_name, record_count, record_count, 0)
                logger.end_operation(operation_index, success=True, records=record_count)
                successful_tables += 1
            else:
                logger.warning(f"工作表解析返回空数据", sheet=sheet_name)
                all_data[table_name] = []
                logger.end_operation(operation_index, success=False, reason="empty_data")
                failed_tables += 1
                
        except Exception as e:
            logger.error(f"解析工作表失败", 
                        sheet=sheet_name,
                        error=str(e),
                        include_traceback=True)
            
            # 记录详细的错误信息
            all_data[table_name] = []
            logger.end_operation(operation_index, success=False, error=str(e))
            failed_tables += 1
        
        finally:
            logger.clear_context()
    
    # 总结解析结果
    success = failed_tables == 0
    logger.info(f"Excel解析完成", 
               successful_tables=successful_tables,
               failed_tables=failed_tables,
               total_tables=len(parsers),
               total_records=total_records,
               success_rate=f"{(successful_tables/len(parsers)*100):.1f}%",
               is_success=success)
    
    logger.end_operation(main_operation, 
                       success=success,
                       successful_tables=successful_tables,
                       failed_tables=failed_tables,
                       total_records=total_records)
    
    return all_data

def extract_materials_from_all_data(all_data: dict, logger: EnhancedLogger) -> list:
    """
    从所有表中提取物料信息
    """
    materials = []
    material_codes_seen = set()
    
    # 从进货参数表提取物料
    if 'purchase_params' in all_data and all_data['purchase_params']:
        for item in all_data['purchase_params']:
            material_code = item.get('material_code', '')
            if material_code and material_code not in material_codes_seen:
                materials.append({
                    'material_code': material_code,
                    'material_name': item.get('material_name', ''),
                    'specification': item.get('specification', ''),
                    'unit': item.get('unit', '台'),
                    'supplier_name': item.get('supplier_name', ''),
                    'source_table': 'purchase_params',
                    'additional_info': {
                        'initial_quantity': item.get('initial_quantity', 0),
                        'safety_stock': item.get('safety_stock', 0),
                        'parameter_description': item.get('parameter_description', ''),
                        'handler': item.get('handler', '')
                    }
                })
                material_codes_seen.add(material_code)
    
    # 从进货入库明细表提取物料
    if 'purchase_inbound' in all_data and all_data['purchase_inbound']:
        for item in all_data['purchase_inbound']:
            material_code = item.get('material_code', '')
            if material_code and material_code not in material_codes_seen:
                materials.append({
                    'material_code': material_code,
                    'material_name': item.get('material_name', ''),
                    'specification': item.get('specification', ''),
                    'unit': item.get('unit', '台'),
                    'supplier_name': item.get('supplier_name', ''),
                    'source_table': 'purchase_inbound',
                    'additional_info': {
                        'handler': item.get('handler', '')
                    }
                })
                material_codes_seen.add(material_code)
    
    # 从销售出库明细表提取物料
    if 'sales_outbound' in all_data and all_data['sales_outbound']:
        for item in all_data['sales_outbound']:
            material_code = item.get('material_code', '')
            if material_code and material_code not in material_codes_seen:
                materials.append({
                    'material_code': material_code,
                    'material_name': item.get('material_name', ''),
                    'specification': item.get('specification', ''),
                    'unit': item.get('unit', '台'),
                    'supplier_name': '',  # 销售记录通常没有供应商信息
                    'source_table': 'sales_outbound',
                    'additional_info': {
                        'handler': item.get('handler', '')
                    }
                })
                material_codes_seen.add(material_code)
    
    logger.info(f"物料信息提取完成", 
               total_materials=len(materials),
               unique_codes=len(material_codes_seen),
               is_success=True)
    
    return materials

def save_individual_table_files(all_data: dict, output_dir: str, logger: EnhancedLogger):
    """
    保存各个表的独立JSON文件
    """
    operation_index = logger.start_operation("保存分表JSON文件", 
                                           output_dir=output_dir)
    
    try:
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录", directory=output_dir, is_success=True)
        
        saved_files = []
        
        # 保存各个表的数据
        for table_name, data in all_data.items():
            if data:  # 只保存非空数据
                table_output = {
                    "metadata": {
                        "table_name": table_name,
                        "source": "excel_sheet",
                        "generated_at": datetime.now().isoformat(),
                        "total_records": len(data) if isinstance(data, list) else 0
                    },
                    "data": data
                }
                
                file_path = os.path.join(output_dir, f"{table_name}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(table_output, f, ensure_ascii=False, indent=2, default=str)
                
                saved_files.append(file_path)
                logger.info(f"表文件保存成功", 
                           table=table_name,
                           file_path=file_path,
                           records=len(data) if isinstance(data, list) else 0,
                           is_success=True)
        
        # 提取并保存物料信息
        materials = extract_materials_from_all_data(all_data, logger)
        if materials:
            materials_output = {
                "metadata": {
                    "source": "excel_extraction",
                    "generated_at": datetime.now().isoformat(),
                    "total_count": len(materials),
                    "extraction_tables": ["purchase_params", "purchase_inbound", "sales_outbound"]
                },
                "data": materials
            }
            
            materials_file = os.path.join(output_dir, "materials.json")
            with open(materials_file, 'w', encoding='utf-8') as f:
                json.dump(materials_output, f, ensure_ascii=False, indent=2, default=str)
            
            saved_files.append(materials_file)
            logger.info(f"物料文件保存成功", 
                       file_path=materials_file,
                       materials_count=len(materials),
                       is_success=True)
        
        logger.info(f"分表文件保存完成", 
                   total_files=len(saved_files),
                   output_dir=output_dir,
                   is_success=True)
        
        logger.end_operation(operation_index, 
                           success=True, 
                           files_saved=len(saved_files))
        
        return saved_files
        
    except Exception as e:
        logger.error(f"保存分表文件失败", 
                    output_dir=output_dir,
                    error=str(e),
                    include_traceback=True)
        logger.end_operation(operation_index, success=False, error=str(e))
        raise

def save_all_data(all_data: dict, output_file: str, logger: EnhancedLogger):
    """
    将所有解析后的数据保存到一个JSON文件中，同时生成分表文件
    """
    operation_index = logger.start_operation("保存解析数据", 
                                           output_file=output_file)
    
    try:
        # 计算统计信息
        total_records = sum(len(records) if isinstance(records, list) else 0 
                          for records in all_data.values())
        
        output = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_tables": len(all_data),
                "total_records": total_records,
                "source": "parse_manager.py",
                "version": "2.0"
            },
            "data": all_data
        }
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录", directory=output_dir, is_success=True)
        
        # 保存主文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        
        # 验证文件大小
        file_size = os.path.getsize(output_file)
        
        logger.info(f"主数据文件保存成功", 
                   output_file=output_file,
                   total_tables=len(all_data),
                   total_records=total_records,
                   file_size_mb=f"{file_size/1024/1024:.2f}MB",
                   is_success=True)
        
        # 保存分表文件
        saved_files = save_individual_table_files(all_data, output_dir, logger)
        
        logger.end_operation(operation_index, 
                           success=True, 
                           file_size=file_size,
                           total_records=total_records,
                           individual_files=len(saved_files))
        
    except Exception as e:
        logger.error(f"保存汇总数据失败", 
                    output_file=output_file,
                    error=str(e),
                    include_traceback=True)
        logger.end_operation(operation_index, success=False, error=str(e))
        raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="从指定的Excel文件解析数据并保存为JSON。")
    parser.add_argument("excel_path", help="要解析的Excel文件的完整路径。")
    parser.add_argument("output_path", help="输出的JSON文件的完整路径。")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别 (默认: INFO)")
    parser.add_argument("--export-report", action="store_true",
                       help="导出详细报告")
    args = parser.parse_args()
    
    # 初始化日志系统
    logger = EnhancedLogger("Excel_Parser", args.log_level)
    
    try:
        # 验证输入文件
        if not os.path.exists(args.excel_path):
            logger.error(f"Excel文件不存在", file_path=args.excel_path)
            sys.exit(1)
        
        # 获取文件信息
        file_size = os.path.getsize(args.excel_path)
        logger.info(f"开始Excel数据解析", 
                   excel_file=args.excel_path,
                   output_file=args.output_path,
                   file_size_mb=f"{file_size/1024/1024:.2f}MB",
                   log_level=args.log_level,
                   is_success=True)
        
        # 执行解析
        all_data = run_all_parsers(args.excel_path, logger)
        
        # 保存数据
        save_all_data(all_data, args.output_path, logger)
        
        logger.info(f"Excel解析流程完成", 
                   output_file=args.output_path,
                   is_success=True)
        
        # 打印摘要
        logger.print_summary()
        
        # 导出报告（如果需要）
        if args.export_report:
            report_path = logger.export_report()
            print(f"\n详细报告已保存到: {report_path}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"解析过程中发生严重错误", 
                    error=str(e),
                    include_traceback=True)
        logger.print_summary()
        sys.exit(1)

if __name__ == "__main__":
    main()