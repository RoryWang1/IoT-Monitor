"""
API dependency injection module
Provide unified database service dependency injection
"""

import logging
from fastapi import HTTPException
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Global service registry
_service_registry = {}

def register_database_service(service):
    """Register the database service to the global registry"""
    _service_registry['database_service'] = service
    logger.info("Database service registered in dependency injection")

def get_database_service_instance():
    """
    Obtain the instance of the database service
    """
    try:
        # Try to obtain it from the registry
        database_service = _service_registry.get('database_service')
        
        if database_service is not None:
            logger.debug("Successfully got database service from registry")
            return database_service
        
        # Try to obtain it from the app module
        try:
            import importlib
            import sys
            
            # Make sure that the app module has been loaded and initialized
            if 'backend.api.app' not in sys.modules:
                logger.warning("App module not yet loaded, importing now")
                import backend.api.app as app_module
            else:
                app_module = sys.modules['backend.api.app']
            
            # Obtain the global database_service
            database_service = getattr(app_module, 'database_service', None)
            
            if database_service is not None:
                # Register to the registry
                register_database_service(database_service)
                logger.debug("Successfully got database service from app module and registered")
                return database_service
                
        except Exception as import_error:
            logger.warning(f"Failed to import from app module: {import_error}")
        
        # If both methods fail, raise an explicit error
        logger.error("Database service not found in registry or app module")
        raise HTTPException(
            status_code=503,
            detail="Database service not properly initialized - check application startup"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get database service instance: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database service error: {str(e)}"
        )


def get_timezone_manager():
    """
    Obtain the instance of the timezone manager
    """
    try:
        from database.services.timezone_manager import timezone_manager
        return timezone_manager
    except ImportError as e:
        logger.error(f"Failed to import timezone manager: {e}")
        raise HTTPException(
            status_code=503,
            detail="Timezone manager not available"
        )
    except Exception as e:
        logger.error(f"Failed to get timezone manager: {e}")
        raise HTTPException(
            status_code=503,
            detail="Timezone manager not available"
        )
