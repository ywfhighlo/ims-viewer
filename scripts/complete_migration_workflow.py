#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vscode_config_reader import get_data_directory
"""
完整的数据迁移工作流脚本
整合Excel解析、标准编码生成和数据库导入的完整流程
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from vscode_config_reader import get_data_directory

class MigrationWorkflow:
    """数据迁移工作流管理器"""
    
    def __init__(self, excel_file: str = None):
        """初始化工作流"""
        if excel_file is None:
            data_dir = get_data_directory()
            self.excel_file = os.path.join(data_dir, "imsviewer.xlsx")
        else:
            self.excel_file = excel_file
        self.output_dir = get_data_directory()
        self.scripts_dir = "scripts"
        self.workflow_log = []
        
    def log_step(self, step: str, status: str, details: str = ""):
        """记录工作流步骤"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "step": step,
            "status": status,
            "details": details
        }
        self.workflow_log.append(log_entry)
        
        status_symbol = "✓" if status == "success" else "✗" if status == "error" else "⚠"
        print(f"{status_symbol} [{timestamp}] {step}: {status}")
        if details:
            print(f"   详情: {details}")
    
    def run_script(self, script_name: str, args: List[str] = None) -> bool:
        """运行Python脚本"""
        try:
            cmd = ["python", os.path.join(self.scripts_dir, script_name)]
            if args:
                cmd.extend(args)
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
            
            if result.returncode == 0:
                return True
            else:
                print(f"脚本执行失败: {script_name}")
                print(f"错误输出: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"运行脚本 {script_name} 时出错: {str(e)}")
            return False
    
    def check_prerequisites(self) -> bool:
        """检查前置条件"""
        print("=== 检查前置条件 ===")
        
        # 检查Excel文件
        if not os.path.exists(self.excel_file):
            self.log_step("检查Excel文件", "error", f"文件不存在: {self.excel_file}")
            return False
        self.log_step("检查Excel文件", "success", f"文件存在: {self.excel_file}")
        
        # 检查必要的脚本
        required_scripts = [
            "parse_manager.py",
            "generate_standard_material_table.py",
            "import_to_mongodb_with_standard_codes.py"
        ]
        
        for script in required_scripts:
            script_path = os.path.join(self.scripts_dir, script)
            if not os.path.exists(script_path):
                self.log_step("检查脚本", "error", f"脚本不存在: {script}")
                return False
        
        self.log_step("检查脚本", "success", "所有必要脚本存在")
        
        # 检查输出目录
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.log_step("创建输出目录", "success", f"目录已创建: {self.output_dir}")
        else:
            self.log_step("检查输出目录", "success", f"目录存在: {self.output_dir}")
        
        return True
    
    def step1_parse_excel(self) -> bool:
        """步骤1: 解析Excel文件生成JSON"""
        print("\n=== 步骤1: 解析Excel文件 ===")
        
        output_file = os.path.join(self.output_dir, "parsed_data.json")
        
        if self.run_script("parse_manager.py", [self.excel_file, output_file]):
            self.log_step("解析Excel", "success", f"生成文件: {output_file}")
            
            # 检查生成的分表文件
            expected_files = [
                "materials.json", "suppliers.json", "customers.json",
                "purchase_params.json", "purchase_inbound.json", "sales_outbound.json",
                "inventory_stats.json", "receipt_details.json", "payment_details.json"
            ]
            
            missing_files = []
            for file in expected_files:
                if not os.path.exists(os.path.join(self.output_dir, file)):
                    missing_files.append(file)
            
            if missing_files:
                self.log_step("检查分表文件", "warning", f"缺失文件: {', '.join(missing_files)}")
            else:
                self.log_step("检查分表文件", "success", "所有分表文件已生成")
            
            return True
        else:
            self.log_step("解析Excel", "error", "Excel解析失败")
            return False
    
    def step2_generate_standard_codes(self) -> bool:
        """步骤2: 生成标准物料编码表"""
        print("\n=== 步骤2: 生成标准物料编码表 ===")
        
        if self.run_script("generate_standard_material_table.py"):
            # 检查生成的文件
            expected_files = [
                "standard_material_table.json",
                "standard_material_table.sql",
                "standard_material_code_mapping.json"
            ]
            
            all_generated = True
            for file in expected_files:
                file_path = os.path.join(self.output_dir, file)
                if os.path.exists(file_path):
                    self.log_step("生成标准编码文件", "success", f"文件已生成: {file}")
                else:
                    self.log_step("生成标准编码文件", "error", f"文件未生成: {file}")
                    all_generated = False
            
            if all_generated:
                # 读取映射文件统计信息
                mapping_file = os.path.join(self.output_dir, "standard_material_code_mapping.json")
                try:
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mapping_count = len(mapping_data.get('mappings', {}))
                        self.log_step("标准编码统计", "success", f"生成 {mapping_count} 个编码映射")
                except Exception as e:
                    self.log_step("标准编码统计", "warning", f"无法读取映射文件: {str(e)}")
            
            return all_generated
        else:
            self.log_step("生成标准编码", "error", "标准编码生成失败")
            return False
    
    def step3_import_to_database(self) -> bool:
        """步骤3: 导入数据到MongoDB"""
        print("\n=== 步骤3: 导入数据到MongoDB ===")
        
        if self.run_script("import_to_mongodb_with_standard_codes.py"):
            self.log_step("数据库导入", "success", "数据已成功导入到MongoDB")
            return True
        else:
            self.log_step("数据库导入", "error", "数据库导入失败")
            return False
    
    def step4_verify_import(self) -> bool:
        """步骤4: 验证导入结果"""
        print("\n=== 步骤4: 验证导入结果 ===")
        
        if self.run_script("verify_import.py"):
            self.log_step("验证导入", "success", "数据导入验证通过")
            return True
        else:
            self.log_step("验证导入", "error", "数据导入验证失败")
            return False
    
    def generate_workflow_report(self):
        """生成工作流报告"""
        print("\n" + "=" * 80)
        print("数据迁移工作流完成报告")
        print("=" * 80)
        
        # 统计步骤结果
        total_steps = len(self.workflow_log)
        success_steps = len([log for log in self.workflow_log if log['status'] == 'success'])
        error_steps = len([log for log in self.workflow_log if log['status'] == 'error'])
        warning_steps = len([log for log in self.workflow_log if log['status'] == 'warning'])
        
        print(f"总步骤数: {total_steps}")
        print(f"成功: {success_steps}, 错误: {error_steps}, 警告: {warning_steps}")
        
        if error_steps == 0:
            print("\n🎉 工作流执行成功!")
        else:
            print("\n⚠️ 工作流执行中有错误，请检查日志")
        
        # 保存详细日志
        log_file = os.path.join(self.output_dir, "migration_workflow_log.json")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "workflow_summary": {
                        "total_steps": total_steps,
                        "success_steps": success_steps,
                        "error_steps": error_steps,
                        "warning_steps": warning_steps,
                        "start_time": self.workflow_log[0]['timestamp'] if self.workflow_log else None,
                        "end_time": self.workflow_log[-1]['timestamp'] if self.workflow_log else None
                    },
                    "detailed_log": self.workflow_log
                }, f, ensure_ascii=False, indent=2)
            print(f"\n详细日志已保存到: {log_file}")
        except Exception as e:
            print(f"\n保存日志失败: {str(e)}")
    
    def run_complete_workflow(self) -> bool:
        """运行完整的迁移工作流"""
        print("开始执行完整的数据迁移工作流...")
        print(f"Excel文件: {self.excel_file}")
        print(f"输出目录: {self.output_dir}")
        
        # 检查前置条件
        if not self.check_prerequisites():
            return False
        
        # 执行各个步骤
        steps = [
            ("解析Excel文件", self.step1_parse_excel),
            ("生成标准编码", self.step2_generate_standard_codes),
            ("导入数据库", self.step3_import_to_database),
            ("验证导入", self.step4_verify_import)
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                self.log_step(f"工作流中断", "error", f"步骤失败: {step_name}")
                self.generate_workflow_report()
                return False
        
        self.log_step("工作流完成", "success", "所有步骤执行成功")
        self.generate_workflow_report()
        return True

def main():
    """主函数"""
    import argparse
    
    # 获取默认Excel文件路径
    default_excel = os.path.join(get_data_directory(), "imsviewer.xlsx")
    
    parser = argparse.ArgumentParser(description="完整的数据迁移工作流")
    parser.add_argument("--excel", default=default_excel, help="Excel文件路径")
    parser.add_argument("--step", choices=["all", "parse", "codes", "import", "verify"], 
                       default="all", help="执行特定步骤")
    
    args = parser.parse_args()
    
    workflow = MigrationWorkflow(args.excel)
    
    if args.step == "all":
        success = workflow.run_complete_workflow()
    elif args.step == "parse":
        success = workflow.check_prerequisites() and workflow.step1_parse_excel()
    elif args.step == "codes":
        success = workflow.step2_generate_standard_codes()
    elif args.step == "import":
        success = workflow.step3_import_to_database()
    elif args.step == "verify":
        success = workflow.step4_verify_import()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()