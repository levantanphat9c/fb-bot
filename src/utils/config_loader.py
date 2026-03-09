"""
Configuration loader module
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file and environment variables
    
    Args:
        config_path: Path to config YAML file
    
    Returns:
        Dictionary containing configuration
    """
    # Load environment variables
    load_dotenv()
    
    # Read config file
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Replace environment variable placeholders
    config = _replace_env_vars(config)
    
    # Override with actual environment variables if present
    if os.getenv('FACEBOOK_PAGE_ID'):
        config['facebook']['page_id'] = os.getenv('FACEBOOK_PAGE_ID')
    if os.getenv('FACEBOOK_ACCESS_TOKEN'):
        config['facebook']['access_token'] = os.getenv('FACEBOOK_ACCESS_TOKEN')
    if os.getenv('ANTHROPIC_API_KEY'):
        # Store in config for easy access
        config['anthropic'] = {'api_key': os.getenv('ANTHROPIC_API_KEY')}
    if os.getenv('UNSPLASH_ACCESS_KEY'):
        config['unsplash'] = {'access_key': os.getenv('UNSPLASH_ACCESS_KEY')}
    if os.getenv('BGG_API_TOKEN'):
        config['bgg'] = {'api_token': os.getenv('BGG_API_TOKEN')}
    
    return config


def _replace_env_vars(obj: Any) -> Any:
    """
    Recursively replace ${VAR_NAME} placeholders with environment variables
    
    Args:
        obj: Object to process (dict, list, or string)
    
    Returns:
        Object with replaced values
    """
    if isinstance(obj, dict):
        return {key: _replace_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_replace_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
        env_var = obj[2:-1]
        return os.getenv(env_var, obj)
    else:
        return obj

