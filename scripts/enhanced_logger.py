#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的日志系统
支持分级日志、错误统计、上下文信息和日志导出
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import traceback
from collections import defaultdict, Counter

class EnhancedLogger:
    """增强的日志系统"""
    
    def __init__(self, name: str = "IMS_Import", log_level: str = "INFO"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 统计信息
        self.stats = {
            'errors': Counter(),
            'warnings': Counter(),
            'info': Counter(),
            'debug': Counter(),
            'total_records_processed': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'start_time': datetime.now(),
            'operations': []
        }
        
        # 错误详情存储
        self.error_details = []
        self.warning_details = []
        
        # 上下文信息
        self.context = {}
        
        # 设置日志格式
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志格式和处理器"""
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器（可选）- 使用系统临时目录避免只读文件系统问题
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "ims_viewer_logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.log_file_path = log_file
    
    def set_context(self, **kwargs):
        """设置上下文信息"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """清除上下文信息"""
        self.context.clear()
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        full_message = self._format_message(message, **kwargs)
        self.logger.error(full_message)
        
        # 统计和详情
        self.stats['errors'][message] += 1
        self.stats['failed_operations'] += 1
        
        error_detail = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'context': self.context.copy(),
            'additional_info': kwargs,
            'traceback': traceback.format_exc() if kwargs.get('include_traceback', False) else None
        }
        self.error_details.append(error_detail)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        full_message = self._format_message(message, **kwargs)
        self.logger.warning(full_message)
        
        # 统计和详情
        self.stats['warnings'][message] += 1
        
        warning_detail = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'context': self.context.copy(),
            'additional_info': kwargs
        }
        self.warning_details.append(warning_detail)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        full_message = self._format_message(message, **kwargs)
        self.logger.info(full_message)
        
        # 统计
        self.stats['info'][message] += 1
        if kwargs.get('is_success', False):
            self.stats['successful_operations'] += 1
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        full_message = self._format_message(message, **kwargs)
        self.logger.debug(full_message)
        
        # 统计
        self.stats['debug'][message] += 1
    
    def _format_message(self, message: str, **kwargs) -> str:
        """格式化日志消息"""
        parts = [message]
        
        # 添加上下文信息
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            parts.append(f"[Context: {context_str}]")
        
        # 添加额外信息
        if kwargs:
            # 过滤掉特殊参数
            filtered_kwargs = {k: v for k, v in kwargs.items() 
                             if k not in ['include_traceback', 'is_success']}
            if filtered_kwargs:
                extra_str = ", ".join([f"{k}={v}" for k, v in filtered_kwargs.items()])
                parts.append(f"[Extra: {extra_str}]")
        
        return " ".join(parts)
    
    def start_operation(self, operation_name: str, **kwargs):
        """开始一个操作"""
        operation = {
            'name': operation_name,
            'start_time': datetime.now(),
            'context': self.context.copy(),
            'additional_info': kwargs,
            'status': 'running'
        }
        self.stats['operations'].append(operation)
        self.info(f"开始操作: {operation_name}", **kwargs)
        return len(self.stats['operations']) - 1  # 返回操作索引
    
    def end_operation(self, operation_index: int, success: bool = True, **kwargs):
        """结束一个操作"""
        if 0 <= operation_index < len(self.stats['operations']):
            operation = self.stats['operations'][operation_index]
            operation['end_time'] = datetime.now()
            operation['duration'] = (operation['end_time'] - operation['start_time']).total_seconds()
            operation['status'] = 'success' if success else 'failed'
            operation['result_info'] = kwargs
            
            status_msg = "成功" if success else "失败"
            self.info(f"操作 {operation['name']} {status_msg}", 
                     duration=f"{operation['duration']:.2f}s", 
                     is_success=success, **kwargs)
    
    def log_data_processing(self, table_name: str, total_records: int, 
                          processed_records: int, failed_records: int = 0):
        """记录数据处理统计"""
        self.stats['total_records_processed'] += processed_records
        
        self.info(f"数据处理完成", 
                 table=table_name,
                 total=total_records,
                 processed=processed_records,
                 failed=failed_records,
                 success_rate=f"{(processed_records/total_records*100):.1f}%" if total_records > 0 else "0%",
                 is_success=True)
    
    def log_field_mapping_issue(self, field_name: str, table_name: str, 
                               issue_type: str = "missing_mapping"):
        """记录字段映射问题"""
        self.warning(f"字段映射问题: {issue_type}", 
                    field=field_name, 
                    table=table_name,
                    suggestion=f"请在字段映射字典中添加 '{field_name}' 的英文映射")
    
    def log_date_parsing_issue(self, field_name: str, value: str, 
                              table_name: str = None):
        """记录日期解析问题"""
        self.warning(f"日期解析失败", 
                    field=field_name, 
                    value=value,
                    table=table_name,
                    suggestion="请检查日期格式或添加到特殊值列表")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        end_time = datetime.now()
        duration = (end_time - self.stats['start_time']).total_seconds()
        
        return {
            'summary': {
                'start_time': self.stats['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'total_records_processed': self.stats['total_records_processed'],
                'successful_operations': self.stats['successful_operations'],
                'failed_operations': self.stats['failed_operations'],
                'success_rate': f"{(self.stats['successful_operations']/(self.stats['successful_operations']+self.stats['failed_operations'])*100):.1f}%" if (self.stats['successful_operations']+self.stats['failed_operations']) > 0 else "0%"
            },
            'message_counts': {
                'errors': dict(self.stats['errors']),
                'warnings': dict(self.stats['warnings']),
                'info': dict(self.stats['info']),
                'debug': dict(self.stats['debug'])
            },
            'operations': self.stats['operations'],
            'error_details': self.error_details,
            'warning_details': self.warning_details
        }
    
    def export_report(self, output_path: Optional[str] = None) -> str:
        """导出详细报告"""
        if output_path is None:
            output_path = f"import_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'logger_name': self.name,
                'log_file': str(self.log_file_path)
            },
            'statistics': self.get_statistics()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        self.info(f"报告已导出", output_path=output_path, is_success=True)
        return output_path
    
    def print_summary(self):
        """打印摘要信息"""
        stats = self.get_statistics()
        summary = stats['summary']
        
        print("\n" + "="*50)
        print("           导入操作摘要报告")
        print("="*50)
        print(f"开始时间: {summary['start_time']}")
        print(f"结束时间: {summary['end_time']}")
        print(f"总耗时: {summary['duration_seconds']:.2f} 秒")
        print(f"处理记录数: {summary['total_records_processed']}")
        print(f"成功操作: {summary['successful_operations']}")
        print(f"失败操作: {summary['failed_operations']}")
        print(f"成功率: {summary['success_rate']}")
        
        # 错误和警告统计
        error_count = sum(stats['message_counts']['errors'].values())
        warning_count = sum(stats['message_counts']['warnings'].values())
        
        if error_count > 0:
            print(f"\n❌ 错误总数: {error_count}")
            for msg, count in stats['message_counts']['errors'].items():
                print(f"   - {msg}: {count} 次")
        
        if warning_count > 0:
            print(f"\n⚠️  警告总数: {warning_count}")
            for msg, count in stats['message_counts']['warnings'].items():
                print(f"   - {msg}: {count} 次")
        
        if error_count == 0 and warning_count == 0:
            print("\n✅ 没有错误或警告")
        
        print("="*50)

# 全局日志实例
enhanced_logger = EnhancedLogger()

# 便捷函数
def get_logger(name: str = "IMS_Import") -> EnhancedLogger:
    """获取日志实例"""
    return EnhancedLogger(name)

def log_error(message: str, **kwargs):
    """便捷函数：记录错误"""
    enhanced_logger.error(message, **kwargs)

def log_warning(message: str, **kwargs):
    """便捷函数：记录警告"""
    enhanced_logger.warning(message, **kwargs)

def log_info(message: str, **kwargs):
    """便捷函数：记录信息"""
    enhanced_logger.info(message, **kwargs)

def log_debug(message: str, **kwargs):
    """便捷函数：记录调试信息"""
    enhanced_logger.debug(message, **kwargs)

if __name__ == "__main__":
    # 测试代码
    logger = EnhancedLogger("Test")
    
    # 设置上下文
    logger.set_context(table="test_table", user="admin")
    
    # 测试各种日志级别
    op_index = logger.start_operation("测试操作")
    
    logger.info("这是一条信息")
    logger.warning("这是一条警告", field="test_field")
    logger.error("这是一条错误", error_code=500)
    
    logger.log_data_processing("test_table", 100, 95, 5)
    logger.log_field_mapping_issue("测试字段", "test_table")
    logger.log_date_parsing_issue("date_field", "invalid_date")
    
    logger.end_operation(op_index, success=True, records_processed=100)
    
    # 打印摘要
    logger.print_summary()
    
    # 导出报告
    report_path = logger.export_report()
    print(f"\n报告已保存到: {report_path}")