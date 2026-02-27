import os
import sys
import time
import logging
import platform
import json
import shutil
import socket
import re
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
import psutil
from typing import Dict, Any, Optional

_LOGGER_INSTANCE = None

class AdvancedLogger:
    
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.usage_stats_file = os.path.join(log_dir, "usage_stats.json")
        self.usage_stats = {
            "scans_count": 0,
            "total_scan_time": 0,
            "paths_scanned": 0,
            "panels_found": 0,
            "last_scan": None,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "errors_count": 0,
            "warnings_count": 0
        }
        
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
                print(f"Created logs directory: {log_dir}")
            except Exception as e:
                print(f"Error creating logs directory: {str(e)}")
                self.log_dir = "."
        
        self._setup_loggers()
        
        self._log_system_info()
        
        self._clean_old_logs()
        
        self._update_stats()

    def _setup_loggers(self):
        self.error_log = os.path.join(self.log_dir, "error.log")
        self.warning_log = os.path.join(self.log_dir, "warning.log")
        self.info_log = os.path.join(self.log_dir, "info.log")
        self.master_log = os.path.join(self.log_dir, "master.log")
        self.usage_log = os.path.join(self.log_dir, "usage.log")
        
        logging.root.setLevel(logging.DEBUG)
        
        self.console_handler = logging.StreamHandler()
        self.console_handler.setLevel(logging.INFO)
        self.console_handler.setFormatter(self._create_formatter(colored=True))
        
        self.error_logger = self._setup_file_logger("error", self.error_log, logging.ERROR)
        self.warning_logger = self._setup_file_logger("warning", self.warning_log, logging.WARNING)
        self.info_logger = self._setup_file_logger("info", self.info_log, logging.INFO)
        self.master_logger = self._setup_file_logger("master", self.master_log, logging.DEBUG)
        self.usage_logger = self._setup_file_logger("usage", self.usage_log, logging.INFO)
        
        self.master_logger.addHandler(self.console_handler)
        
        self.master_logger.info("Logging system initialized")

    def _setup_file_logger(self, name, log_file, level):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        try:
            handler = self._create_file_handler(log_file, level)
            logger.addHandler(handler)
        except Exception as e:
            print(f"Error setting up {name} logger: {str(e)}")
            logger.addHandler(self.console_handler)
        return logger

    def _create_file_handler(self, log_file, level):
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                
            handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024, 
                backupCount=5
            )
            handler.setLevel(level)
            handler.setFormatter(self._create_formatter())
            return handler
        except Exception as e:
            print(f"Error creating file handler for {log_file}: {str(e)}")
            raise

    def _create_formatter(self, colored=False):
        if colored:
            return ColoredFormatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            return logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

    def _log_system_info(self):
        system_info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "hostname": socket.gethostname(),
            "cpu_cores": psutil.cpu_count(),
            "total_memory": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "available_memory": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
        }
        
        self.master_logger.info("System Information:")
        for key, value in system_info.items():
            self.master_logger.info(f"  {key}: {value}")

    def _clean_old_logs(self):
        try:
            current_time = datetime.now()
            cutoff_date = current_time - timedelta(days=30)
            
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                
                if not os.path.isfile(filepath):
                    continue
                    
                if not filename.endswith('.log') and not filename.endswith('.log.1'):
                    continue
                
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_date:
                    os.remove(filepath)
                    self.master_logger.info(f"Removed old log file: {filename}")
        except Exception as e:
            self.master_logger.error(f"Error cleaning old logs: {str(e)}")

    def _update_stats(self):
        try:
            if os.path.exists(self.usage_stats_file):
                with open(self.usage_stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    
                for key, value in loaded_stats.items():
                    if key in self.usage_stats:
                        self.usage_stats[key] = value
                        
                self.usage_stats["last_session_start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                self._save_stats()
                
            self.usage_logger.info(f"Usage statistics loaded: {self.usage_stats}")
        except Exception as e:
            self.master_logger.error(f"Error updating stats: {str(e)}")
            
    def _save_stats(self):
        try:
            with open(self.usage_stats_file, 'w') as f:
                json.dump(self.usage_stats, f, indent=4)
        except Exception as e:
            self.master_logger.error(f"Error saving usage stats: {str(e)}")
            
    def log_scan_start(self, url, mode, paths_count):
        message = f"Scan started for {url} using mode {mode} with {paths_count} paths"
        self.info_logger.info(message)
        
        self.usage_stats["scans_count"] += 1
        self.usage_stats["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_stats()

    def log_scan_end(self, url, duration, found_count, total_scanned):
        message = (
            f"Scan completed for {url} in {duration:.2f} seconds. "
            f"Found {found_count} admin panels out of {total_scanned} paths."
        )
        self.usage_logger.info(message)
        self.master_logger.info(message)
        
        self.usage_stats["total_scan_time"] += duration
        self.usage_stats["paths_scanned"] += total_scanned
        self.usage_stats["panels_found"] += found_count
        self._save_stats()
    
    def log_scan_complete(self, url, total_paths, found_count, scan_time):
        message = f"Scan completed for {url}: found {found_count}/{total_paths} in {scan_time:.2f}s"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_results_exported(self, formats, count):
        formats_str = ", ".join(formats)
        message = f"Exported {count} results to formats: {formats_str}"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_settings_change(self, setting_name, old_value, new_value):
        message = f"Setting changed: {setting_name} from '{old_value}' to '{new_value}'"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_error(self, message, exc_info=None):
        self.error_logger.error(message, exc_info=exc_info)
        self.master_logger.error(message, exc_info=exc_info)
        self.usage_stats["errors_count"] += 1
        self._save_stats()
    
    def log_warning(self, message):
        self.warning_logger.warning(message)
        self.master_logger.warning(message)
        self.usage_stats["warnings_count"] += 1
        self._save_stats()
    
    def log_info(self, message):
        self.info_logger.info(message)
        self.master_logger.info(message)
    
    def log_debug(self, message):
        self.master_logger.debug(message)
    
    def shutdown(self):
        end_time = datetime.now()
        start_time = datetime.strptime(self.usage_stats["start_time"], "%Y-%m-%d %H:%M:%S")
        session_duration = (end_time - start_time).total_seconds()
        
        message = (
            f"Logging session ended. Duration: {session_duration:.2f} seconds. "
            f"Scans: {self.usage_stats['scans_count']}, "
            f"Errors: {self.usage_stats['errors_count']}, "
            f"Warnings: {self.usage_stats['warnings_count']}"
        )
        self.usage_logger.info(message)
        self.master_logger.info(message)
        
        self.usage_stats["last_shutdown"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        self.usage_stats["last_session_duration"] = session_duration
        self._save_stats()
        
        logging.shutdown()


class ColoredFormatter(logging.Formatter):
    
    COLORS = {
        'DEBUG': '\033[94m',  
        'INFO': '\033[92m',   
        'WARNING': '\033[93m', 
        'ERROR': '\033[91m',  
        'CRITICAL': '\033[91m\033[1m',  
        'RESET': '\033[0m'    
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname
        
        return super().format(record)


def get_logger(log_dir="logs") -> AdvancedLogger:
    global _LOGGER_INSTANCE
    
    if _LOGGER_INSTANCE is None:
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                print(f"Created log directory: {log_dir}")
                
            _LOGGER_INSTANCE = AdvancedLogger(log_dir)
            print(f"Logger initialized with log directory: {log_dir}")
        except Exception as e:
            print(f"Error initializing logger: {str(e)}")
            _LOGGER_INSTANCE = AdvancedLogger(".")
            print("Logger initialized with fallback to current directory")
    
    return _LOGGER_INSTANCE 
