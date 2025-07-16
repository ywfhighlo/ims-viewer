#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端用户体验管理器
提供优化的前端加载体验和用户反馈
"""

import sys
import os
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.async_report_controller import get_async_controller


@dataclass
class UIState:
    """UI状态数据模型"""
    is_loading: bool = False
    progress: float = 0.0
    message: str = ""
    error_message: Optional[str] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class UIExperienceManager:
    """前端用户体验管理器"""
    
    def __init__(self, logger: Optional[EnhancedLogger] = None):
        """
        初始化用户体验管理器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or EnhancedLogger("ui_experience_manager")
        self.async_controller = get_async_controller()
        
        # UI状态管理
        self._ui_states: Dict[str, UIState] = {}
        
        # 支持的报表类型
        self._report_types = {
            'supplier-reconciliation': '供应商对账表',
            'customer-reconciliation': '客户对账单',
            'inventory-report': '库存报表',
            'sales-report': '销售报表',
            'purchase-report': '采购报表'
        }
        
        self.logger.info("前端用户体验管理器初始化完成")
    
    def start_async_report_generation(self, 
                                    session_id: str,
                                    report_type: str, 
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """
        启动异步报表生成
        
        Args:
            session_id: 会话ID
            report_type: 报表类型
            params: 查询参数
            
        Returns:
            启动结果
        """
        try:
            self.logger.info(f"启动异步报表生成: {report_type}, 会话: {session_id}")
            
            # 检查报表类型是否支持
            if report_type not in self._report_types:
                raise ValueError(f"不支持的报表类型: {report_type}")
            
            # 启动异步任务
            task_id = self.async_controller.start_report_generation(
                view_name=report_type.replace('-', '_'),
                params=params
            )
            
            # 初始化UI状态
            self._ui_states[session_id] = UIState(
                is_loading=True,
                progress=0.0,
                message=f"正在生成{self._report_types[report_type]}..."
            )
            
            self.logger.info(f"异步报表任务已启动: {task_id}")
            
            return {
                'success': True,
                'task_id': task_id,
                'report_type': report_type,
                'message': f'{self._report_types[report_type]}生成任务已启动'
            }
            
        except Exception as e:
            self.logger.error(f"启动异步报表生成失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'启动{self._report_types.get(report_type, "报表")}生成失败'
            }
    
    def get_report_progress(self, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        获取报表生成进度
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            进度信息
        """
        try:
            # 从异步控制器获取进度
            progress_info = self.async_controller.get_report_progress(task_id)
            
            # 更新UI状态
            if session_id in self._ui_states:
                ui_state = self._ui_states[session_id]
                ui_state.progress = progress_info.get('progress', 0.0)
                ui_state.last_updated = datetime.now()
                
                # 根据状态更新消息
                status = progress_info.get('status', 'unknown')
                if status == 'running':
                    ui_state.message = "正在处理数据..."
                elif status == 'completed':
                    ui_state.message = "报表生成完成"
                    ui_state.is_loading = False
                elif status == 'failed':
                    ui_state.message = "报表生成失败"
                    ui_state.error_message = progress_info.get('error_message')
                    ui_state.is_loading = False
            
            return {
                'success': True,
                'task_id': task_id,
                'status': progress_info.get('status'),
                'progress': progress_info.get('progress', 0.0),
                'message': progress_info.get('error_message') if progress_info.get('status') == 'failed' else None,
                'duration': progress_info.get('running_seconds', 0)
            }
            
        except Exception as e:
            self.logger.error(f"获取报表进度失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'task_id': task_id,
                'status': 'failed'
            }
    
    def get_report_result(self, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        获取报表结果
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            报表结果
        """
        try:
            # 从异步控制器获取结果
            result = self.async_controller.get_report_result(task_id)
            
            # 清理UI状态
            if session_id in self._ui_states:
                del self._ui_states[session_id]
            
            if result is not None:
                self.logger.info(f"报表结果获取成功: {task_id}, 数据量: {len(result)}")
                return {
                    'success': True,
                    'task_id': task_id,
                    'data': result,
                    'record_count': len(result)
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': '报表尚未完成或已失败',
                    'data': []
                }
                
        except Exception as e:
            self.logger.error(f"获取报表结果失败: {str(e)}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'data': []
            }
    
    def cancel_report_generation(self, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        取消报表生成
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            取消结果
        """
        try:
            # 取消异步任务
            success = self.async_controller.cancel_report_generation(task_id)
            
            # 清理UI状态
            if session_id in self._ui_states:
                del self._ui_states[session_id]
            
            if success:
                self.logger.info(f"报表生成已取消: {task_id}")
                return {
                    'success': True,
                    'task_id': task_id,
                    'message': '报表生成已取消'
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': '取消失败，任务可能已完成或不存在'
                }
                
        except Exception as e:
            self.logger.error(f"取消报表生成失败: {str(e)}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    def show_loading_state(self, session_id: str, message: str = "正在加载数据...") -> Dict[str, Any]:
        """
        显示加载状态
        
        Args:
            session_id: 会话ID
            message: 加载消息
            
        Returns:
            状态信息
        """
        self._ui_states[session_id] = UIState(
            is_loading=True,
            progress=0.0,
            message=message
        )
        
        return {
            'session_id': session_id,
            'is_loading': True,
            'message': message,
            'progress': 0.0
        }
    
    def update_progress(self, session_id: str, progress: float, message: str = "") -> Dict[str, Any]:
        """
        更新进度
        
        Args:
            session_id: 会话ID
            progress: 进度值 (0.0-1.0)
            message: 进度消息
            
        Returns:
            更新结果
        """
        if session_id in self._ui_states:
            ui_state = self._ui_states[session_id]
            ui_state.progress = max(0.0, min(1.0, progress))
            ui_state.last_updated = datetime.now()
            
            if message:
                ui_state.message = message
            
            return {
                'session_id': session_id,
                'progress': ui_state.progress,
                'message': ui_state.message,
                'updated': True
            }
        else:
            return {
                'session_id': session_id,
                'error': '会话不存在',
                'updated': False
            }
    
    def show_error_with_retry(self, 
                            session_id: str,
                            error_message: str, 
                            retry_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        显示错误信息和重试选项
        
        Args:
            session_id: 会话ID
            error_message: 错误消息
            retry_callback: 重试回调函数
            
        Returns:
            错误状态信息
        """
        if session_id in self._ui_states:
            ui_state = self._ui_states[session_id]
            ui_state.is_loading = False
            ui_state.error_message = error_message
            ui_state.last_updated = datetime.now()
        else:
            self._ui_states[session_id] = UIState(
                is_loading=False,
                error_message=error_message
            )
        
        return {
            'session_id': session_id,
            'is_loading': False,
            'error_message': error_message,
            'has_retry': retry_callback is not None,
            'timestamp': datetime.now().isoformat()
        }
    
    def hide_loading_state(self, session_id: str) -> Dict[str, Any]:
        """
        隐藏加载状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            状态信息
        """
        if session_id in self._ui_states:
            ui_state = self._ui_states[session_id]
            ui_state.is_loading = False
            ui_state.last_updated = datetime.now()
            
            return {
                'session_id': session_id,
                'is_loading': False,
                'hidden': True
            }
        else:
            return {
                'session_id': session_id,
                'error': '会话不存在',
                'hidden': False
            }
    
    def is_interface_responsive(self, session_id: str) -> bool:
        """
        检查界面是否响应
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否响应
        """
        if session_id not in self._ui_states:
            return True
        
        ui_state = self._ui_states[session_id]
        
        # 如果没有在加载状态，认为是响应的
        if not ui_state.is_loading:
            return True
        
        # 检查最后更新时间，如果超过30秒没有更新，可能有问题
        time_diff = (datetime.now() - ui_state.last_updated).total_seconds()
        return time_diff < 30
    
    def get_ui_state(self, session_id: str) -> Dict[str, Any]:
        """
        获取UI状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            UI状态信息
        """
        if session_id in self._ui_states:
            ui_state = self._ui_states[session_id]
            return {
                'session_id': session_id,
                'is_loading': ui_state.is_loading,
                'progress': ui_state.progress,
                'message': ui_state.message,
                'error_message': ui_state.error_message,
                'last_updated': ui_state.last_updated.isoformat(),
                'is_responsive': self.is_interface_responsive(session_id)
            }
        else:
            return {
                'session_id': session_id,
                'is_loading': False,
                'progress': 0.0,
                'message': '',
                'error_message': None,
                'exists': False
            }
    
    def cleanup_expired_sessions(self, max_age_hours: int = 1) -> int:
        """
        清理过期的会话状态
        
        Args:
            max_age_hours: 最大保留时间（小时）
            
        Returns:
            清理的会话数量
        """
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, ui_state in self._ui_states.items():
                time_diff = (current_time - ui_state.last_updated).total_seconds()
                if time_diff > max_age_hours * 3600:
                    expired_sessions.append(session_id)
            
            # 删除过期会话
            for session_id in expired_sessions:
                del self._ui_states[session_id]
            
            if expired_sessions:
                self.logger.info(f"清理过期UI会话: {len(expired_sessions)} 个")
            
            return len(expired_sessions)
            
        except Exception as e:
            self.logger.error(f"清理过期会话失败: {str(e)}")
            return 0
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        获取管理器统计信息
        
        Returns:
            统计信息
        """
        active_sessions = len(self._ui_states)
        loading_sessions = sum(1 for state in self._ui_states.values() if state.is_loading)
        error_sessions = sum(1 for state in self._ui_states.values() if state.error_message)
        
        return {
            'active_sessions': active_sessions,
            'loading_sessions': loading_sessions,
            'error_sessions': error_sessions,
            'supported_report_types': len(self._report_types),
            'report_types': list(self._report_types.keys())
        }


def main():
    """测试前端用户体验管理器功能"""
    logger = EnhancedLogger("ui_experience_manager_test")
    
    try:
        print("=== 前端用户体验管理器测试 ===")
        
        # 创建用户体验管理器
        ui_manager = UIExperienceManager(logger)
        
        # 测试启动异步报表生成
        print("\n1. 测试启动异步报表生成")
        session_id = "test_session_001"
        result = ui_manager.start_async_report_generation(
            session_id=session_id,
            report_type='supplier-reconciliation',
            params={'start_date': '2024-01-01', 'end_date': '2024-12-31'}
        )
        print(f"启动结果: {result}")
        
        if result['success']:
            task_id = result['task_id']
            
            # 测试进度查询
            print("\n2. 测试进度查询")
            time.sleep(2)  # 等待任务开始执行
            
            progress_result = ui_manager.get_report_progress(session_id, task_id)
            print(f"进度结果: {progress_result}")
            
            # 测试UI状态
            print("\n3. 测试UI状态")
            ui_state = ui_manager.get_ui_state(session_id)
            print(f"UI状态: {ui_state}")
            
            # 等待任务完成或超时
            print("\n4. 等待任务完成")
            max_wait = 30
            wait_count = 0
            
            while wait_count < max_wait:
                progress_result = ui_manager.get_report_progress(session_id, task_id)
                status = progress_result.get('status')
                
                print(f"任务状态: {status}, 进度: {progress_result.get('progress', 0)*100:.1f}%")
                
                if status in ['completed', 'failed']:
                    break
                
                time.sleep(1)
                wait_count += 1
            
            # 测试获取结果
            print("\n5. 测试获取结果")
            if status == 'completed':
                result_data = ui_manager.get_report_result(session_id, task_id)
                print(f"结果数据: 成功={result_data['success']}, 记录数={result_data.get('record_count', 0)}")
            else:
                print("任务未完成或失败")
        
        # 测试管理器统计
        print("\n6. 测试管理器统计")
        stats = ui_manager.get_manager_stats()
        print(f"管理器统计: {stats}")
        
        print("\n前端用户体验管理器测试完成！")
        
    except Exception as e:
        logger.error(f"前端用户体验管理器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()