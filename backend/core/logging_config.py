import logging
import sys
import structlog
from core.config import settings

def configure_logging():
    """
    Configure structlog and intercept standard library logging.
    - Local Dev: Pretty console output (colors).
    - Production: JSON output (for Cloud Run).
    """
    
    # 1. Define Processors (Shared between stdlib and structlog)
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add extra context columns if needed here
    ]

    # 2. Define Renderer based on Environment
    if settings.ENVIRONMENT == "production":
        # JSON for Cloud Run
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Pretty Colors for Local Dev
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]

    # 3. Configure Structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 4. Configure Standard Library Logging (for Uvicorn/SQLAlchemy compatibility)
    # This intercepts standard logging calls and processes them through the chain above
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production" else structlog.dev.ConsoleRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
    
    # Silence noisy loggers if needed
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
