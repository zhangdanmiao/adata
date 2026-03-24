# -*- coding: utf-8 -*-
"""
@desc: 异常信息
@author: 1nchaos
@time: 2023/7/8
@log: change log
"""

THS_IP_LIMIT_RES = '<h1>Nginx forbidden.</h1>'
"""同花顺Ip限制的返回结果"""
THS_IP_LIMIT_MSG = "ths流量防控：当前ip被限制，请降低请求频率或更换ip或使用代理设置，勿使用国外ip！！！"
"""同花顺IP：403限制提醒"""
RATE_LIMIT_MSG = "请求频率超限：域名 {domain} 在 {window_seconds} 秒内最多允许 {max_count} 次请求，请稍后再试"
"""请求频率限制提醒"""
