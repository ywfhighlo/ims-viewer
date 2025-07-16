#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON数据导入器
将 all_parsed_data.json 文件中的数据导入到MongoDB数据库
集成增强的日期解析器和日志系统
"""

import json
import os
import pymongo
from datetime import datetime
from field_mapping_utils import FieldMappingUtils
from enhanced_date_parser import EnhancedDateParser
from enhanced_logger import EnhancedLogger
import argparse
import sys

# --- 配置 ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = os.environ.get('IMS_DB_NAME', 'ims_database')

def connect_mongodb(logger):
    """连接到MongoDB"""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        # 测试连接
        client.admin.command('ping')
        logger.info("成功连接到MongoDB", 
                   uri=MONGO_URI, 
                   database=DB_NAME, 
                   is_success=True)
        return client, db
    except pymongo.errors.ConnectionFailure as e:
        logger.error("MongoDB连接失败", 
                    uri=MONGO_URI, 
                    error=str(e), 
                    include_traceback=True)
        raise
    except Exception as e:
        logger.error("连接MongoDB时发生未知错误", 
                    error=str(e), 
                    include_traceback=True)
        raise

def get_date_fields(mapper: FieldMappingUtils, table_name: str, logger) -> list:
    """从词典获取指定表的所有日期类型字段"""
    try:
        date_fields = []
        chinese_fields = mapper.get_table_fields(table_name, "chinese")
        
        for ch_field in chinese_fields:
            info = mapper.get_field_info(ch_field)
            if info and info.get("data_type") == "date":
                english_field = info.get("english")
                if english_field:
                    date_fields.append(english_field)
        
        logger.info(f"识别日期字段", 
                   table=table_name, 
                   date_fields=date_fields, 
                   count=len(date_fields))
        return date_fields
        
    except Exception as e:
        logger.error(f"获取日期字段失败", 
                    table=table_name, 
                    error=str(e))
        return []

def process_date_fields(records: list, date_fields: list, table_name: str, logger) -> list:
    """使用增强的日期解析器处理日期字段"""
    if not date_fields or not records:
        return records
    
    date_parser = EnhancedDateParser()
    processed_count = 0
    failed_count = 0
    
    logger.set_context(table=table_name, operation="date_processing")
    
    for record in records:
        for field in date_fields:
            if field in record and record[field]:
                try:
                    original_value = record[field]
                    
                    # 跳过已经是datetime对象的字段
                    if isinstance(original_value, datetime):
                        processed_count += 1
                        continue
                    
                    # 只处理字符串类型的日期
                    if isinstance(original_value, str):
                        parsed_date = date_parser.parse_date(original_value)
                        
                        if parsed_date is not None:
                            record[field] = parsed_date
                            processed_count += 1
                        else:
                            logger.log_date_parsing_issue(field, original_value, table_name)
                            failed_count += 1
                            # 保持原值
                    else:
                        # 非字符串类型，尝试转换为字符串再解析
                        try:
                            str_value = str(original_value)
                            parsed_date = date_parser.parse_date(str_value)
                            if parsed_date is not None:
                                record[field] = parsed_date
                                processed_count += 1
                            else:
                                failed_count += 1
                        except Exception:
                            failed_count += 1
                            
                except Exception as e:
                    logger.error(f"处理日期字段时出错", 
                               field=field, 
                               value=str(record[field]), 
                               error=str(e))
                    failed_count += 1
    
    logger.info(f"日期字段处理完成", 
               processed=processed_count, 
               failed=failed_count, 
               total_fields=len(date_fields) * len(records),
               success_rate=f"{(processed_count/(processed_count+failed_count)*100):.1f}%" if (processed_count+failed_count) > 0 else "0%",
               is_success=True)
    
    logger.clear_context()
    return records

def create_indexes(collection, table_name: str, mapper: FieldMappingUtils, logger):
    """为集合创建索引"""
    try:
        table_schema = mapper.get_table_schema(table_name)
        indexes = table_schema.get("indexes", [])
        
        if not indexes:
            logger.info(f"未找到索引配置", table=table_name)
            return
        
        created_indexes = 0
        failed_indexes = 0
        
        # 先删除旧索引，避免冲突（保留_id索引）
        try:
            collection.drop_indexes()
            logger.info(f"清除旧索引", table=table_name, is_success=True)
        except Exception as e:
            logger.warning(f"清除旧索引失败", table=table_name, error=str(e))
        
        for index_info in indexes:
            try:
                keys = [(key, pymongo.ASCENDING) for key in index_info["keys"]]
                is_unique = index_info.get("unique", False)
                index_name = f"{'_'.join(index_info['keys'])}_idx"
                
                collection.create_index(keys, name=index_name, unique=is_unique)
                
                logger.info(f"创建索引成功", 
                           table=table_name,
                           index_name=index_name, 
                           keys=index_info["keys"],
                           unique=is_unique,
                           is_success=True)
                created_indexes += 1
                
            except Exception as e:
                logger.warning(f"创建索引失败", 
                              table=table_name,
                              index_name=index_info.get('name', 'unknown'), 
                              error=str(e))
                failed_indexes += 1
        
        logger.info(f"索引创建完成", 
                   table=table_name,
                   created=created_indexes, 
                   failed=failed_indexes, 
                   total=len(indexes),
                   is_success=True)
                   
    except Exception as e:
        logger.error(f"创建索引时出错", 
                    table=table_name,
                    error=str(e), 
                    include_traceback=True)

def import_table_data(db, mapper: FieldMappingUtils, table_name: str, records: list, logger):
    """导入单个表的数据"""
    operation_index = logger.start_operation(f"导入表数据", 
                                           table=table_name,
                                           record_count=len(records))
    
    try:
        logger.set_context(table=table_name)
        collection = db[table_name]
        
        # 1. 清空集合
        delete_result = collection.delete_many({})
        logger.info(f"清空集合", 
                   deleted_count=delete_result.deleted_count, 
                   is_success=True)
        
        if not records:
            logger.warning(f"没有记录需要导入")
            logger.end_operation(operation_index, success=True, reason="no_records")
            logger.clear_context()
            return True
        
        # 2. 处理日期字段
        date_fields = get_date_fields(mapper, table_name, logger)
        if date_fields:
            records = process_date_fields(records, date_fields, table_name, logger)
        
        # 3. 插入新数据
        insert_result = collection.insert_many(records)
        inserted_count = len(insert_result.inserted_ids)
        
        logger.info(f"成功插入记录", 
                   inserted_count=inserted_count, 
                   is_success=True)
        
        # 记录数据处理统计
        logger.log_data_processing(table_name, len(records), inserted_count, 0)
        
        # 4. 创建索引
        create_indexes(collection, table_name, mapper, logger)
        
        logger.end_operation(operation_index, 
                           success=True, 
                           inserted_records=inserted_count)
        logger.clear_context()
        return True
        
    except Exception as e:
        logger.error(f"导入表数据失败", 
                    table=table_name,
                    error=str(e), 
                    include_traceback=True)
        logger.end_operation(operation_index, success=False, error=str(e))
        logger.clear_context()
        return False

def import_data(db, mapper: FieldMappingUtils, json_file_path: str, logger):
    """执行数据导入"""
    main_operation = logger.start_operation("数据导入主流程", 
                                          json_file=json_file_path)
    
    try:
        if not os.path.exists(json_file_path):
            logger.error(f"JSON数据文件不存在", file_path=json_file_path)
            logger.end_operation(main_operation, success=False, reason="file_not_found")
            return False
        
        # 读取JSON文件
        logger.info(f"开始读取JSON文件", file_path=json_file_path)
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        data_to_import = all_data.get("data", {})
        
        if not data_to_import:
            logger.warning(f"JSON文件中没有找到数据")
            logger.end_operation(main_operation, success=False, reason="no_data")
            return False
        
        logger.info(f"成功读取JSON文件", 
                   tables_count=len(data_to_import),
                   total_records=sum(len(records) for records in data_to_import.values()),
                   is_success=True)
        
        # 导入每个表的数据
        successful_tables = 0
        failed_tables = 0
        
        for table_name, records in data_to_import.items():
            logger.info(f"开始处理表", table=table_name, record_count=len(records))
            
            if import_table_data(db, mapper, table_name, records, logger):
                successful_tables += 1
            else:
                failed_tables += 1
        
        # 总结导入结果
        success = failed_tables == 0
        logger.info(f"数据导入完成", 
                   successful_tables=successful_tables,
                   failed_tables=failed_tables,
                   total_tables=len(data_to_import),
                   success_rate=f"{(successful_tables/len(data_to_import)*100):.1f}%",
                   is_success=success)
        
        logger.end_operation(main_operation, 
                           success=success,
                           successful_tables=successful_tables,
                           failed_tables=failed_tables)
        
        return success
        
    except Exception as e:
        logger.error(f"导入过程中发生严重错误", 
                    error=str(e), 
                    include_traceback=True)
        logger.end_operation(main_operation, success=False, error=str(e))
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="从指定的JSON文件向MongoDB导入数据。")
    parser.add_argument("json_path", help="包含要导入数据的JSON文件的完整路径。")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别 (默认: INFO)")
    parser.add_argument("--export-report", action="store_true",
                       help="导出详细报告")
    args = parser.parse_args()
    
    # 初始化日志系统
    logger = EnhancedLogger("MongoDB_Import", args.log_level)
    
    client = None
    try:
        logger.info(f"开始MongoDB数据导入", 
                   json_file=args.json_path,
                   log_level=args.log_level,
                   is_success=True)
        
        # 连接数据库
        client, db = connect_mongodb(logger)
        
        # 初始化字段映射工具
        mapper = FieldMappingUtils()
        logger.info(f"字段映射工具初始化完成", is_success=True)
        
        # 执行数据导入
        success = import_data(db, mapper, args.json_path, logger)
        
        if success:
            logger.info(f"所有数据导入成功完成", is_success=True)
        else:
            logger.error(f"数据导入过程中存在失败")
        
        # 打印摘要
        logger.print_summary()
        
        # 导出报告（如果需要）
        if args.export_report:
            report_path = logger.export_report()
            print(f"\n详细报告已保存到: {report_path}")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"程序执行过程中发生严重错误", 
                    error=str(e), 
                    include_traceback=True)
        logger.print_summary()
        sys.exit(1)
        
    finally:
        if client:
            client.close()
            logger.info(f"MongoDB连接已关闭", is_success=True)

if __name__ == "__main__":
    main()