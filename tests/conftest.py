import os
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_wav_path(temp_dir: Path) -> Path:
    """Create a sample WAV file path (file not actually created)."""
    return temp_dir / "sample.wav"


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide a sample configuration dictionary."""
    return {
        "sample_rate": 22050,
        "hop_length": 256,
        "win_length": 1024,
        "n_fft": 1024,
        "f0_floor": 71,
        "f0_ceil": 800,
    }


@pytest.fixture
def mock_hydra_config():
    """Mock Hydra configuration for testing."""
    mock_config = {
        'sample_rate': 22050,
        'hop_length': 256,
        'model_path': '/tmp/model.pth'
    }
    return mock_config


@pytest.fixture
def mock_torch_model():
    """Mock PyTorch model for testing."""
    mock_model = Mock()
    mock_model.eval.return_value = None
    mock_model.forward.return_value = Mock()
    return mock_model


@pytest.fixture
def sample_phonemes() -> list:
    """Sample phoneme sequence for testing."""
    return ['sil', 'k', 'o', 'n', 'n', 'i', 'ch', 'i', 'w', 'a', 'sil']


@pytest.fixture
def sample_timing_data() -> Dict[str, Any]:
    """Sample timing data for testing."""
    return {
        'phonemes': ['sil', 'k', 'o', 'sil'],
        'durations': [0.1, 0.2, 0.3, 0.1],
        'start_times': [0.0, 0.1, 0.3, 0.6]
    }


@pytest.fixture
def mock_nnsvs_model():
    """Mock NNSVS model for testing."""
    mock_model = Mock()
    mock_model.predict.return_value = Mock()
    return mock_model


@pytest.fixture
def sample_ust_data() -> Dict[str, Any]:
    """Sample UST (UTAU Sequence Text) data for testing."""
    return {
        'version': '1.20',
        'project_name': 'test_project',
        'output_file': 'test.wav',
        'cache_dir': 'test_cache',
        'tool1': 'wavtool.exe',
        'tool2': 'resampler.exe',
        'notes': []
    }


@pytest.fixture
def cleanup_files():
    """Fixture to clean up test files after tests."""
    files_to_cleanup = []
    
    def add_file(filepath: str):
        files_to_cleanup.append(filepath)
    
    yield add_file
    
    # Cleanup
    for filepath in files_to_cleanup:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables and cleanup."""
    # Set test environment variables
    old_env = os.environ.copy()
    os.environ['TESTING'] = '1'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(old_env)


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests") 
    config.addinivalue_line("markers", "slow: Slow running tests")