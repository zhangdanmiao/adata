# -*- coding: utf-8 -*-
"""
@desc: 滑动窗口频率限制器
@author: 
@time: 2026/03/24
"""
import threading
import time
from collections import defaultdict
from urllib.parse import urlparse


class SlidingWindowRateLimiter:
    """滑动窗口频率限制器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._requests = defaultdict(list)

    def check_and_record(self, url, max_count=30, window_seconds=60):
        """
        检查请求是否超过频率限制，并记录当前请求
        :param url: 请求的URL
        :param max_count: 时间窗口内最大请求次数
        :param window_seconds: 时间窗口大小，单位秒
        :return: (是否允许请求, 剩余请求次数, 重置时间)
        """
        domain = self._extract_domain(url)
        current_time = time.time()
        
        with self._lock:
            timestamps = self._requests[domain]
            
            cutoff = current_time - window_seconds
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]
            self._requests[domain] = valid_timestamps
            
            if len(valid_timestamps) >= max_count:
                valid_timestamps.sort()
                reset_time = valid_timestamps[0] + window_seconds
                return False, 0, reset_time
            
            self._requests[domain].append(current_time)
            return True, max_count - len(self._requests[domain]), current_time + window_seconds

    def _extract_domain(self, url):
        """提取完整域名"""
        parsed = urlparse(url)
        return parsed.netloc

    def reset_domain(self, url):
        """重置指定域名的请求记录"""
        domain = self._extract_domain(url)
        with self._lock:
            if domain in self._requests:
                del self._requests[domain]

    def reset_all(self):
        """重置所有域名的请求记录"""
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()
