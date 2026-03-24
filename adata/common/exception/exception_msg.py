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

# 请求频率限制相关
RATE_LIMIT_STATUS_CODE = 429
"""请求频率超过限制的HTTP状态码"""
RATE_LIMIT_ERROR = "RATE_LIMIT_EXCEEDED"
"""请求频率超过限制的错误码"""
RATE_LIMIT_MSG_TEMPLATE = "请求频率超过限制: 域名 '{}' 在 {} 秒内最多允许 {} 次请求，请 {} 秒后重试"
"""请求频率限制提示消息模板"""
