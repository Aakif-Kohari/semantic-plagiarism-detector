import pytest
import time
from src.utils.processing_time import ProcessingTimer

def test_timer_initialization():
    timer = ProcessingTimer()
    assert timer.durations == []
    assert timer._active_timers == 0

def test_single_time_block(monkeypatch):
    timer = ProcessingTimer()
    
    times = [0.0, 1.5]
    def mock_perf_counter():
        return times.pop(0)
    
    monkeypatch.setattr(time, 'perf_counter', mock_perf_counter)
    
    with timer.time_block():
        assert timer._active_timers == 1
        
    assert timer._active_timers == 0
    assert len(timer.durations) == 1
    assert timer.durations[0] == 1.5

def test_nested_time_blocks(monkeypatch):
    timer = ProcessingTimer()
    
    # Enter outer (0.0), enter inner (1.0), exit inner (2.0), exit outer (3.5)
    times = [0.0, 1.0, 2.0, 3.5]
    def mock_perf_counter():
        return times.pop(0)
    
    monkeypatch.setattr(time, 'perf_counter', mock_perf_counter)
    
    with timer.time_block():
        assert timer._active_timers == 1
        with timer.time_block():
            assert timer._active_timers == 2
        assert timer._active_timers == 1
        
    assert timer._active_timers == 0
    assert len(timer.durations) == 2
    # Inner duration: 2.0 - 1.0 = 1.0
    assert timer.durations[0] == 1.0
    # Outer duration: 3.5 - 0.0 = 3.5
    assert timer.durations[1] == 3.5

def test_exception_handling_in_timer(monkeypatch):
    timer = ProcessingTimer()
    
    times = [0.0, 1.2]
    def mock_perf_counter():
        return times.pop(0)
    
    monkeypatch.setattr(time, 'perf_counter', mock_perf_counter)
    
    with pytest.raises(ValueError, match="Test error"):
        with timer.time_block():
            assert timer._active_timers == 1
            raise ValueError("Test error")
            
    assert timer._active_timers == 0
    assert len(timer.durations) == 1
    assert timer.durations[0] == 1.2

def test_nested_timers_with_inner_exception(monkeypatch):
    timer = ProcessingTimer()
    
    # Enter outer (0.0), enter inner (1.0), exit inner exception (2.0), exit outer exception (3.0)
    times = [0.0, 1.0, 2.0, 3.0]
    def mock_perf_counter():
        return times.pop(0)
    
    monkeypatch.setattr(time, 'perf_counter', mock_perf_counter)
    
    with pytest.raises(RuntimeError):
        with timer.time_block():
            with timer.time_block():
                raise RuntimeError("Failed")
                
    assert timer._active_timers == 0
    assert len(timer.durations) == 2
    assert timer.durations[0] == 1.0
    assert timer.durations[1] == 3.0
