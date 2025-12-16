"""
Setup.py - Packaging & Installation Metadata

This file contains ONLY packaging and installation information:
- Project metadata (name, version, author, license)
- Dependencies (install_requires)
- Entry points (console scripts)
- Package discovery

❌ NOT for runtime configuration
✅ This is for pip/pdm to install your project
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    # Project metadata
    name="voice_platform",
    version="0.1.0",
    description="Restaurant AI Voice Assistant - Modular Voice Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Kinjal",
    author_email="",  # Add if available
    license="MIT",
    url="",  # Add repository URL if available
    
    # Package discovery
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*", "env", "env.*"]),
    include_package_data=True,
    python_requires=">=3.10",  # Match environment files (CPU/GPU envs use Python 3.10)
    
    # Dependencies - synced with requirements.txt
    install_requires=[
        # Core ML/AI Framework
        "torch>=2.0.0",
        "transformers>=4.40.0,<4.46.0",
        
        # Speech-to-Text & Text-to-Speech
        "faster-whisper>=0.9.0",
        "TTS>=0.20.0",
        
        # Audio Processing
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "numpy>=1.22.0",  # Compatible with TTS 0.22.0 which requires numpy==1.22.0 for Python 3.10
        "librosa>=0.10.0",
        "pydub>=0.25.1",
        
        # Web Framework (for API)
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        
        # Data Validation
        "pydantic>=2.0.0",
        "typing-extensions>=4.5.0",
        
        # Database
        "pymongo>=4.5.0",
        
        # HTTP & Networking
        "requests>=2.32.0",
        
        # Hugging Face Ecosystem (for model management)
        "huggingface-hub>=0.24.0",
        "safetensors>=0.4.0",
        "accelerate>=1.1.0",
        "datasets>=2.20.0",
        "tokenizers>=0.20.0",
        
        # Monitoring & Logging
        "psutil>=5.9.0",
        
        # Configuration
        "pyyaml>=6.0.0",
        "python-dotenv>=1.0.1",
    ],
    
    # Optional dependencies
    extras_require={
        "dev": [
            # Testing Framework
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            
            # Code Quality & Formatting
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
            "isort>=5.12.0",
            
            # Type Checking
            "types-requests>=2.31.0",
            "types-pyyaml>=6.0.12",
            
            # Development Tools
            "ipython>=8.12.0",
            "ipdb>=0.13.13",
        ],
    },
    
    # Entry points (console scripts)
    entry_points={
        "console_scripts": [
            "voice-platform=voice_platform.main:main",
            "voice-platform-setup-env=voice_platform.scripts.setup_env:main",
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
)
