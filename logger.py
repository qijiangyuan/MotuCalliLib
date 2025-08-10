import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 日志级别映射
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
    'none': logging.CRITICAL + 10  # 自定义级别，用于完全禁用日志
}

# 默认配置
DEFAULT_LOG_LEVEL = 'info'
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_DIR = 'logs'
DEFAULT_LOG_FILE = 'app.log'
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

class Logger:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, name='motu_callilib', level=None, log_to_console=True, log_to_file=False):
        # 单例模式，确保只初始化一次
        if self._initialized:
            return
        
        self.name = name
        self.logger = logging.getLogger(name)
        
        # 设置日志级别
        self.set_level(level or DEFAULT_LOG_LEVEL)
        
        # 清除现有的处理器
        for handler in self.logger.handlers[:]:  
            self.logger.removeHandler(handler)
        
        # 设置格式化器
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        
        # 添加控制台处理器
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件处理器
        if log_to_file:
            # 确保日志目录存在
            log_dir = os.path.join(os.getcwd(), DEFAULT_LOG_DIR)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 创建滚动文件处理器
            log_file = os.path.join(log_dir, DEFAULT_LOG_FILE)
            try:
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=DEFAULT_MAX_BYTES,
                    backupCount=DEFAULT_BACKUP_COUNT,
                    encoding='utf-8'  # 添加UTF-8编码设置
                )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                sys.stderr.write(f"创建日志文件处理器失败: {e}\n")
                import traceback
                traceback.print_exc()
        
        self._initialized = True
    
    def set_level(self, level):
        """设置日志级别"""
        if isinstance(level, str):
            level = level.lower()
            level = LOG_LEVELS.get(level, logging.INFO)
        
        self.logger.setLevel(level)
    
    def debug(self, message, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)

# 创建默认日志实例
default_logger = None  # 初始化为None，稍后再创建

# 便捷函数
def get_logger(name=None, level=None, log_to_console=True, log_to_file=False):
    """获取或创建一个日志记录器
    
    Args:
        name: 日志记录器名称，默认使用默认记录器
        level: 日志级别，可以是字符串('debug', 'info', 'warning', 'error', 'critical', 'none')或logging模块的级别常量
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
    
    Returns:
        Logger实例
    """
    global default_logger
    
    if name is None:
        # 如果default_logger还没有被初始化，则创建它
        if default_logger is None:
            default_logger = Logger(level=level or DEFAULT_LOG_LEVEL, 
                                   log_to_console=log_to_console, 
                                   log_to_file=log_to_file)
        else:
            if level is not None:
                default_logger.set_level(level)
        return default_logger
    
    return Logger(name, level, log_to_console, log_to_file)

# 从环境变量获取日志级别
def configure_from_env():
    """从环境变量配置日志
    
    环境变量:
        MOTU_LOG_LEVEL: 日志级别 (debug, info, warning, error, critical, none)
        MOTU_LOG_TO_FILE: 是否输出到文件 (true, false)
    """
    log_level = os.environ.get('MOTU_LOG_LEVEL', DEFAULT_LOG_LEVEL).lower()
    log_to_file = os.environ.get('MOTU_LOG_TO_FILE', 'false').lower() == 'true'
    
    # 直接创建一个新的Logger实例，而不是使用get_logger
    global default_logger
    default_logger = Logger(level=log_level, log_to_file=log_to_file)
    
    return default_logger