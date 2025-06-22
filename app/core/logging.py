import structlog
import logging
import sys
import os
from pathlib import Path
from .config import settings

def setup_logging():
    """Setup structured logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Add file handler
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    logger = structlog.get_logger()
    logger.info("Logging configured", 
                log_level=settings.log_level,
                log_file=settings.log_file) 