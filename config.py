from typing import Dict
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API Keys and External Service Configurations
# EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY", "default_key")

# Weights for multicriteria evaluation
EVALUATION_WEIGHTS: Dict[str, float] = {
    'experience': 0.3,
    'skills': 0.4,
    'education': 0.2,
    'languages': 0.1
}

# Education level mapping
EDUCATION_LEVELS: Dict[str, float] = {
    'None': 0.0,
    'School': 0.2,
    'Bachelor': 0.5,
    'Master': 0.7,
    'PhD': 1.0
}

# External API endpoints (commented out for now)
# API_ENDPOINTS = {
#     'diploma_verification': 'https://external-check.service.com/checkDiploma',
#     'linkedin_profile': 'https://api.linkedin.com/v2/profile',
#     'github_profile': 'https://api.github.com/users'
# }

# Database configuration
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hr_system.db")
