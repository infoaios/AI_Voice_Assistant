"""
Cache Management Service

Handles HuggingFace model cache operations with proper Windows permission handling.
Decouples cache management from model loading logic.
"""
import os
import shutil
import time
import stat
from pathlib import Path
from typing import Optional, List
from platform import system


class CacheService:
    """
    Service for managing HuggingFace model caches with Windows permission handling.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache service.
        
        Args:
            cache_dir: Optional custom cache directory. Defaults to HuggingFace default.
        """
        if cache_dir:
            self.cache_base = cache_dir
        else:
            self.cache_base = Path.home() / ".cache"
        
        self.hf_cache = self.cache_base / "huggingface" / "hub"
        self.ctranslate_cache = self.cache_base / "ctranslate2"
        self.is_windows = system() == "Windows"
    
    def _normalize_model_name(self, model_id: str) -> str:
        """
        Normalize model ID for cache directory naming.
        
        Converts:
        - "openai/whisper-large-v3-turbo" -> "openai--whisper-large-v3-turbo"
        - "large-v3-turbo" -> "large-v3-turbo"
        
        Args:
            model_id: Model identifier (can be HuggingFace path or simple name)
            
        Returns:
            Normalized model name for cache directory
        """
        # Replace slashes with double dashes (HuggingFace convention)
        return model_id.replace('/', '--')
    
    def _fix_permissions(self, path: Path) -> bool:
        """
        Fix file permissions on Windows to allow deletion.
        
        Args:
            path: Path to file or directory
            
        Returns:
            True if permissions were fixed, False otherwise
        """
        if not self.is_windows or not path.exists():
            return True
        
        try:
            # On Windows, make files writable before deletion
            if path.is_file():
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            elif path.is_dir():
                # Recursively fix permissions for all files in directory
                for root, dirs, files in os.walk(path):
                    for d in dirs:
                        os.chmod(Path(root) / d, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                    for f in files:
                        os.chmod(Path(root) / f, stat.S_IWRITE | stat.S_IREAD)
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            return True
        except Exception as e:
            print(f"[CACHE] ⚠️  Could not fix permissions for {path}: {e}")
            return False
    
    def _safe_remove(self, path: Path, retries: int = 3, delay: float = 0.5) -> bool:
        """
        Safely remove a file or directory with retry logic and permission handling.
        
        Args:
            path: Path to remove
            retries: Number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            True if removal was successful, False otherwise
        """
        if not path.exists():
            return True
        
        # Fix permissions before attempting removal
        self._fix_permissions(path)
        
        for attempt in range(retries):
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                return True
            except PermissionError as e:
                if attempt < retries - 1:
                    print(f"[CACHE] ⚠️  Permission error (attempt {attempt + 1}/{retries}): {e}")
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                    self._fix_permissions(path)
                else:
                    print(f"[CACHE] ❌ Failed to remove {path} after {retries} attempts: {e}")
                    return False
            except Exception as e:
                print(f"[CACHE] ⚠️  Error removing {path}: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    return False
        
        return False
    
    def get_model_cache_path(self, model_id: str) -> Path:
        """
        Get the cache path for a given model ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Path to model cache directory
        """
        normalized_name = self._normalize_model_name(model_id)
        return self.hf_cache / f"models--{normalized_name}"
    
    def clear_model_cache(self, model_id: str) -> bool:
        """
        Clear cache for a specific model.
        
        Args:
            model_id: Model identifier to clear cache for
            
        Returns:
            True if cache was cleared successfully, False otherwise
        """
        model_cache = self.get_model_cache_path(model_id)
        
        if not model_cache.exists():
            return True  # Nothing to clear
        
        print(f"[CACHE] 🧹 Clearing cache for model: {model_id}")
        success = self._safe_remove(model_cache)
        
        if success:
            print(f"[CACHE] ✅ Cleared model cache: {model_cache}")
        else:
            print(f"[CACHE] ⚠️  Could not fully clear model cache: {model_cache}")
        
        return success
    
    def clear_corrupted_snapshots(self, model_id: str) -> bool:
        """
        Clear only corrupted snapshots for a model (more targeted cleanup).
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if any corrupted snapshots were found and cleared
        """
        model_cache = self.get_model_cache_path(model_id)
        
        if not model_cache.exists():
            return False
        
        snapshots_dir = model_cache / "snapshots"
        if not snapshots_dir.exists():
            return False
        
        cleared_any = False
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir():
                # Check for common corruption indicators
                model_bin = snapshot / "model.bin"
                config_json = snapshot / "config.json"
                
                # If snapshot exists but critical files are missing, it's corrupted
                if not model_bin.exists() or not config_json.exists():
                    print(f"[CACHE] ⚠️  Found corrupted snapshot: {snapshot.name}")
                    if self._safe_remove(snapshot):
                        print(f"[CACHE] ✅ Cleared corrupted snapshot")
                        cleared_any = True
        
        return cleared_any
    
    def clear_ctranslate_cache(self, model_id: Optional[str] = None) -> bool:
        """
        Clear CTranslate2 cache (used by faster-whisper).
        
        Args:
            model_id: Optional model ID to filter cache entries. If None, clears all Whisper-related caches.
            
        Returns:
            True if any caches were cleared
        """
        if not self.ctranslate_cache.exists():
            return False
        
        cleared_any = False
        search_terms = ["whisper", "distil"]
        
        if model_id:
            # Normalize model ID for search
            normalized = model_id.lower().replace('/', '-').replace('_', '-')
            search_terms.append(normalized)
        
        try:
            for item in list(self.ctranslate_cache.iterdir()):
                item_name_lower = item.name.lower()
                if any(term in item_name_lower for term in search_terms):
                    if self._safe_remove(item):
                        print(f"[CACHE] ✅ Cleared ctranslate2 cache: {item.name}")
                        cleared_any = True
        except Exception as e:
            print(f"[CACHE] ⚠️  Error clearing ctranslate2 cache: {e}")
        
        return cleared_any
    
    def clear_all_model_caches(self, model_id: str) -> bool:
        """
        Clear all caches related to a model (HuggingFace + CTranslate2).
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if all caches were cleared successfully
        """
        print(f"[CACHE] 🧹 Clearing all caches for model: {model_id}")
        
        # Clear HuggingFace cache
        hf_success = self.clear_model_cache(model_id)
        
        # Clear CTranslate2 cache
        ctranslate_success = self.clear_ctranslate_cache(model_id)
        
        # Also check for any remaining references in HF cache
        if self.hf_cache.exists():
            normalized_name = self._normalize_model_name(model_id)
            for item in list(self.hf_cache.iterdir()):
                if normalized_name in item.name and item.is_dir():
                    if self._safe_remove(item):
                        print(f"[CACHE] ✅ Cleared remaining cache: {item.name}")
        
        return hf_success or ctranslate_success
    
    def get_cache_size(self, model_id: str) -> Optional[int]:
        """
        Get the size of model cache in bytes.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Cache size in bytes, or None if cache doesn't exist
        """
        model_cache = self.get_model_cache_path(model_id)
        
        if not model_cache.exists():
            return None
        
        total_size = 0
        try:
            for root, dirs, files in os.walk(model_cache):
                for f in files:
                    file_path = Path(root) / f
                    if file_path.exists():
                        total_size += file_path.stat().st_size
        except Exception:
            return None
        
        return total_size



