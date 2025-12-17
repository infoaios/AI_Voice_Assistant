#!/usr/bin/env python3
"""
Environment Setup Script (Installable Version)

This is the installable version of the environment setup script.
It can be called via: voice-platform-setup-env

The standalone version is in: env/setup_env.py
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, check=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=check
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode


def check_cuda_available():
    """Check if CUDA is available via PyTorch"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        # PyTorch not installed, try nvidia-smi
        stdout, stderr, code = run_command("nvidia-smi", check=False)
        return code == 0


def get_gpu_name():
    """Get GPU name from nvidia-smi"""
    stdout, stderr, code = run_command("nvidia-smi --query-gpu=name --format=csv,noheader", check=False)
    if code == 0 and stdout:
        return stdout.split('\n')[0].strip()
    return None


def detect_hardware():
    """Detect hardware configuration"""
    print("🔍 Detecting hardware configuration...")
    
    has_cuda = check_cuda_available()
    
    if not has_cuda:
        print("❌ No GPU detected (or CUDA not available)")
        return "cpu"
    
    gpu_name = get_gpu_name()
    if not gpu_name:
        print("⚠️  GPU detected but could not determine model")
        return "gpu3080"  # Default to 3080 config
    
    print(f"✅ GPU detected: {gpu_name}")
    
    gpu_name_lower = gpu_name.lower()
    
    if "3080" in gpu_name_lower:
        print("✅ RTX 3080 detected")
        return "gpu3080"
    elif "5080" in gpu_name_lower or "50" in gpu_name_lower:
        print("✅ RTX 5080 (or newer) detected")
        return "gpu5080"
    else:
        print(f"⚠️  Unknown GPU model: {gpu_name}")
        print("   Using RTX 3080 configuration (CUDA 11.8 compatible)")
        return "gpu3080"


def create_environment(env_type):
    """Create conda environment from YAML file"""
    env_files = {
        "cpu": "cpu_env.yml",
        "gpu3080": "gpu3080_env.yml",
        "gpu5080": "gpu5080_env.yml"
    }
    
    env_names = {
        "cpu": "voice_assistant_cpu",
        "gpu3080": "voice_assistant_gpu3080",
        "gpu5080": "voice_assistant_gpu5080"
    }
    
    if env_type not in env_files:
        print(f"❌ Unknown environment type: {env_type}")
        return False
    
    env_file = env_files[env_type]
    env_name = env_names[env_type]
    
    # Find env directory relative to project root
    # This script is in scripts/, so project root is parent, then env/ is in project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_dir = project_root / "env"
    env_path = env_dir / env_file
    
    if not env_path.exists():
        print(f"❌ Environment file not found: {env_path}")
        print(f"   Looking for: {env_path}")
        return False
    
    print(f"\n📦 Creating environment: {env_name}")
    print(f"   Using file: {env_file}")
    
    # Check if conda is available
    stdout, stderr, code = run_command("conda --version", check=False)
    if code != 0:
        print("❌ Conda not found. Please install Anaconda or Miniconda.")
        return False
    
    # Create environment
    cmd = f'conda env create -f "{env_path}"'
    print(f"\n🔧 Running: {cmd}")
    print("   This may take several minutes...\n")
    
    stdout, stderr, code = run_command(cmd, check=False)
    
    if code == 0:
        print(f"\n✅ Environment '{env_name}' created successfully!")
        print(f"\n📝 Next steps:")
        print(f"   1. Activate environment: conda activate {env_name}")
        print(f"   2. Verify installation: python -c \"import torch; print('CUDA:', torch.cuda.is_available())\"")
        print(f"   3. Run application: python main.py")
        return True
    else:
        print(f"\n❌ Failed to create environment")
        print(f"   Error: {stderr}")
        print(f"\n💡 Troubleshooting:")
        print(f"   - Check conda installation: conda --version")
        print(f"   - Try manual creation: conda env create -f {env_path}")
        return False


def main():
    """Main function"""
    print("=" * 70)
    print("🍽️  Restaurant AI Voice Assistant - Environment Setup")
    print("=" * 70)
    print()
    
    # Detect hardware
    env_type = detect_hardware()
    
    print(f"\n📋 Selected environment: {env_type}")
    print()
    
    # Ask for confirmation
    response = input(f"Create '{env_type}' environment? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Setup cancelled")
        return
    
    # Create environment
    success = create_environment(env_type)
    
    if success:
        print("\n" + "=" * 70)
        print("✅ Setup complete!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ Setup failed. Please check errors above.")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()

