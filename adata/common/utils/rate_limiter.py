# -*- coding: utf-8 -*-
"""
@desc: 请求频率限制器 - 基于滑动窗口算法
@author: 1nchaos
@time: 2026/3/24
@log: change log

功能说明：
- 基于域名进行请求频率控制
- 默认限制：同一域名每分钟最多30次请求
- 支持自定义频率限制配置
- 线程安全实现
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse


@dataclass
class RateLimitConfig:
    """频率限制配置类"""
    enabled: bool = True          # 是否启用限流
    max_requests: int = 30        # 时间窗口内最大请求数
    window: int = 60              # 时间窗口（秒）
    domain: str = 'auto'          # 域名，'auto'表示自动从URL提取


class RateLimitExceeded(Exception):
    """请求频率超过限制异常"""
    
    def __init__(self, domain: str, max_requests: int, window: int, retry_after: int):
        self.domain = domain
        self.max_requests = max_requests
        self.window = window
        self.retry_after = retry_after
        self.status_code = 429  # HTTP 429 Too Many Requests
        super().__init__(f"请求频率超过限制: 域名 '{domain}' 在 {window} 秒内最多允许 {max_requests} 次请求，请 {retry_after} 秒后重试")


class RateLimiter:
    """
    基于滑动窗口的请求频率限制器
    
    特性：
    1. 按域名独立限流
    2. 线程安全
    3. 滑动窗口算法，精确控制
    4. 支持动态配置
    
    使用示例：
        limiter = RateLimiter()
        
        # 检查是否允许请求
        if limiter.allow_request('https://api.example.com/data'):
            # 执行请求
            pass
        else:
            # 处理限流
            pass
    """
    
    def __init__(self):
        # 存储每个域名的请求时间戳列表 {domain: [timestamp1, timestamp2, ...]}
        self._requests: Dict[str, List[float]] = defaultdict(list)
        # 存储每个域名的自定义配置 {domain: RateLimitConfig}
        self._configs: Dict[str, RateLimitConfig] = {}
        # 线程锁，保证线程安全
        self._lock = threading.RLock()
        # 默认配置
        self._default_config = RateLimitConfig()
    
    def _extract_domain(self, url: str) -> str:
        """
        从URL中提取域名
        
        :param url: 请求URL
        :return: 域名
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() or parsed.path.lower()
        except Exception:
            # 如果解析失败，返回原始字符串
            return url.lower()
    
    def set_domain_config(self, domain: str, config: Union[RateLimitConfig, dict]):
        """
        为指定域名设置频率限制配置
        
        :param domain: 域名
        :param config: 配置对象或字典
        """
        if isinstance(config, dict):
            config = RateLimitConfig(**config)
        
        with self._lock:
            self._configs[domain.lower()] = config
    
    def set_default_config(self, config: Union[RateLimitConfig, dict]):
        """
        设置默认频率限制配置
        
        :param config: 配置对象或字典
        """
        if isinstance(config, dict):
            config = RateLimitConfig(**config)
        
        with self._lock:
            self._default_config = config
    
    def _get_config(self, domain: str, override_config: Optional[RateLimitConfig] = None) -> RateLimitConfig:
        """
        获取域名的频率限制配置
        
        优先级：override_config > 域名特定配置 > 默认配置
        
        :param domain: 域名
        :param override_config: 临时覆盖配置
        :return: 配置对象
        """
        if override_config is not None:
            return override_config
        
        return self._configs.get(domain, self._default_config)
    
    def _clean_old_requests(self, domain: str, window: float, current_time: float):
        """
        清理过期的请求记录（滑动窗口）
        
        :param domain: 域名
        :param window: 时间窗口（秒）
        :param current_time: 当前时间戳
        """
        cutoff_time = current_time - window
        self._requests[domain] = [
            ts for ts in self._requests[domain] 
            if ts > cutoff_time
        ]
    
    def allow_request(self, url: str, rate_limit: Optional[Union[RateLimitConfig, dict]] = None) -> tuple:
        """
        检查是否允许发送请求
        
        :param url: 请求URL
        :param rate_limit: 频率限制配置（可选）
        :return: (是否允许, 域名, 配置, 下次可重试时间)
                 如果允许，下次可重试时间为0
        """
        # 提取域名
        domain = self._extract_domain(url)
        
        # 解析配置
        if isinstance(rate_limit, dict):
            rate_limit = RateLimitConfig(**rate_limit)
        
        config = self._get_config(domain, rate_limit)
        
        # 如果禁用限流，直接允许
        if not config.enabled:
            return True, domain, config, 0
        
        current_time = time.time()
        
        with self._lock:
            # 清理过期记录
            self._clean_old_requests(domain, config.window, current_time)
            
            # 获取当前窗口内的请求数
            request_count = len(self._requests[domain])
            
            # 检查是否超过限制
            if request_count >= config.max_requests:
                # 计算需要等待的时间
                oldest_request = min(self._requests[domain]) if self._requests[domain] else current_time
                retry_after = int(oldest_request + config.window - current_time) + 1
                return False, domain, config, max(1, retry_after)
            
            # 记录本次请求
            self._requests[domain].append(current_time)
            return True, domain, config, 0
    
    def check_rate_limit(self, url: str, rate_limit: Optional[Union[RateLimitConfig, dict]] = None):
        """
        检查频率限制，如果超过限制则抛出异常
        
        :param url: 请求URL
        :param rate_limit: 频率限制配置（可选）
        :raises RateLimitExceeded: 当请求频率超过限制时抛出
        """
        allowed, domain, config, retry_after = self.allow_request(url, rate_limit)
        
        if not allowed:
            raise RateLimitExceeded(
                domain=domain,
                max_requests=config.max_requests,
                window=config.window,
                retry_after=retry_after
            )
    
    def get_domain_status(self, domain: Optional[str] = None) -> dict:
        """
        获取域名的限流状态
        
        :param domain: 域名（可选，不传返回所有域名）
        :return: 状态字典
        """
        current_time = time.time()
        
        with self._lock:
            if domain:
                domain = domain.lower()
                config = self._get_config(domain)
                self._clean_old_requests(domain, config.window, current_time)
                return {
                    'domain': domain,
                    'current_requests': len(self._requests[domain]),
                    'max_requests': config.max_requests,
                    'window': config.window,
                    'remaining': max(0, config.max_requests - len(self._requests[domain]))
                }
            else:
                result = {}
                for d in list(self._requests.keys()):
                    config = self._get_config(d)
                    self._clean_old_requests(d, config.window, current_time)
                    result[d] = {
                        'current_requests': len(self._requests[d]),
                        'max_requests': config.max_requests,
                        'window': config.window,
                        'remaining': max(0, config.max_requests - len(self._requests[d]))
                    }
                return result
    
    def reset(self, domain: Optional[str] = None):
        """
        重置限流记录
        
        :param domain: 域名（可选，不传重置所有）
        """
        with self._lock:
            if domain:
                domain = domain.lower()
                if domain in self._requests:
                    del self._requests[domain]
            else:
                self._requests.clear()


# 全局限流器实例
rate_limiter = RateLimiter()
