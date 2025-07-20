#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导入导出服务
提供灵活的数据导入导出功能，支持多种格式
"""

import sys
import os
import json
import csv
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import tempfile
import io
from dataclasses import dataclass
import logging

# 添加脚本目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_config import get_database
from enhanced_logger import EnhancedLogger
from data_validator import DataValidator

# 尝试导入可选的依赖
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

@dataclass
class ImportResult:
    """导入结果数据类"""
    success: bool
    total_records: int
    imported_records: int
    failed_records: int
    errors: List[Dict[str, Any]]
    message: str
    execution_time: float

@dataclass
class ExportResult:
    """导出结果数据类"""
    success: bool
    file_path: str
    file_size: int
    record_count: int
    message: str
    execution_time: float

@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool
    valid_records: List[Dict[str, Any]]
    invalid_records: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    summary: Dict[str, int]

class ImportExportService:
    """数据导入导出服务类"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        self.db = get_database()
        if self.db is None:
            raise Exception("无法连接到数据库")
        self.logger = logger or EnhancedLogger("import_export_service")
        self.validator = DataValidator()
        
        # 支持的格式
        self.export_formats = ['excel', 'csv', 'json', 'pdf']
        self.import_formats = ['excel', 'csv', 'json']
        
        # 数据模式定义
        self.data_schemas = {
            'customers': {
                'required_fields': ['customer_name', 'contact_person'],
                'optional_fields': ['phone', 'email', 'address', 'credit_limit'],
                'field_types': {
                    'customer_name': str,
                    'contact_person': str,
                    'phone': str,
                    'email': str,
                    'address': str,
                    'credit_limit': float
                }
            },
            'suppliers': {
                'required_fields': ['supplier_name', 'contact_person'],
                'optional_fields': ['phone', 'email', 'address', 'payment_terms'],
                'field_types': {
                    'supplier_name': str,
                    'contact_person': str,
                    'phone': str,
                    'email': str,
                    'address': str,
                    'payment_terms': str
                }
            },
            'materials': {
                'required_fields': ['material_code', 'material_name', 'unit'],
                'optional_fields': ['category', 'specification', 'unit_price', 'supplier_code'],
                'field_types': {
                    'material_code': str,
                    'material_name': str,
                    'unit': str,
                    'category': str,
                    'specification': str,
                    'unit_price': float,
                    'supplier_code': str
                }
            }
        }

    def export_data(self, data: List[Dict], format: str, options: Dict = None) -> ExportResult:
        """
        导出数据到指定格式
        
        Args:
            data: 要导出的数据列表
            format: 导出格式 ('excel', 'csv', 'json', 'pdf')
            options: 导出选项，包含文件路径、标题等
            
        Returns:
            ExportResult: 导出结果
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"开始导出数据，格式: {format}, 记录数: {len(data)}")
            
            if format not in self.export_formats:
                raise ValueError(f"不支持的导出格式: {format}")
            
            if not data:
                raise ValueError("没有数据需要导出")
            
            options = options or {}
            
            # 生成文件路径
            if 'file_path' not in options:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"export_{timestamp}.{format}"
                file_path = os.path.join(tempfile.gettempdir(), filename)
            else:
                file_path = options['file_path']
            
            # 根据格式调用相应的导出方法
            if format == 'excel':
                self._export_to_excel(data, file_path, options)
            elif format == 'csv':
                self._export_to_csv(data, file_path, options)
            elif format == 'json':
                self._export_to_json(data, file_path, options)
            elif format == 'pdf':
                self._export_to_pdf(data, file_path, options)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = ExportResult(
                success=True,
                file_path=file_path,
                file_size=file_size,
                record_count=len(data),
                message=f"成功导出 {len(data)} 条记录到 {format} 格式",
                execution_time=execution_time
            )
            
            self.logger.info(f"数据导出完成，文件: {file_path}, 大小: {file_size} bytes")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"数据导出失败: {str(e)}")
            
            return ExportResult(
                success=False,
                file_path="",
                file_size=0,
                record_count=0,
                message=f"导出失败: {str(e)}",
                execution_time=execution_time
            )

    def _export_to_excel(self, data: List[Dict], file_path: str, options: Dict):
        """导出到Excel格式"""
        df = pd.DataFrame(data)
        
        # 创建Excel写入器
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # 写入数据
            sheet_name = options.get('sheet_name', 'Sheet1')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 获取工作表
            worksheet = writer.sheets[sheet_name]
            
            # 设置列宽自适应
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

    def _export_to_csv(self, data: List[Dict], file_path: str, options: Dict):
        """导出到CSV格式"""
        if not data:
            return
        
        encoding = options.get('encoding', 'utf-8-sig')  # 使用BOM确保中文正确显示
        
        with open(file_path, 'w', newline='', encoding=encoding) as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def _export_to_json(self, data: List[Dict], file_path: str, options: Dict):
        """导出到JSON格式"""
        json_options = {
            'ensure_ascii': False,
            'indent': options.get('indent', 2),
            'separators': (',', ': ')
        }
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, default=str, **json_options)

    def _export_to_pdf(self, data: List[Dict], file_path: str, options: Dict):
        """导出到PDF格式"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("PDF导出需要安装 reportlab 库: pip install reportlab")
        
        if not data:
            return
        
        # 创建PDF文档
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        story = []
        
        # 样式
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # 居中
        )
        
        # 添加标题
        title = options.get('title', '数据导出报告')
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # 准备表格数据
        if data:
            headers = list(data[0].keys())
            table_data = [headers]
            
            for row in data:
                table_data.append([str(row.get(header, '')) for header in headers])
            
            # 创建表格
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        
        # 添加页脚信息
        story.append(Spacer(1, 12))
        footer_text = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>总记录数: {len(data)}"
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # 构建PDF
        doc.build(story)

    def import_data(self, file_data: bytes, format: str, mapping: Dict = None, data_type: str = None) -> ImportResult:
        """
        从文件数据导入数据
        
        Args:
            file_data: 文件二进制数据
            format: 文件格式 ('excel', 'csv', 'json')
            mapping: 字段映射关系
            data_type: 数据类型 ('customers', 'suppliers', 'materials')
            
        Returns:
            ImportResult: 导入结果
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"开始导入数据，格式: {format}, 数据类型: {data_type}")
            
            if format not in self.import_formats:
                raise ValueError(f"不支持的导入格式: {format}")
            
            # 解析文件数据
            if format == 'excel':
                data = self._parse_excel_data(file_data)
            elif format == 'csv':
                data = self._parse_csv_data(file_data)
            elif format == 'json':
                data = self._parse_json_data(file_data)
            else:
                raise ValueError(f"未实现的格式解析: {format}")
            
            if not data:
                raise ValueError("文件中没有有效数据")
            
            # 应用字段映射
            if mapping:
                data = self._apply_field_mapping(data, mapping)
            
            # 验证数据
            validation_result = self.validate_import_data(data, data_type)
            
            # 导入有效数据
            imported_count = 0
            failed_count = 0
            errors = []
            
            if validation_result.valid_records:
                try:
                    if data_type and data_type in ['customers', 'suppliers', 'materials']:
                        imported_count = self._import_to_database(validation_result.valid_records, data_type)
                    else:
                        # 如果没有指定数据类型，只返回验证结果
                        imported_count = len(validation_result.valid_records)
                except Exception as e:
                    self.logger.error(f"数据库导入失败: {str(e)}")
                    errors.append({
                        'type': 'database_error',
                        'message': str(e),
                        'record_count': len(validation_result.valid_records)
                    })
            
            failed_count = len(validation_result.invalid_records)
            errors.extend(validation_result.errors)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = ImportResult(
                success=imported_count > 0 or failed_count == 0,
                total_records=len(data),
                imported_records=imported_count,
                failed_records=failed_count,
                errors=errors,
                message=f"导入完成: 成功 {imported_count} 条，失败 {failed_count} 条",
                execution_time=execution_time
            )
            
            self.logger.info(f"数据导入完成: {result.message}")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"数据导入失败: {str(e)}")
            
            return ImportResult(
                success=False,
                total_records=0,
                imported_records=0,
                failed_records=0,
                errors=[{'type': 'import_error', 'message': str(e)}],
                message=f"导入失败: {str(e)}",
                execution_time=execution_time
            )

    def _parse_excel_data(self, file_data: bytes) -> List[Dict]:
        """解析Excel数据"""
        try:
            # 使用pandas读取Excel
            df = pd.read_excel(io.BytesIO(file_data))
            
            # 清理数据
            df = df.dropna(how='all')  # 删除全空行
            df = df.fillna('')  # 填充空值
            
            # 转换为字典列表
            return df.to_dict('records')
            
        except Exception as e:
            raise ValueError(f"Excel文件解析失败: {str(e)}")

    def _parse_csv_data(self, file_data: bytes) -> List[Dict]:
        """解析CSV数据"""
        try:
            # 尝试检测编码
            content = file_data.decode('utf-8-sig')  # 优先尝试UTF-8 BOM
        except UnicodeDecodeError:
            try:
                content = file_data.decode('gbk')  # 尝试GBK编码
            except UnicodeDecodeError:
                content = file_data.decode('utf-8', errors='ignore')  # 忽略错误
        
        # 使用pandas读取CSV
        try:
            df = pd.read_csv(io.StringIO(content))
            df = df.dropna(how='all')
            df = df.fillna('')
            return df.to_dict('records')
        except Exception as e:
            raise ValueError(f"CSV文件解析失败: {str(e)}")

    def _parse_json_data(self, file_data: bytes) -> List[Dict]:
        """解析JSON数据"""
        try:
            content = file_data.decode('utf-8')
            data = json.loads(content)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise ValueError("JSON数据格式不正确，期望数组或对象")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON文件解析失败: {str(e)}")
        except UnicodeDecodeError as e:
            raise ValueError(f"文件编码错误: {str(e)}")

    def _apply_field_mapping(self, data: List[Dict], mapping: Dict) -> List[Dict]:
        """应用字段映射"""
        mapped_data = []
        
        for record in data:
            mapped_record = {}
            for source_field, target_field in mapping.items():
                if source_field in record:
                    mapped_record[target_field] = record[source_field]
            mapped_data.append(mapped_record)
        
        return mapped_data

    def validate_import_data(self, data: List[Dict], data_type: str = None) -> ValidationResult:
        """
        验证导入数据
        
        Args:
            data: 要验证的数据
            data_type: 数据类型 ('customers', 'suppliers', 'materials')
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            self.logger.info(f"开始验证数据，数据类型: {data_type}, 记录数: {len(data)}")
            
            valid_records = []
            invalid_records = []
            errors = []
            
            # 获取数据模式
            schema = self.data_schemas.get(data_type) if data_type else None
            
            for i, record in enumerate(data):
                try:
                    # 基本验证
                    if not record or not isinstance(record, dict):
                        invalid_records.append(record)
                        errors.append({
                            'row': i + 1,
                            'type': 'invalid_format',
                            'message': '记录格式无效'
                        })
                        continue
                    
                    # 如果有模式定义，进行详细验证
                    if schema:
                        validation_errors = self._validate_record_against_schema(record, schema)
                        if validation_errors:
                            invalid_records.append(record)
                            for error in validation_errors:
                                error['row'] = i + 1
                                errors.append(error)
                            continue
                    
                    # 数据类型验证和转换
                    cleaned_record = self._clean_and_validate_record(record, schema)
                    valid_records.append(cleaned_record)
                    
                except Exception as e:
                    invalid_records.append(record)
                    errors.append({
                        'row': i + 1,
                        'type': 'validation_error',
                        'message': str(e)
                    })
            
            summary = {
                'total_records': len(data),
                'valid_records': len(valid_records),
                'invalid_records': len(invalid_records),
                'error_count': len(errors)
            }
            
            result = ValidationResult(
                is_valid=len(invalid_records) == 0,
                valid_records=valid_records,
                invalid_records=invalid_records,
                errors=errors,
                summary=summary
            )
            
            self.logger.info(f"数据验证完成: {summary}")
            return result
            
        except Exception as e:
            self.logger.error(f"数据验证失败: {str(e)}")
            return ValidationResult(
                is_valid=False,
                valid_records=[],
                invalid_records=data,
                errors=[{'type': 'validation_error', 'message': str(e)}],
                summary={'total_records': len(data), 'valid_records': 0, 'invalid_records': len(data), 'error_count': 1}
            )

    def _validate_record_against_schema(self, record: Dict, schema: Dict) -> List[Dict]:
        """根据模式验证单个记录"""
        errors = []
        
        # 检查必需字段
        for field in schema.get('required_fields', []):
            if field not in record or not record[field]:
                errors.append({
                    'type': 'missing_required_field',
                    'field': field,
                    'message': f'缺少必需字段: {field}'
                })
        
        # 检查字段类型
        field_types = schema.get('field_types', {})
        for field, expected_type in field_types.items():
            if field in record and record[field]:
                try:
                    # 尝试类型转换
                    if expected_type == float:
                        float(record[field])
                    elif expected_type == int:
                        int(record[field])
                    elif expected_type == str:
                        str(record[field])
                except (ValueError, TypeError):
                    errors.append({
                        'type': 'invalid_type',
                        'field': field,
                        'expected_type': expected_type.__name__,
                        'actual_value': record[field],
                        'message': f'字段 {field} 类型错误，期望 {expected_type.__name__}'
                    })
        
        return errors

    def _clean_and_validate_record(self, record: Dict, schema: Dict = None) -> Dict:
        """清理和验证记录"""
        cleaned_record = {}
        
        for key, value in record.items():
            # 清理字符串值
            if isinstance(value, str):
                value = value.strip()
            
            # 类型转换
            if schema and key in schema.get('field_types', {}):
                expected_type = schema['field_types'][key]
                if value and expected_type in [int, float]:
                    try:
                        value = expected_type(value)
                    except (ValueError, TypeError):
                        pass  # 保持原值，让验证捕获错误
            
            cleaned_record[key] = value
        
        return cleaned_record

    def _import_to_database(self, data: List[Dict], data_type: str) -> int:
        """导入数据到数据库"""
        collection_name = data_type
        collection = self.db[collection_name]
        
        imported_count = 0
        
        for record in data:
            try:
                # 添加时间戳
                record['created_at'] = datetime.now()
                record['updated_at'] = datetime.now()
                
                # 插入记录
                result = collection.insert_one(record)
                if result.inserted_id:
                    imported_count += 1
                    
            except Exception as e:
                self.logger.error(f"插入记录失败: {str(e)}, 记录: {record}")
                continue
        
        return imported_count

    def get_import_template(self, data_type: str) -> bytes:
        """
        获取导入模板
        
        Args:
            data_type: 数据类型 ('customers', 'suppliers', 'materials')
            
        Returns:
            bytes: Excel模板文件的二进制数据
        """
        try:
            self.logger.info(f"生成导入模板，数据类型: {data_type}")
            
            if data_type not in self.data_schemas:
                raise ValueError(f"不支持的数据类型: {data_type}")
            
            schema = self.data_schemas[data_type]
            
            # 创建模板数据
            headers = schema['required_fields'] + schema.get('optional_fields', [])
            template_data = pd.DataFrame(columns=headers)
            
            # 添加示例行
            example_row = {}
            for field in headers:
                if field in schema['field_types']:
                    field_type = schema['field_types'][field]
                    if field_type == str:
                        example_row[field] = f"示例{field}"
                    elif field_type == float:
                        example_row[field] = 100.00
                    elif field_type == int:
                        example_row[field] = 1
                else:
                    example_row[field] = f"示例{field}"
            
            template_data = pd.concat([template_data, pd.DataFrame([example_row])], ignore_index=True)
            
            # 导出到Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                template_data.to_excel(writer, sheet_name='模板', index=False)
                
                # 获取工作表并设置样式
                worksheet = writer.sheets['模板']
                
                # 设置表头样式
                from openpyxl.styles import PatternFill, Font
                header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                header_font = Font(color="FFFFFF", bold=True)
                
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                
                # 设置列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            buffer.seek(0)
            template_bytes = buffer.read()
            
            self.logger.info(f"模板生成完成，大小: {len(template_bytes)} bytes")
            return template_bytes
            
        except Exception as e:
            self.logger.error(f"生成导入模板失败: {str(e)}")
            raise

if __name__ == '__main__':
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='数据导入导出服务')
    parser.add_argument('--action', required=True, choices=['export', 'import', 'template', 'validate'], help='操作类型')
    parser.add_argument('--format', choices=['excel', 'csv', 'json', 'pdf'], help='文件格式')
    parser.add_argument('--data-type', choices=['customers', 'suppliers', 'materials'], help='数据类型')
    parser.add_argument('--file-path', help='文件路径')
    parser.add_argument('--collection', help='数据库集合名称')
    parser.add_argument('--query', help='查询条件（JSON格式）')
    parser.add_argument('--mapping', help='字段映射（JSON格式）')
    parser.add_argument('--options', help='额外选项（JSON格式）')
    
    args = parser.parse_args()
    
    try:
        service = ImportExportService()
        result = None
        
        if args.action == 'export':
            # 导出数据
            if not args.collection:
                raise ValueError("导出操作需要指定 --collection 参数")
            
            # 从数据库获取数据
            query = json.loads(args.query) if args.query else {}
            collection = service.db[args.collection]
            data = list(collection.find(query))
            
            # 清理MongoDB的_id字段
            for record in data:
                if '_id' in record:
                    record['_id'] = str(record['_id'])
            
            # 导出选项
            options = json.loads(args.options) if args.options else {}
            if args.file_path:
                options['file_path'] = args.file_path
            
            result = service.export_data(data, args.format, options)
            
        elif args.action == 'import':
            # 导入数据
            if not args.file_path or not os.path.exists(args.file_path):
                raise ValueError("导入操作需要指定有效的 --file-path 参数")
            
            # 读取文件
            with open(args.file_path, 'rb') as f:
                file_data = f.read()
            
            # 字段映射
            mapping = json.loads(args.mapping) if args.mapping else None
            
            result = service.import_data(file_data, args.format, mapping, args.data_type)
            
        elif args.action == 'template':
            # 生成模板
            if not args.data_type:
                raise ValueError("生成模板需要指定 --data-type 参数")
            
            template_data = service.get_import_template(args.data_type)
            
            # 保存模板文件
            template_path = args.file_path or f"{args.data_type}_template.xlsx"
            with open(template_path, 'wb') as f:
                f.write(template_data)
            
            result = {
                'success': True,
                'message': f'模板已生成: {template_path}',
                'file_path': template_path,
                'file_size': len(template_data)
            }
            
        elif args.action == 'validate':
            # 验证数据
            if not args.file_path or not os.path.exists(args.file_path):
                raise ValueError("验证操作需要指定有效的 --file-path 参数")
            
            # 读取文件
            with open(args.file_path, 'rb') as f:
                file_data = f.read()
            
            # 解析数据
            if args.format == 'excel':
                data = service._parse_excel_data(file_data)
            elif args.format == 'csv':
                data = service._parse_csv_data(file_data)
            elif args.format == 'json':
                data = service._parse_json_data(file_data)
            else:
                raise ValueError(f"不支持的格式: {args.format}")
            
            # 验证数据
            validation_result = service.validate_import_data(data, args.data_type)
            
            result = {
                'success': validation_result.is_valid,
                'summary': validation_result.summary,
                'errors': validation_result.errors,
                'message': f"验证完成: 有效记录 {len(validation_result.valid_records)} 条，无效记录 {len(validation_result.invalid_records)} 条"
            }
        
        # 输出结果
        if hasattr(result, '__dict__'):
            # 如果是dataclass对象，转换为字典
            result_dict = result.__dict__
        else:
            result_dict = result
        
        print(json.dumps(result_dict, ensure_ascii=False, default=str))
        
    except Exception as e:
        error_result = {
            'success': False,
            'message': f'操作失败: {str(e)}'
        }
        print(json.dumps(error_result, ensure_ascii=False)) 