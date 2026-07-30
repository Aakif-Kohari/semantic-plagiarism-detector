"""
config.py
---------
Configuration management and validation for branding settings.
Provides safe loading and validation of branding_config.json with graceful fallbacks.
"""

import json
import logging
import os
import re
from typing import Optional, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

# Default branding configuration
DEFAULT_BRAND_COLOR = "#1e3a8a"
DEFAULT_LOGO_PATH = None

# Path to branding config file (relative to project root)
BRANDING_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "branding_config.json")
)


def validate_hex_color(color: str) -> bool:
    """
    Validate that a string is a valid hex color code.
    
    Args:
        color: Color string to validate
        
    Returns:
        True if valid hex color (#RRGGBB or #RGB), False otherwise
    """
    if not color or not isinstance(color, str):
        return False
    
    # Match #RRGGBB or #RGB format
    pattern = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    return bool(pattern.match(color))


class BrandingConfig:
    """
    validated branding configuration with safe defaults.
    """
    
    def __init__(
        self,
        brand_color: str = DEFAULT_BRAND_COLOR,
        logo_path: Optional[str] = DEFAULT_LOGO_PATH,
    ):
        """
        Initialize branding configuration.
        
        Args:
            brand_color: Hex color code for branding
            logo_path: Optional path to logo file
        """
        self.brand_color = brand_color
        self.logo_path = logo_path
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrandingConfig":
        """
        Create BrandingConfig from dictionary with validation.
        
        Args:
            data: Dictionary containing branding configuration
            
        Returns:
            BrandingConfig instance with validated values
        """
        brand_color = data.get("brand_color", DEFAULT_BRAND_COLOR)
        logo_path = data.get("logo_path", DEFAULT_LOGO_PATH)
        
        # Validate brand_color
        if brand_color is not None and not validate_hex_color(brand_color):
            logger.warning(
                f"Invalid brand_color format: '{brand_color}'. "
                f"Expected hex color (#RRGGBB or #RGB). Using default: {DEFAULT_BRAND_COLOR}"
            )
            brand_color = DEFAULT_BRAND_COLOR
        
        # Validate logo_path (allow None or string)
        if logo_path is not None and not isinstance(logo_path, str):
            logger.warning(
                f"Invalid logo_path type: {type(logo_path).__name__}. "
                f"Expected string or None. Using default: {DEFAULT_LOGO_PATH}"
            )
            logo_path = DEFAULT_LOGO_PATH
        
        return cls(brand_color=brand_color, logo_path=logo_path)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert BrandingConfig to dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "brand_color": self.brand_color,
            "logo_path": self.logo_path,
        }


def load_branding_config(config_path: Optional[str] = None) -> BrandingConfig:
    """
    Load and validate branding configuration from JSON file.
    
    Args:
        config_path: Optional path to branding config file. 
                    If not provided, uses default BRANDING_CONFIG_PATH.
        
    Returns:
        BrandingConfig instance with validated values or defaults if loading fails
    """
    if config_path is None:
        config_path = BRANDING_CONFIG_PATH
    
    # Check if file exists
    if not os.path.exists(config_path):
        logger.info(
            f"Branding config file not found at {config_path}. Using default branding configuration."
        )
        return BrandingConfig()
    
    # Try to load and parse JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(
            f"Invalid JSON in branding config file {config_path}: {e}. Using default branding configuration."
        )
        return BrandingConfig()
    except Exception as e:
        logger.warning(
            f"Error reading branding config file {config_path}: {e}. Using default branding configuration."
        )
        return BrandingConfig()
    
    # Validate and create config
    try:
        config = BrandingConfig.from_dict(data)
        logger.info(f"Successfully loaded branding configuration from {config_path}")
        return config
    except Exception as e:
        logger.warning(
            f"Error validating branding configuration: {e}. Using default branding configuration."
        )
        return BrandingConfig()


# Global branding configuration instance
_branding_config: Optional[BrandingConfig] = None


def get_branding_config() -> BrandingConfig:
    """
    Get the global branding configuration instance.
    Loads on first call and caches the result.
    
    Returns:
        BrandingConfig instance
    """
    global _branding_config
    if _branding_config is None:
        _branding_config = load_branding_config()
    return _branding_config


def reload_branding_config() -> BrandingConfig:
    """
    Force reload the branding configuration from file.
    Useful for testing or when config file changes at runtime.
    
    Returns:
        Newly loaded BrandingConfig instance
    """
    global _branding_config
    _branding_config = load_branding_config()
    return _branding_config
