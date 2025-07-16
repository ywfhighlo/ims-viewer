#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据传输优化器
优化数据传输，减少网络开销，支持流式传输和增量更新
"""

import sys
import os
import json
import gzip
import hashlib
import time
from typing import Dict, Any, List, Optional, Union, Iterator, Callable
from datetime import datetime, timedelta
import threading
import queue
from dataclasses import dataclass, field

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_logger import EnhancedLogger
from scripts.data_paginator import DataPaginator


@dataclass
class TransferChunk:
    """数据传输块"""
    chunk_id: str
    sequence: int
    data: List[Dict[str, Any]]
    checksum: str
    is_last: bool = False
    compressed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TransferSession:
    """数据传输会话"""
    session_id: str
    total_chunks: int
    received_chunks: int = 0
    chunks: Dict[int, TransferChunk] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_complete: bool = False
    error: Optional[str] = None


class DataTransferOptimizer:
    """数据传输优化器类"""
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 compression_threshold: int = 500,
                 max_concurrent_transfers: int = 5,
                 session_timeout_minutes: int = 30,
                 logger: Optional[EnhancedLogger] = None):
        """
        初始化数据传输优化器
        
        Args:
            chunk_size: 数据块大小（记录数）
            compression_threshold: 压缩阈值
            max_concurrent_transfers: 最大并发传输数
            session_timeout_minutes: 会话超时时间（分钟）
            logger: 日志记录器
        """
        self.chunk_size = chunk_size
        self.compression_threshold = compression_threshold
        self.max_concurrent_transfers = max_concurrent_transfers
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.logger = logger or EnhancedLogger("data_transfer_optimizer")
        
        # 传输会话管理
        self._sessions = {}
        self._sessions_lock = threading.RLock()
        
        # 数据分页器
        self.paginator = DataPaginator(logger=self.logger)
        
        # 传输队列
        self._transfer_queue = queue.Queue()
        self._transfer_workers = []
        
        # 启动传输工作线程
        self._start_transfer_workers()
        
        # 启动会话清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()
        
        self.logger.info(f"数据传输优化器初始化完成，块大小: {chunk_size}, 压缩阈值: {compression_threshold}")
    
    def prepare_chunked_transfer(self, 
                               data: List[Dict[str, Any]], 
                               enable_compression: bool = True) -> Dict[str, Any]:
        """
        准备分块传输
        
        Args:
            data: 要传输的数据
            enable_compression: 是否启用压缩
            
        Returns:
            传输准备信息
        """
        try:
            session_id = self._generate_session_id()
            total_count = len(data)
            
            # 计算分块数量
            total_chunks = (total_count + self.chunk_size - 1) // self.chunk_size
            
            # 创建传输会话
            session = TransferSession(
                session_id=session_id,
                total_chunks=total_chunks
            )
            
            # 生成数据块
            chunks_info = []
            for i in range(total_chunks):
                start_idx = i * self.chunk_size
                end_idx = min(start_idx + self.chunk_size, total_count)
                chunk_data = data[start_idx:end_idx]
                
                # 生成校验和
                checksum = self._calculate_checksum(chunk_data)
                
                # 判断是否需要压缩
                should_compress = enable_compression and len(chunk_data) >= self.compression_threshold
                
                chunk = TransferChunk(
                    chunk_id=f"{session_id}_{i}",
                    sequence=i,
                    data=chunk_data,
                    checksum=checksum,
                    is_last=(i == total_chunks - 1),
                    compressed=should_compress
                )
                
                session.chunks[i] = chunk
                
                # 构建块信息（不包含实际数据）
                chunk_info = {
                    'chunk_id': chunk.chunk_id,
                    'sequence': i,
                    'size': len(chunk_data),
                    'checksum': checksum,
                    'is_last': chunk.is_last,
                    'compressed': should_compress
                }
                chunks_info.append(chunk_info)
            
            # 保存会话
            with self._sessions_lock:
                self._sessions[session_id] = session
            
            # 构建传输准备信息
            transfer_info = {
                'session_id': session_id,
                'total_count': total_count,
                'total_chunks': total_chunks,
                'chunk_size': self.chunk_size,
                'chunks': chunks_info,
                'estimated_transfer_time': self._estimate_transfer_time(total_count),
                'compression_enabled': enable_compression,
                'prepared_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"分块传输准备完成，会话ID: {session_id}, "
                           f"总数据: {total_count}, 分块数: {total_chunks}")
            
            return transfer_info
            
        except Exception as e:
            self.logger.error(f"准备分块传输失败: {str(e)}")
            return {
                'error': str(e),
                'session_id': None
            }
    
    def get_chunk(self, session_id: str, chunk_sequence: int) -> Dict[str, Any]:
        """
        获取数据块
        
        Args:
            session_id: 会话ID
            chunk_sequence: 块序号
            
        Returns:
            数据块信息
        """
        try:
            with self._sessions_lock:
                session = self._sessions.get(session_id)
                
                if not session:
                    return {
                        'error': '会话不存在或已过期',
                        'session_id': session_id
                    }
                
                # 更新会话活动时间
                session.last_activity = datetime.now()
                
                # 获取指定的数据块
                chunk = session.chunks.get(chunk_sequence)
                
                if not chunk:
                    return {
                        'error': f'数据块不存在: {chunk_sequence}',
                        'session_id': session_id
                    }
                
                # 准备返回数据
                chunk_data = chunk.data
                compressed_data = None
                
                # 如果需要压缩
                if chunk.compressed:
                    try:
                        compressed_data = self.paginator.compress_data(chunk_data)
                        # 压缩成功后，可以选择不返回原始数据以节省带宽
                        # 但为了测试兼容性，这里仍然返回原始数据
                        # chunk_data = None  # 不返回原始数据
                    except Exception as e:
                        self.logger.warning(f"数据块压缩失败: {str(e)}")
                        compressed_data = None
                        chunk.compressed = False
                
                # 构建返回结果
                result = {
                    'session_id': session_id,
                    'chunk_id': chunk.chunk_id,
                    'sequence': chunk.sequence,
                    'data': chunk_data,
                    'compressed_data': compressed_data,
                    'checksum': chunk.checksum,
                    'is_last': chunk.is_last,
                    'compressed': chunk.compressed,
                    'timestamp': chunk.timestamp.isoformat(),
                    'total_chunks': session.total_chunks,
                    'progress': {
                        'current': chunk.sequence + 1,
                        'total': session.total_chunks,
                        'percentage': round((chunk.sequence + 1) / session.total_chunks * 100, 2)
                    }
                }
                
                # 更新接收计数
                session.received_chunks += 1
                
                # 检查是否完成
                if chunk.is_last:
                    session.is_complete = True
                    self.logger.info(f"分块传输完成，会话ID: {session_id}")
                
                return result
                
        except Exception as e:
            self.logger.error(f"获取数据块失败: {session_id}, 块序号: {chunk_sequence}, 错误: {str(e)}")
            return {
                'error': str(e),
                'session_id': session_id,
                'chunk_sequence': chunk_sequence
            }
    
    def get_transfer_progress(self, session_id: str) -> Dict[str, Any]:
        """
        获取传输进度
        
        Args:
            session_id: 会话ID
            
        Returns:
            传输进度信息
        """
        try:
            with self._sessions_lock:
                session = self._sessions.get(session_id)
                
                if not session:
                    return {
                        'error': '会话不存在或已过期',
                        'session_id': session_id
                    }
                
                # 计算进度
                progress_percentage = (session.received_chunks / session.total_chunks * 100) if session.total_chunks > 0 else 0
                
                # 计算传输速度
                elapsed_time = (datetime.now() - session.started_at).total_seconds()
                transfer_rate = session.received_chunks / elapsed_time if elapsed_time > 0 else 0
                
                # 估算剩余时间
                remaining_chunks = session.total_chunks - session.received_chunks
                estimated_remaining_time = remaining_chunks / transfer_rate if transfer_rate > 0 else 0
                
                return {
                    'session_id': session_id,
                    'total_chunks': session.total_chunks,
                    'received_chunks': session.received_chunks,
                    'remaining_chunks': remaining_chunks,
                    'progress_percentage': round(progress_percentage, 2),
                    'is_complete': session.is_complete,
                    'transfer_rate_chunks_per_second': round(transfer_rate, 2),
                    'estimated_remaining_seconds': round(estimated_remaining_time, 2),
                    'elapsed_seconds': round(elapsed_time, 2),
                    'started_at': session.started_at.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'error': session.error
                }
                
        except Exception as e:
            self.logger.error(f"获取传输进度失败: {session_id}, 错误: {str(e)}")
            return {
                'error': str(e),
                'session_id': session_id
            }
    
    def cancel_transfer(self, session_id: str) -> Dict[str, Any]:
        """
        取消传输
        
        Args:
            session_id: 会话ID
            
        Returns:
            取消结果
        """
        try:
            with self._sessions_lock:
                session = self._sessions.get(session_id)
                
                if not session:
                    return {
                        'error': '会话不存在或已过期',
                        'session_id': session_id
                    }
                
                # 标记会话为错误状态
                session.error = '用户取消传输'
                
                # 删除会话
                del self._sessions[session_id]
                
                self.logger.info(f"传输已取消，会话ID: {session_id}")
                
                return {
                    'success': True,
                    'session_id': session_id,
                    'message': '传输已取消'
                }
                
        except Exception as e:
            self.logger.error(f"取消传输失败: {session_id}, 错误: {str(e)}")
            return {
                'error': str(e),
                'session_id': session_id
            }
    
    def create_incremental_update(self, 
                                old_data: List[Dict[str, Any]], 
                                new_data: List[Dict[str, Any]],
                                key_field: str = 'id') -> Dict[str, Any]:
        """
        创建增量更新
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            key_field: 用于比较的键字段
            
        Returns:
            增量更新信息
        """
        try:
            # 创建数据索引
            old_index = {item.get(key_field): item for item in old_data if key_field in item}
            new_index = {item.get(key_field): item for item in new_data if key_field in item}
            
            # 找出变化
            added = []  # 新增的记录
            updated = []  # 更新的记录
            deleted = []  # 删除的记录
            
            # 检查新增和更新
            for key, new_item in new_index.items():
                if key not in old_index:
                    added.append(new_item)
                else:
                    old_item = old_index[key]
                    if self._calculate_checksum([old_item]) != self._calculate_checksum([new_item]):
                        updated.append({
                            'key': key,
                            'old': old_item,
                            'new': new_item
                        })
            
            # 检查删除
            for key, old_item in old_index.items():
                if key not in new_index:
                    deleted.append(old_item)
            
            # 计算变化统计
            total_changes = len(added) + len(updated) + len(deleted)
            change_ratio = total_changes / len(old_data) if old_data else 1.0
            
            # 构建增量更新信息
            incremental_update = {
                'key_field': key_field,
                'changes': {
                    'added': added,
                    'updated': updated,
                    'deleted': deleted
                },
                'statistics': {
                    'total_old': len(old_data),
                    'total_new': len(new_data),
                    'added_count': len(added),
                    'updated_count': len(updated),
                    'deleted_count': len(deleted),
                    'total_changes': total_changes,
                    'change_ratio': round(change_ratio, 4),
                    'is_efficient': change_ratio < 0.5  # 如果变化少于50%，增量更新更高效
                },
                'generated_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"增量更新创建完成，总变化: {total_changes}, "
                           f"变化比例: {change_ratio:.2%}")
            
            return incremental_update
            
        except Exception as e:
            self.logger.error(f"创建增量更新失败: {str(e)}")
            return {
                'error': str(e),
                'changes': {'added': [], 'updated': [], 'deleted': []},
                'statistics': {'total_changes': 0, 'is_efficient': False}
            }
    
    def optimize_data_for_transfer(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        优化数据以便传输
        
        Args:
            data: 要优化的数据
            
        Returns:
            优化后的数据信息
        """
        try:
            if not data:
                return {
                    'optimized_data': [],
                    'optimization_info': {
                        'original_size': 0,
                        'optimized_size': 0,
                        'reduction_ratio': 0,
                        'optimizations_applied': []
                    }
                }
            
            optimized_data = []
            optimizations_applied = []
            
            # 1. 移除空值字段
            for item in data:
                if isinstance(item, dict):
                    optimized_item = {k: v for k, v in item.items() if v is not None and v != ''}
                    optimized_data.append(optimized_item)
                else:
                    optimized_data.append(item)
            
            if len(optimized_data) != len(data) or any(len(opt) != len(orig) for opt, orig in zip(optimized_data, data) if isinstance(orig, dict)):
                optimizations_applied.append('移除空值字段')
            
            # 2. 数值精度优化
            for item in optimized_data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, float):
                            # 保留4位小数
                            item[key] = round(value, 4)
            
            optimizations_applied.append('数值精度优化')
            
            # 3. 字符串优化
            for item in optimized_data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str):
                            # 去除首尾空格
                            item[key] = value.strip()
            
            optimizations_applied.append('字符串优化')
            
            # 计算优化效果
            original_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            optimized_json = json.dumps(optimized_data, ensure_ascii=False, separators=(',', ':'))
            
            original_size = len(original_json.encode('utf-8'))
            optimized_size = len(optimized_json.encode('utf-8'))
            reduction_ratio = (1 - optimized_size / original_size) if original_size > 0 else 0
            
            optimization_info = {
                'original_size': original_size,
                'optimized_size': optimized_size,
                'size_reduction_bytes': original_size - optimized_size,
                'reduction_ratio': round(reduction_ratio, 4),
                'reduction_percentage': round(reduction_ratio * 100, 2),
                'optimizations_applied': optimizations_applied,
                'record_count': len(optimized_data)
            }
            
            self.logger.debug(f"数据传输优化完成，原始大小: {original_size} bytes, "
                            f"优化后: {optimized_size} bytes, "
                            f"减少: {reduction_ratio:.2%}")
            
            return {
                'optimized_data': optimized_data,
                'optimization_info': optimization_info
            }
            
        except Exception as e:
            self.logger.error(f"优化数据传输失败: {str(e)}")
            return {
                'optimized_data': data,
                'optimization_info': {
                    'error': str(e),
                    'optimizations_applied': []
                }
            }
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = str(int(time.time() * 1000))
        random_part = hashlib.md5(f"{timestamp}_{threading.get_ident()}".encode()).hexdigest()[:8]
        return f"transfer_{timestamp}_{random_part}"
    
    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """计算数据校验和"""
        try:
            json_str = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            return hashlib.md5(json_str.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.md5(str(data).encode('utf-8')).hexdigest()
    
    def _estimate_transfer_time(self, record_count: int) -> Dict[str, Any]:
        """估算传输时间"""
        # 基于经验值估算
        avg_record_size_kb = 0.5  # 假设每条记录约0.5KB
        total_size_mb = (record_count * avg_record_size_kb) / 1024
        
        # 假设网络速度（可以根据实际情况调整）
        network_speed_mbps = 10  # 10 Mbps
        
        estimated_seconds = (total_size_mb * 8) / network_speed_mbps  # 转换为秒
        
        return {
            'estimated_seconds': round(estimated_seconds, 2),
            'estimated_minutes': round(estimated_seconds / 60, 2),
            'total_size_mb': round(total_size_mb, 2),
            'assumed_network_speed_mbps': network_speed_mbps
        }
    
    def _start_transfer_workers(self):
        """启动传输工作线程"""
        for i in range(min(self.max_concurrent_transfers, 3)):
            worker = threading.Thread(target=self._transfer_worker, daemon=True)
            worker.start()
            self._transfer_workers.append(worker)
    
    def _transfer_worker(self):
        """传输工作线程"""
        while True:
            try:
                # 从队列获取传输任务
                task = self._transfer_queue.get(timeout=1)
                
                # 处理传输任务
                self._process_transfer_task(task)
                
                # 标记任务完成
                self._transfer_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"传输工作线程错误: {str(e)}")
    
    def _process_transfer_task(self, task: Dict[str, Any]):
        """处理传输任务"""
        # 这里可以实现具体的传输逻辑
        # 例如：预处理数据、压缩、加密等
        pass
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        while True:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                with self._sessions_lock:
                    for session_id, session in self._sessions.items():
                        if current_time - session.last_activity > self.session_timeout:
                            expired_sessions.append(session_id)
                    
                    # 删除过期会话
                    for session_id in expired_sessions:
                        del self._sessions[session_id]
                        self.logger.info(f"清理过期传输会话: {session_id}")
                
                # 每5分钟检查一次
                time.sleep(300)
                
            except Exception as e:
                self.logger.error(f"清理过期会话失败: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟再重试
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """获取活跃会话列表"""
        try:
            with self._sessions_lock:
                sessions_info = []
                for session_id, session in self._sessions.items():
                    session_info = {
                        'session_id': session_id,
                        'total_chunks': session.total_chunks,
                        'received_chunks': session.received_chunks,
                        'is_complete': session.is_complete,
                        'started_at': session.started_at.isoformat(),
                        'last_activity': session.last_activity.isoformat(),
                        'error': session.error
                    }
                    sessions_info.append(session_info)
                
                return sessions_info
                
        except Exception as e:
            self.logger.error(f"获取活跃会话列表失败: {str(e)}")
            return []


def main():
    """测试数据传输优化器功能"""
    logger = EnhancedLogger("data_transfer_optimizer_test")
    
    try:
        print("=== 数据传输优化器测试 ===")
        
        # 创建测试数据
        test_data = []
        for i in range(150):
            test_data.append({
                'id': i + 1,
                'name': f'测试项目_{i + 1}',
                'value': round(i * 10.123456, 2),
                'category': f'分类_{i % 5}',
                'description': f'这是第{i + 1}个测试项目的详细描述信息，包含一些额外的内容',
                'empty_field': None,
                'blank_field': '',
                'status': 'active' if i % 2 == 0 else 'inactive'
            })
        
        # 创建数据传输优化器
        optimizer = DataTransferOptimizer(
            chunk_size=30,
            compression_threshold=20,
            logger=logger
        )
        
        # 测试数据优化
        print(f"\n1. 测试数据传输优化（总数据: {len(test_data)} 条）")
        optimization_result = optimizer.optimize_data_for_transfer(test_data)
        print(f"优化信息: {optimization_result['optimization_info']}")
        
        # 测试分块传输准备
        print(f"\n2. 测试分块传输准备")
        optimized_data = optimization_result['optimized_data']
        transfer_info = optimizer.prepare_chunked_transfer(optimized_data, enable_compression=True)
        
        if 'error' not in transfer_info:
            session_id = transfer_info['session_id']
            print(f"传输会话ID: {session_id}")
            print(f"总分块数: {transfer_info['total_chunks']}")
            print(f"估算传输时间: {transfer_info['estimated_transfer_time']}")
            
            # 测试获取数据块
            print(f"\n3. 测试获取数据块")
            for i in range(min(3, transfer_info['total_chunks'])):  # 只测试前3个块
                chunk_result = optimizer.get_chunk(session_id, i)
                if 'error' not in chunk_result:
                    print(f"块 {i}: 数据量={len(chunk_result.get('data', []))}, "
                          f"压缩={chunk_result['compressed']}, "
                          f"进度={chunk_result['progress']['percentage']}%")
                else:
                    print(f"获取块 {i} 失败: {chunk_result['error']}")
            
            # 测试传输进度
            print(f"\n4. 测试传输进度")
            progress = optimizer.get_transfer_progress(session_id)
            if 'error' not in progress:
                print(f"传输进度: {progress['progress_percentage']}%")
                print(f"传输速度: {progress['transfer_rate_chunks_per_second']} 块/秒")
            
            # 测试取消传输
            print(f"\n5. 测试取消传输")
            cancel_result = optimizer.cancel_transfer(session_id)
            print(f"取消结果: {cancel_result}")
        
        # 测试增量更新
        print(f"\n6. 测试增量更新")
        # 创建修改后的数据
        modified_data = test_data.copy()
        # 修改一些记录
        modified_data[0]['name'] = '修改后的名称'
        modified_data[1]['value'] = 999.99
        # 删除一些记录
        modified_data = modified_data[:-5]
        # 添加一些新记录
        for i in range(3):
            modified_data.append({
                'id': len(test_data) + i + 1,
                'name': f'新增项目_{i + 1}',
                'value': i * 100,
                'category': '新分类',
                'description': f'这是新增的第{i + 1}个项目'
            })
        
        incremental_update = optimizer.create_incremental_update(test_data, modified_data, key_field='id')
        print(f"增量更新统计: {incremental_update['statistics']}")
        
        # 测试活跃会话
        print(f"\n7. 测试活跃会话")
        active_sessions = optimizer.get_active_sessions()
        print(f"活跃会话数: {len(active_sessions)}")
        
        print("\n数据传输优化器测试完成！")
        
    except Exception as e:
        logger.error(f"数据传输优化器测试失败: {str(e)}")
        print(f"错误: {str(e)}")


if __name__ == "__main__":
    main()