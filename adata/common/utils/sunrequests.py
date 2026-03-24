# -*- coding: utf-8 -*-
"""
代理:https://jahttp.zhimaruanjian.com/getapi/

@desc: adata 请求工具类
@author: 1nchaos
@time:2023/3/30
@log: 封装请求次数，增加频率限制功能
"""

import threading
import time
from typing import Optional, Union

import requests

from adata.common.utils.rate_limiter import RateLimiter, RateLimitConfig, rate_limiter as global_rate_limiter


class SunProxy(object):
    _data = {}
    _instance_lock = threading.Lock()

    def __init__(self):
        pass

    def __new__(cls, *args, **kwargs):
        if not hasattr(SunProxy, "_instance"):
            with SunProxy._instance_lock:
                if not hasattr(SunProxy, "_instance"):
                    SunProxy._instance = object.__new__(cls)

    @classmethod
    def set(cls, key, value):
        cls._data[key] = value

    @classmethod
    def get(cls, key):
        return cls._data.get(key)

    @classmethod
    def delete(cls, key):
        if key in cls._data:
            del cls._data[key]


class RateLimitResponse:
    """
    频率限制响应对象
    当请求频率超过限制时返回此对象，模拟requests.Response接口
    """
    
    def __init__(self, domain: str, max_requests: int, window: int, retry_after: int):
        self.status_code = 429  # HTTP 429 Too Many Requests
        self.domain = domain
        self.max_requests = max_requests
        self.window = window
        self.retry_after = retry_after
        self.headers = {'Retry-After': str(retry_after)}
        self._json_data = {
            'status_code': 429,
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': f'请求频率超过限制: 域名 "{domain}" 在 {window} 秒内最多允许 {max_requests} 次请求，请 {retry_after} 秒后重试',
            'domain': domain,
            'retry_after': retry_after
        }
    
    def json(self):
        """返回JSON格式的错误信息"""
        return self._json_data
    
    def text(self):
        """返回文本格式的错误信息"""
        return self._json_data['message']
    
    def __bool__(self):
        """频率限制响应始终为False，表示请求未成功"""
        return False


class SunRequests(object):
    def __init__(self, sun_proxy: SunProxy = None, rate_limiter_instance: RateLimiter = None) -> None:
        super().__init__()
        self.sun_proxy = sun_proxy
        # 使用传入的限流器或默认的全局限流器
        self.rate_limiter = rate_limiter_instance or global_rate_limiter

    def request(self, method='get', url=None, times=3, retry_wait_time=1588, proxies=None, wait_time=None, 
                rate_limit: Optional[Union[dict, RateLimitConfig]] = None, **kwargs):
        """
        简单封装的请求，参考requests，增加循环次数和次数之间的等待时间
        
        :param proxies: 代理配置
        :param method: 请求方法： get；post
        :param url: url
        :param times: 次数，int
        :param retry_wait_time: 重试等待时间，毫秒
        :param wait_time: 等待时间：毫秒；表示每个请求的间隔时间，在请求之前等待sleep，主要用于防止请求太频繁的限制。
        :param rate_limit: 频率限制配置，可选
            - enabled: 是否启用限流，默认True
            - max_requests: 时间窗口内最大请求数，默认30
            - window: 时间窗口（秒），默认60
            - domain: 域名，'auto'表示自动从URL提取
            示例: {'enabled': True, 'max_requests': 30, 'window': 60}
        :param kwargs: 其它 requests 参数，用法相同
        :return: requests.Response 或 RateLimitResponse（当触发限流时）
        """
        # 0. 检查频率限制
        if url and self.rate_limiter:
            allowed, domain, config, retry_after = self.rate_limiter.allow_request(url, rate_limit)
            if not allowed:
                # 触发频率限制，返回限流响应对象
                return RateLimitResponse(
                    domain=domain,
                    max_requests=config.max_requests,
                    window=config.window,
                    retry_after=retry_after
                )
        
        # 1. 获取设置代理
        proxies = self.__get_proxies(proxies)
        # 2. 请求数据结果
        res = None
        for i in range(times):
            if wait_time:
                time.sleep(wait_time / 1000)
            res = requests.request(method=method, url=url, proxies=proxies, **kwargs)
            if res.status_code in (200, 404):
                return res
            time.sleep(retry_wait_time / 1000)
            if i == times - 1:
                return res
        return res

    def __get_proxies(self, proxies):
        """
        获取代理配置
        """
        if proxies is None:
            proxies = {}
        is_proxy = SunProxy.get('is_proxy')
        ip = SunProxy.get('ip')
        proxy_url = SunProxy.get('proxy_url')
        if not ip and is_proxy and proxy_url:
            ip = requests.get(url=proxy_url).text.replace('\r\n', '') \
                .replace('\r', '').replace('\n', '').replace('\t', '')
        if is_proxy and ip:
            proxies = {'https': f"http://{ip}", 'http': f"http://{ip}"}
        return proxies

    def set_rate_limit_config(self, domain: str, config: Union[dict, RateLimitConfig]):
        """
        为指定域名设置频率限制配置
        
        :param domain: 域名
        :param config: 配置对象或字典
            示例: {'enabled': True, 'max_requests': 60, 'window': 60}
        """
        if self.rate_limiter:
            self.rate_limiter.set_domain_config(domain, config)

    def set_default_rate_limit(self, config: Union[dict, RateLimitConfig]):
        """
        设置默认频率限制配置
        
        :param config: 配置对象或字典
            示例: {'enabled': True, 'max_requests': 30, 'window': 60}
        """
        if self.rate_limiter:
            self.rate_limiter.set_default_config(config)

    def get_rate_limit_status(self, domain: Optional[str] = None):
        """
        获取频率限制状态
        
        :param domain: 域名（可选，不传返回所有域名）
        :return: 状态字典
        """
        if self.rate_limiter:
            return self.rate_limiter.get_domain_status(domain)
        return {}

    def reset_rate_limit(self, domain: Optional[str] = None):
        """
        重置频率限制记录
        
        :param domain: 域名（可选，不传重置所有）
        """
        if self.rate_limiter:
            self.rate_limiter.reset(domain)


sun_requests = SunRequests()
