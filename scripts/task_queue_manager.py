#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列管理器
支持任务优先级、批量处理和负载均衡
"""

import sys
import os
import heapq
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.async_report_controller import AsyncReportController, TaskStatus


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class QueuedTask:
    """队列任务数据模型"""
    task_id: str
    view_name: str
    params: Dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """支持优先级队列排序"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class TaskQueueManager:
    """任务队列管理器"""
    
    def __init__(self, 
                 max_concurrent_tasks: int = 5,
                 max_queue_size: int = 1000,
                 retry_delay: int = 60,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化任务队列管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数
            max_queue_size: 最大队列大小
            retry_delay: 重试延迟（秒）
            logger: 日志记录器
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size
        self.retry_delay = retry_delay
        self.logger = logger or EnhancedLogger("task_queue_manager")
        
        # 任务队列（优先级队列）
        self._task_queue: List[QueuedTask] = []
        self._queue_lock = threading.RLock()
        
        # 延迟任务队列
        self._delayed_tasks: List[QueuedTask] = []
        self._delayed_lock = threading.RLock()
        
        # 正在执行的任务
        self._running_tasks: Dict[str, QueuedTask] = {}
        self._running_lock = threading.RLock()
        
        # 失败任务队列
        self._failed_tasks: List[QueuedTask] = []
        self._failed_lock = threading.RLock()
        
        # 异步报表控制器
        self._async_controller = AsyncReportController(
            max_workers=max_concurrent_tasks,
            logger=logger
        )
        
        # 队列处理线程
        self._queue_processor_running = True
        self._queue_processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._queue_processor_thread.start()
        
        # 延迟任务处理线程
        self._delayed_processor_thread = threading.Thread(target=self._process_delayed_tasks, daemon=True)
        self._delayed_processor_thread.start()
        
        self.logger.info(f"任务队列管理器初始化完成，最大并发任务数: {max_concurrent_tasks}")
    
    def enqueue_task(self, 
                    view_name: str, 
                    params: Dict[str, Any],
                    priority: TaskPriority = TaskPriority.NORMAL,
                    scheduled_at: Optional[datetime] = None,
                    callback: Optional[Callable] = None) -> str:
        """
        将任务加入队列
        
        Args:
            view_name: 视图名称
            params: 查询参数
            priority: 任务优先级
            scheduled_at: 计划执行时间
            callback: 完成回调函数
            
        Returns:
            任务ID
        """
        try:
            task_id = str(uuid.uuid4())
            
            queued_task = QueuedTask(
                task_id=task_id,
                view_name=view_name,
                params=params.copy(),
                priority=priority,
                created_at=datetime.now(),
                scheduled_at=scheduled_at,
                callback=callback
            )
            
            if scheduled_at and scheduled_at > datetime.now():
                # 延迟任务
                with self._delayed_lock:
                    if len(self._delayed_tasks) >= self.max_queue_size:
                        raise RuntimeError("延迟任务队列已满")
                    
                    heapq.heappush(self._delayed_tasks, queued_task)
                
                self.logger.info(f"延迟任务已加入队列: {task_id}, 计划执行时间: {scheduled_at}")
            else:
                # 立即执行任务
                with self._queue_lock:
                    if len(self._task_queue) >= self.max_queue_size:
                        raise RuntimeError("任务队列已满")
                    
                    heapq.heappush(self._task_queue, queued_task)
                
                self.logger.info(f"任务已加入队列: {task_id}, 优先级: {priority.name}")
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"任务入队失败: {view_name}, 错误: {str(e)}")
            raise
    
    def enqueue_batch_tasks(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        批量将任务加入队列
        
        Args:
            tasks: 任务列表，每个任务包含view_name, params等信息
            
        Returns:
            任务ID列表
        """
        task_ids = []
        
        try:
            for task_info in tasks:
                view_name = task_info['view_name']
                params = task_info['params']
                priority = TaskPriority(task_info.get('priority', TaskPriority.NORMAL.value))
                scheduled_at = task_info.get('scheduled_at')
                
                task_id = self.enqueue_task(view_name, params, priority, scheduled_at)
                task_ids.append(task_id)
            
            self.logger.info(f"批量任务入队完成: {len(task_ids)} 个任务")
            return task_ids
            
        except Exception as e:
            self.logger.error(f"批量任务入队失败: {str(e)}")
            raise
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            队列状态信息
        """
        with self._queue_lock, self._delayed_lock, self._running_lock, self._failed_lock:
            return {
                'pending_tasks': len(self._task_queue),
                'delayed_tasks': len(self._delayed_tasks),
                'running_tasks': len(self._running_tasks),
                'failed_tasks': len(self._failed_tasks),
                'max_concurrent_tasks': self.max_concurrent_tasks,
                'max_queue_size': self.max_queue_size,
                'queue_utilization': len(self._task_queue) / self.max_queue_size * 100,
                'concurrent_utilization': len(self._running_tasks) / self.max_concurrent_tasks * 100
            }
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        # 检查正在运行的任务
        with self._running_lock:
            if task_id in self._running_tasks:
                queued_task = self._running_tasks[task_id]
                progress = self._async_controller.get_report_progress(task_id)
                return {
                    'task_id': task_id,
                    'view_name': queued_task.view_name,
                    'priority': queued_task.priority.name,
                    'status': 'running',
                    'progress': progress.get('progress', 0.0),
                    'created_at': queued_task.created_at.isoformat(),
                    'retry_count': queued_task.retry_count
                }
        
        # 检查队列中的任务
        with self._queue_lock:
            for task in self._task_queue:
                if task.task_id == task_id:
                    return {
                        'task_id': task_id,
                        'view_name': task.view_name,
                        'priority': task.priority.name,
                        'status': 'pending',
                        'created_at': task.created_at.isoformat(),
                        'retry_count': task.retry_count
                    }
        
        # 检查延迟任务
        with self._delayed_lock:
            for task in self._delayed_tasks:
                if task.task_id == task_id:
                    return {
                        'task_id': task_id,
                        'view_name': task.view_name,
                        'priority': task.priority.name,
                        'status': 'scheduled',
                        'created_at': task.created_at.isoformat(),
                        'scheduled_at': task.scheduled_at.isoformat() if task.scheduled_at else None,
                        'retry_count': task.retry_count
                    }
        
        # 检查失败任务
        with self._failed_lock:
            for task in self._failed_tasks:
                if task.task_id == task_id:
                    return {
                        'task_id': task_id,
                        'view_name': task.view_name,
                        'priority': task.priority.name,
                        'status': 'failed',
                        'created_at': task.created_at.isoformat(),
                        'retry_count': task.retry_count
                    }
        
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        try:
            # 尝试取消正在运行的任务
            with self._running_lock:
                if task_id in self._running_tasks:
                    success = self._async_controller.cancel_report_generation(task_id)
                    if success:
                        del self._running_tasks[task_id]
                        self.logger.info(f"正在运行的任务已取消: {task_id}")
                        return True
            
            # 尝试从队列中移除任务
            with self._queue_lock:
                for i, task in enumerate(self._task_queue):
                    if task.task_id == task_id:
                        del self._task_queue[i]
                        heapq.heapify(self._task_queue)
                        self.logger.info(f"队列中的任务已取消: {task_id}")
                        return True
            
            # 尝试从延迟队列中移除任务
            with self._delayed_lock:
                for i, task in enumerate(self._delayed_tasks):
                    if task.task_id == task_id:
                        del self._delayed_tasks[i]
                        heapq.heapify(self._delayed_tasks)
                        self.logger.info(f"延迟队列中的任务已取消: {task_id}")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"取消任务失败: {task_id}, 错误: {str(e)}")
            return False
    
    def retry_failed_task(self, task_id: str) -> bool:
        """
        重试失败的任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功重试
        """
        try:
            with self._failed_lock:
                for i, task in enumerate(self._failed_tasks):
                    if task.task_id == task_id:
                        if task.retry_count >= task.max_retries:
                            self.logger.warning(f"任务已达到最大重试次数: {task_id}")
                            return False
                        
                        # 移除失败任务并重新入队
                        failed_task = self._failed_tasks.pop(i)
                        failed_task.retry_count += 1
                        
                        with self._queue_lock:
                            heapq.heappush(self._task_queue, failed_task)
                        
                        self.logger.info(f"失败任务已重新入队: {task_id}, 重试次数: {failed_task.retry_count}")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"重试失败任务失败: {task_id}, 错误: {str(e)}")
            return False
    
    def _process_queue(self):
        """队列处理线程函数"""
        while self._queue_processor_running:
            try:
                # 检查是否有可用的执行槽位
                with self._running_lock:
                    if len(self._running_tasks) >= self.max_concurrent_tasks:
                        time.sleep(1)
                        continue
                
                # 从队列中获取任务
                task = None
                with self._queue_lock:
                    if self._task_queue:
                        task = heapq.heappop(self._task_queue)
                
                if task:
                    # 启动任务执行
                    try:
                        async_task_id = self._async_controller.start_report_generation(
                            task.view_name, task.params
                        )
                        
                        # 将任务移到运行中列表
                        with self._running_lock:
                            self._running_tasks[async_task_id] = task
                        
                        # 启动任务监控
                        monitor_thread = threading.Thread(
                            target=self._monitor_task,
                            args=(async_task_id, task),
                            daemon=True
                        )
                        monitor_thread.start()
                        
                        self.logger.info(f"任务开始执行: {task.task_id} -> {async_task_id}")
                        
                    except Exception as e:
                        self.logger.error(f"启动任务执行失败: {task.task_id}, 错误: {str(e)}")
                        
                        # 将任务移到失败列表
                        with self._failed_lock:
                            self._failed_tasks.append(task)
                else:
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"队列处理失败: {str(e)}")
                time.sleep(1)
    
    def _process_delayed_tasks(self):
        """延迟任务处理线程函数"""
        while self._queue_processor_running:
            try:
                current_time = datetime.now()
                tasks_to_move = []
                
                with self._delayed_lock:
                    while (self._delayed_tasks and 
                           self._delayed_tasks[0].scheduled_at and
                           self._delayed_tasks[0].scheduled_at <= current_time):
                        task = heapq.heappop(self._delayed_tasks)
                        tasks_to_move.append(task)
                
                # 将到期的延迟任务移到主队列
                if tasks_to_move:
                    with self._queue_lock:
                        for task in tasks_to_move:
                            heapq.heappush(self._task_queue, task)
                    
                    self.logger.info(f"延迟任务已移到主队列: {len(tasks_to_move)} 个任务")
                
                time.sleep(10)  # 每10秒检查一次延迟任务
                
            except Exception as e:
                self.logger.error(f"延迟任务处理失败: {str(e)}")
                time.sleep(10)
    
    def _monitor_task(self, async_task_id: str, queued_task: QueuedTask):
        """监控任务执行"""
        try:
            while True:
                progress = self._async_controller.get_report_progress(async_task_id)
                status = progress.get('status')
                
                if status in ['completed', 'failed', 'cancelled']:
                    # 任务完成，从运行中列表移除
                    with self._running_lock:
                        if async_task_id in self._running_tasks:
                            del self._running_tasks[async_task_id]
                    
                    if status == 'completed':
                        self.logger.info(f"任务执行完成: {queued_task.task_id}")
                        
                        # 执行回调函数
                        if queued_task.callback:
                            try:
                                result = self._async_controller.get_report_result(async_task_id)
                                queued_task.callback(queued_task.task_id, result)
                            except Exception as e:
                                self.logger.error(f"任务回调执行失败: {queued_task.task_id}, 错误: {str(e)}")
                    
                    elif status == 'failed':
                        self.logger.error(f"任务执行失败: {queued_task.task_id}")
                        
                        # 检查是否需要重试
                        if queued_task.retry_count < queued_task.max_retries:
                            # 延迟重试
                            queued_task.retry_count += 1
                            queued_task.scheduled_at = datetime.now() + timedelta(seconds=self.retry_delay)
                            
                            with self._delayed_lock:
                                heapq.heappush(self._delayed_tasks, queued_task)
                            
                            self.logger.info(f"任务将延迟重试: {queued_task.task_id}, 重试次数: {queued_task.retry_count}")
                        else:
                            # 移到失败列表
                            with self._failed_lock:
                                self._failed_tasks.append(queued_task)
                            
                            self.logger.error(f"任务重试次数已达上限: {queued_task.task_id}")
                    
                    break
                
                time.sleep(2)  # 每2秒检查一次任务状态
                
        except Exception as e:
            self.logger.error(f"任务监控失败: {async_task_id}, 错误: {str(e)}")
    
    def shutdown(self):
        """关闭任务队列管理器"""
        try:
            self.logger.info("正在关闭任务队列管理器...")
            
            # 停止队列处理
            self._queue_processor_running = False
            
            # 等待处理线程结束
            if self._queue_processor_thread.is_alive():
                self._queue_processor_thread.join(timeout=5)
            
            if self._delayed_processor_thread.is_alive():
                self._delayed_processor_thread.join(timeout=5)
            
            # 关闭异步控制器
            self._async_controller.shutdown()
            
            self.logger.info("任务队列管理器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭任务队列管理器失败: {str(e)}")


def main():
    """测试任务队列管理器功能"""
    logger = EnhancedLogger("task_queue_manager_test")
    
    try:
        print("=== 任务队列管理器测试 ===")
        
        # 创建任务队列管理器
        queue_manager = TaskQueueManager(max_concurrent_tasks=2, logger=logger)
        
        # 测试任务入队
        print("\n1. 测试任务入队")
        task_id1 = queue_manager.enqueue_task(
            'supplier_reconciliation',
            {'start_date': '2024-01-01'},
            TaskPriority.HIGH
        )
        print(f"高优先级任务已入队: {task_id1}")
        
        task_id2 = queue_manager.enqueue_task(
            'customer_reconciliation',
            {'start_date': '2024-01-01'},
            TaskPriority.NORMAL
        )
        print(f"普通优先级任务已入队: {task_id2}")
        
        # 测试延迟任务
        print("\n2. 测试延迟任务")
        scheduled_time = datetime.now() + timedelta(seconds=5)
        task_id3 = queue_manager.enqueue_task(
            'inventory_report',
            {'product_name': '测试产品'},
            TaskPriority.LOW,
            scheduled_at=scheduled_time
        )
        print(f"延迟任务已入队: {task_id3}, 计划执行时间: {scheduled_time}")
        
        # 测试队列状态
        print("\n3. 测试队列状态")
        status = queue_manager.get_queue_status()
        print(f"队列状态: {status}")
        
        # 等待任务执行
        print("\n4. 等待任务执行")
        time.sleep(10)
        
        # 检查任务信息
        print("\n5. 检查任务信息")
        for task_id in [task_id1, task_id2, task_id3]:
            info = queue_manager.get_task_info(task_id)
            if info:
                print(f"任务 {task_id}: {info['status']} - {info.get('progress', 0)*100:.1f}%")
        
        # 最终状态
        print("\n6. 最终队列状态")
        final_status = queue_manager.get_queue_status()
        print(f"最终状态: {final_status}")
        
        # 关闭队列管理器
        queue_manager.shutdown()
        
        print("\n任务队列管理器测试完成！")
        
    except Exception as e:
        logger.error(f"任务队列管理器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()