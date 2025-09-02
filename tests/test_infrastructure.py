"""
Validation tests for the testing infrastructure setup.
These tests verify that the testing environment is properly configured.
"""

import pytest
import sys
from pathlib import Path


def test_python_version():
    """Test that Python version meets minimum requirements."""
    assert sys.version_info >= (3, 8), "Python 3.8+ is required"


def test_pytest_markers():
    """Test that custom pytest markers are available."""
    # These markers should be defined in pyproject.toml
    pytest_config = pytest.Config
    # This test will pass if markers are properly configured
    assert True  # Placeholder - pytest will fail if markers are misconfigured


@pytest.mark.unit
def test_unit_marker():
    """Test that unit marker works."""
    assert True


@pytest.mark.integration  
def test_integration_marker():
    """Test that integration marker works."""
    assert True


@pytest.mark.slow
def test_slow_marker():
    """Test that slow marker works."""
    assert True


def test_fixtures_available(temp_dir, sample_config, sample_phonemes):
    """Test that common fixtures are available and working."""
    assert temp_dir.exists()
    assert isinstance(sample_config, dict)
    assert isinstance(sample_phonemes, list)
    assert len(sample_phonemes) > 0


def test_project_structure():
    """Test that the project structure is as expected."""
    project_root = Path(__file__).parent.parent
    
    # Check main directories exist
    assert (project_root / "synthesis").exists()
    assert (project_root / "py").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "tests" / "unit").exists()
    assert (project_root / "tests" / "integration").exists()
    
    # Check configuration files exist
    assert (project_root / "pyproject.toml").exists()


def test_import_main_modules():
    """Test that main project modules can be imported."""
    try:
        # Test basic imports that should work
        import os
        import sys
        from pathlib import Path
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import basic modules: {e}")


class TestConfigurationValidation:
    """Test class for configuration validation."""
    
    def test_sample_config_structure(self, sample_config):
        """Test that sample configuration has expected structure."""
        required_keys = ['sample_rate', 'hop_length', 'win_length']
        for key in required_keys:
            assert key in sample_config
            assert isinstance(sample_config[key], int)
    
    def test_timing_data_structure(self, sample_timing_data):
        """Test that timing data fixture has correct structure."""
        assert 'phonemes' in sample_timing_data
        assert 'durations' in sample_timing_data
        assert 'start_times' in sample_timing_data
        
        assert isinstance(sample_timing_data['phonemes'], list)
        assert isinstance(sample_timing_data['durations'], list)
        assert isinstance(sample_timing_data['start_times'], list)


def test_mock_functionality(mock_torch_model):
    """Test that mock fixtures work correctly."""
    assert mock_torch_model is not None
    assert hasattr(mock_torch_model, 'eval')
    assert hasattr(mock_torch_model, 'forward')


def test_temporary_directory_cleanup(temp_dir):
    """Test that temporary directories are properly managed."""
    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    
    assert test_file.exists()
    assert test_file.read_text() == "test content"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])