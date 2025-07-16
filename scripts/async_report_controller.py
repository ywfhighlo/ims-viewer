#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步报表生成控制器
支持非阻塞任务执行、任务状态跟踪和进度反馈机制
"""

import sys
import os
import uuid
import threading
import time
import queue
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.query_optimizer import QueryOptimizer
from scripts.cache_manager import cache_report_data


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReportTask:
    """报表任务数据模型"""
    task_id: str
    view_name: str
    params: Dict[str, Any]
    status: TaskStatus
    progress: float  # 0.0 - 1.0
    result: Optional[List[Dict]] = None
    error_message: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        # 处理枚举和datetime对象的序列化
        result['status'] = self.status.value
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        if self.started_at:
            result['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            result['completed_at'] = self.completed_at.isoformat()
        return result
    
    def update_progress(self, progress: float, message: Optional[str] = None):
        """更新任务进度"""
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.now()
        if message and hasattr(self, 'progress_message'):
            self.progress_message = message


class AsyncReportController:
    """异步报表生成控制器"""
    
    def __init__(self, 
                 max_workers: int = 4,
                 max_queue_size: int = 100,
                 task_timeout: int = 300,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化异步报表控制器
        
        Args:
            max_workers: 最大工作线程数
            max_queue_size: 最大队列大小
            task_timeout: 任务超时时间（秒）
            logger: 日志记录器
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_timeout = task_timeout
        self.logger = logger or EnhancedLogger("async_report_controller")
        
        # 任务存储
        self._tasks: Dict[str, ReportTask] = {}
        self._tasks_lock = threading.RLock()
        
        # 线程池执行器
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ReportWorker"
        )
        
        # 任务队列
        self._task_queue = queue.Queue(maxsize=max_queue_size)
        
        # 支持的报表类型
        self._report_generators = {
            'supplier_reconciliation': self._generate_supplier_reconciliation,
            'customer_reconciliation': self._generate_customer_reconciliation,
            'inventory_report': self._generate_inventory_report,
            'sales_report': self._generate_sales_report,
            'purchase_report': self._generate_purchase_report
        }
        
        # 启动任务清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_tasks, daemon=True)
        self._cleanup_thread.start()
        
        self.logger.info(f"异步报表控制器初始化完成，最大工作线程数: {max_workers}, 任务超时: {task_timeout}秒")
    
    def start_report_generation(self, view_name: str, params: Dict[str, Any]) -> str:
        """
        启动报表生成任务
        
        Args:
            view_name: 视图名称
            params: 查询参数
            
        Returns:
            任务ID
        """
        try:
            # 检查是否支持该报表类型
            if view_name not in self._report_generators:
                raise ValueError(f"不支持的报表类型: {view_name}")
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建任务对象
            task = ReportTask(
                task_id=task_id,
                view_name=view_name,
                params=params.copy(),
                status=TaskStatus.PENDING,
                progress=0.0
            )
            
            # 存储任务
            with self._tasks_lock:
                self._tasks[task_id] = task
            
            # 提交任务到线程池
            future = self._executor.submit(self._execute_report_task, task_id)
            
            self.logger.info(f"报表生成任务已启动: {task_id}, 视图: {view_name}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"启动报表生成任务失败: {view_name}, 错误: {str(e)}")
            raise
    
    def get_report_progress(self, task_id: str) -> Dict[str, Any]:
        """
        获取报表生成进度
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务进度信息
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            
            progress_info = {
                'task_id': task_id,
                'status': task.status.value,
                'progress': task.progress,
                'view_name': task.view_name,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'error_message': task.error_message
            }
            
            # 计算执行时间
            if task.started_at:
                progress_info['started_at'] = task.started_at.isoformat()
                if task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    progress_info['duration_seconds'] = duration
                else:
                    duration = (datetime.now() - task.started_at).total_seconds()
                    progress_info['running_seconds'] = duration
            
            return progress_info
    
    def get_report_result(self, task_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取报表生成结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            报表数据，如果任务未完成则返回None
        """
        with self._tasks_lock:
            task = self._tasks.get(task_id)
            
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            
            if task.status == TaskStatus.COMPLETED:
                return task.result.copy() if task.result else []
            elif task.status == TaskStatus.FAILED:
                raise RuntimeError(f"任务执行失败: {task.error_message}")
            else:
                return None
    
    def cancel_report_generation(self, task_id: str) -> bool:
        """
        取消报表生成任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        try:
            with self._tasks_lock:
                task = self._tasks.get(task_id)
                
                if not task:
                    return False
                
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    return False
                
                # 标记任务为已取消
                task.status = TaskStatus.CANCELLED
                task.updated_at = datetime.now()
                task.error_message = "任务已被用户取消"
                
                self.logger.info(f"任务已取消: {task_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
            return False
    
    def get_task_list(self, status_filter: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取任务列表
        
        Args:
            status_filter: 状态过滤器
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        with self._tasks_lock:
            tasks = list(self._tasks.values())
            
            # 状态过滤
            if status_filter:
                tasks = [task for task in tasks if task.status.value == status_filter]
            
            # 按创建时间倒序排序
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            
            # 限制数量
            tasks = tasks[:limit]
            
            return [task.to_dict() for task in tasks]
    
    def get_controller_stats(self) -> Dict[str, Any]:
        """
        获取控制器统计信息
        
        Returns:
            统计信息字典
        """
        with self._tasks_lock:
            total_tasks = len(self._tasks)
            status_counts = {}
            
            for task in self._tasks.values():
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_tasks': total_tasks,
                'status_counts': status_counts,
                'max_workers': self.max_workers,
                'max_queue_size': self.max_queue_size,
                'task_timeout': self.task_timeout,
                'active_threads': threading.active_count()
            }
    
    def _execute_report_task(self, task_id: str):
        """
        执行报表生成任务
        
        Args:
            task_id: 任务ID
        """
        task = None
        try:
            with self._tasks_lock:
                task = self._tasks.get(task_id)
                
                if not task or task.status == TaskStatus.CANCELLED:
                    return
                
                # 更新任务状态
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                task.progress = 0.1
                task.updated_at = datetime.now()
            
            self.logger.info(f"开始执行报表任务: {task_id}, 视图: {task.view_name}")
            
            # 获取报表生成器
            generator = self._report_generators.get(task.view_name)
            if not generator:
                raise ValueError(f"未找到报表生成器: {task.view_name}")
            
            # 更新进度
            task.progress = 0.2
            task.updated_at = datetime.now()
            
            # 执行报表生成
            result = generator(task.params, task)
            
            # 检查任务是否被取消
            if task.status == TaskStatus.CANCELLED:
                return
            
            # 更新任务完成状态
            with self._tasks_lock:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 1.0
                task.completed_at = datetime.now()
                task.updated_at = datetime.now()
            
            self.logger.info(f"报表任务执行完成: {task_id}, 数据量: {len(result) if result else 0}")
            
        except Exception as e:
            self.logger.error(f"报表任务执行失败: {task_id}, 错误: {str(e)}")
            
            if task:
                with self._tasks_lock:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.completed_at = datetime.now()
                    task.updated_at = datetime.now()
    
    def _generate_supplier_reconciliation(self, params: Dict[str, Any], task: ReportTask) -> List[Dict[str, Any]]:
        """生成供应商对账表"""
        task.progress = 0.3
        task.updated_at = datetime.now()
        
        optimizer = QueryOptimizer(self.logger)
        
        task.progress = 0.5
        task.updated_at = datetime.now()
        
        result = optimizer.optimize_supplier_reconciliation_query(params)
        
        task.progress = 0.9
        task.updated_at = datetime.now()
        
        return result
    
    def _generate_customer_reconciliation(self, params: Dict[str, Any], task: ReportTask) -> List[Dict[str, Any]]:
        """生成客户对账单"""
        task.progress = 0.3
        task.updated_at = datetime.now()
        
        optimizer = QueryOptimizer(self.logger)
        
        task.progress = 0.5
        task.updated_at = datetime.now()
        
        result = optimizer.optimize_customer_reconciliation_query(params)
        
        task.progress = 0.9
        task.updated_at = datetime.now()
        
        return result
    
    def _generate_inventory_report(self, params: Dict[str, Any], task: ReportTask) -> List[Dict[str, Any]]:
        """生成库存报表"""
        task.progress = 0.3
        task.updated_at = datetime.now()
        
        optimizer = QueryOptimizer(self.logger)
        
        task.progress = 0.5
        task.updated_at = datetime.now()
        
        result = optimizer.optimize_inventory_report_query(params)
        
        task.progress = 0.9
        task.updated_at = datetime.now()
        
        return result
    
    def _generate_sales_report(self, params: Dict[str, Any], task: ReportTask) -> List[Dict[str, Any]]:
        """生成销售报表"""
        task.progress = 0.3
        task.updated_at = datetime.now()
        
        optimizer = QueryOptimizer(self.logger)
        
        task.progress = 0.5
        task.updated_at = datetime.now()
        
        result = optimizer.optimize_sales_report_query(params)
        
        task.progress = 0.9
        task.updated_at = datetime.now()
        
        return result
    
    def _generate_purchase_report(self, params: Dict[str, Any], task: ReportTask) -> List[Dict[str, Any]]:
        """生成采购报表"""
        task.progress = 0.3
        task.updated_at = datetime.now()
        
        optimizer = QueryOptimizer(self.logger)
        
        task.progress = 0.5
        task.updated_at = datetime.now()
        
        result = optimizer.optimize_purchase_report_query(params)
        
        task.progress = 0.9
        task.updated_at = datetime.now()
        
        return result
    
    def _cleanup_expired_tasks(self):
        """清理过期任务的后台线程"""
        while True:
            try:
                time.sleep(60)  # 每分钟清理一次
                
                current_time = datetime.now()
                expired_tasks = []
                
                with self._tasks_lock:
                    for task_id, task in self._tasks.items():
                        # 清理超过1小时的已完成任务
                        if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                            (current_time - task.updated_at).total_seconds() > 3600):
                            expired_tasks.append(task_id)
                        
                        # 清理超时的运行中任务
                        elif (task.status == TaskStatus.RUNNING and
                              task.started_at and
                              (current_time - task.started_at).total_seconds() > self.task_timeout):
                            task.status = TaskStatus.FAILED
                            task.error_message = "任务执行超时"
                            task.completed_at = current_time
                            task.updated_at = current_time
                            expired_tasks.append(task_id)
                    
                    # 删除过期任务
                    for task_id in expired_tasks:
                        del self._tasks[task_id]
                
                if expired_tasks:
                    self.logger.info(f"清理过期任务: {len(expired_tasks)} 个")
                    
            except Exception as e:
                self.logger.error(f"清理过期任务失败: {str(e)}")
    
    def shutdown(self):
        """关闭异步报表控制器"""
        try:
            self.logger.info("正在关闭异步报表控制器...")
            
            # 关闭线程池
            self._executor.shutdown(wait=True)
            
            self.logger.info("异步报表控制器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭异步报表控制器失败: {str(e)}")


# 全局异步报表控制器实例
_global_async_controller: Optional[AsyncReportController] = None
_controller_lock = threading.Lock()


def get_async_controller() -> AsyncReportController:
    """
    获取全局异步报表控制器实例（单例模式）
    
    Returns:
        异步报表控制器实例
    """
    global _global_async_controller
    
    if _global_async_controller is None:
        with _controller_lock:
            if _global_async_controller is None:
                _global_async_controller = AsyncReportController()
    
    return _global_async_controller


def main():
    """测试异步报表控制器功能"""
    logger = EnhancedLogger("async_report_controller_test")
    
    try:
        print("=== 异步报表控制器测试 ===")
        
        # 创建异步报表控制器
        controller = AsyncReportController(max_workers=2, logger=logger)
        
        # 测试启动报表生成任务
        print("\n1. 测试启动报表生成任务")
        task_id1 = controller.start_report_generation('supplier_reconciliation', {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        })
        print(f"任务1已启动: {task_id1}")
        
        task_id2 = controller.start_report_generation('customer_reconciliation', {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        })
        print(f"任务2已启动: {task_id2}")
        
        # 测试获取任务进度
        print("\n2. 测试获取任务进度")
        time.sleep(1)  # 等待任务开始执行
        
        progress1 = controller.get_report_progress(task_id1)
        print(f"任务1进度: {progress1['status']} - {progress1['progress']*100:.1f}%")
        
        progress2 = controller.get_report_progress(task_id2)
        print(f"任务2进度: {progress2['status']} - {progress2['progress']*100:.1f}%")
        
        # 等待任务完成
        print("\n3. 等待任务完成")
        max_wait = 30  # 最多等待30秒
        wait_count = 0
        
        while wait_count < max_wait:
            progress1 = controller.get_report_progress(task_id1)
            progress2 = controller.get_report_progress(task_id2)
            
            print(f"任务1: {progress1['status']} - {progress1['progress']*100:.1f}%")
            print(f"任务2: {progress2['status']} - {progress2['progress']*100:.1f}%")
            
            if (progress1['status'] in ['completed', 'failed'] and 
                progress2['status'] in ['completed', 'failed']):
                break
            
            time.sleep(1)
            wait_count += 1
        
        # 测试获取任务结果
        print("\n4. 测试获取任务结果")
        try:
            result1 = controller.get_report_result(task_id1)
            print(f"任务1结果: {len(result1) if result1 else 0} 条数据")
        except Exception as e:
            print(f"任务1结果获取失败: {str(e)}")
        
        try:
            result2 = controller.get_report_result(task_id2)
            print(f"任务2结果: {len(result2) if result2 else 0} 条数据")
        except Exception as e:
            print(f"任务2结果获取失败: {str(e)}")
        
        # 测试获取任务列表
        print("\n5. 测试获取任务列表")
        task_list = controller.get_task_list()
        print(f"任务列表: {len(task_list)} 个任务")
        
        # 测试获取控制器统计
        print("\n6. 测试获取控制器统计")
        stats = controller.get_controller_stats()
        print(f"控制器统计: {stats}")
        
        # 关闭控制器
        controller.shutdown()
        
        print("\n异步报表控制器测试完成！")
        
    except Exception as e:
        logger.error(f"异步报表控制器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()