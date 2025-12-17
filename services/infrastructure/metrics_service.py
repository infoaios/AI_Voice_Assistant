"""
Metrics Service

Collection and reporting of application metrics.
"""

from typing import Dict, Optional
from collections import defaultdict
import time


class MetricsService:
    """
    Metrics collection and reporting service.
    
    Provides methods to track and report application metrics.
    """
    
    def __init__(self):
        """Initialize metrics service"""
        self._metrics = defaultdict(float)
        self._counts = defaultdict(int)
        self._timings = defaultdict(list)
    
    def increment(self, metric_name: str, value: int = 1):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to increment by (default: 1)
        """
        self._counts[metric_name] += value
    
    def record(self, metric_name: str, value: float):
        """
        Record a value metric.
        
        Args:
            metric_name: Name of the metric
            value: Value to record
        """
        self._metrics[metric_name] = value
    
    def start_timer(self, metric_name: str) -> float:
        """
        Start a timer for a metric.
        
        Args:
            metric_name: Name of the timing metric
            
        Returns:
            Start time (can be used with end_timer)
        """
        start_time = time.time()
        return start_time
    
    def end_timer(self, metric_name: str, start_time: float):
        """
        End a timer and record the duration.
        
        Args:
            metric_name: Name of the timing metric
            start_time: Start time returned from start_timer
        """
        duration = time.time() - start_time
        self._timings[metric_name].append(duration)
    
    def get_metric(self, metric_name: str) -> Optional[float]:
        """
        Get a metric value.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Metric value or None if not found
        """
        if metric_name in self._metrics:
            return self._metrics[metric_name]
        if metric_name in self._counts:
            return self._counts[metric_name]
        return None
    
    def get_timing_stats(self, metric_name: str) -> Optional[Dict[str, float]]:
        """
        Get timing statistics for a metric.
        
        Args:
            metric_name: Name of the timing metric
            
        Returns:
            Dictionary with min, max, avg, count or None if not found
        """
        if metric_name not in self._timings or not self._timings[metric_name]:
            return None
        
        timings = self._timings[metric_name]
        return {
            'min': min(timings),
            'max': max(timings),
            'avg': sum(timings) / len(timings),
            'count': len(timings)
        }
    
    def get_all_metrics(self) -> Dict[str, any]:
        """
        Get all metrics.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'metrics': dict(self._metrics),
            'counts': dict(self._counts),
            'timings': {k: self.get_timing_stats(k) for k in self._timings.keys()}
        }
    
    def reset(self):
        """Reset all metrics"""
        self._metrics.clear()
        self._counts.clear()
        self._timings.clear()

