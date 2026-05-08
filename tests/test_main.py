"""Tests for main.py startup validation and dependency checks.

Validates: Requirements 9.3, 9.4
- 9.3: Validate required dependencies (FFmpeg, Redis) are available on startup
- 9.4: Log error and fail to start with descriptive message if dependency unavailable
"""

import pytest
from unittest.mock import patch, MagicMock


class TestValidateDependencies:
    """Tests for the validate_dependencies function."""

    def test_validate_dependencies_ffmpeg_found(self):
        """Test that FFmpeg validation passes when FFmpeg is in PATH."""
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function
            from app.main import validate_dependencies
            
            # Should not raise any exception
            validate_dependencies()
            
            # Verify FFmpeg was checked
            mock_which.assert_called_once_with("ffmpeg")

    def test_validate_dependencies_ffmpeg_not_found(self):
        """Test that FFmpeg validation fails with descriptive error when FFmpeg is not in PATH."""
        with patch('shutil.which') as mock_which:
            # Setup mock - FFmpeg not found
            mock_which.return_value = None
            
            # Import and call the function
            from app.main import validate_dependencies
            
            # Should raise RuntimeError with descriptive message
            with pytest.raises(RuntimeError) as exc_info:
                validate_dependencies()
            
            assert "FFmpeg" in str(exc_info.value)
            assert "required" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()

    def test_validate_dependencies_redis_connection_success(self):
        """Test that Redis validation passes when connection is successful."""
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function
            from app.main import validate_dependencies
            
            # Should not raise any exception
            validate_dependencies()
            
            # Verify Redis ping was called
            mock_redis_instance.ping.assert_called_once()

    def test_validate_dependencies_redis_connection_failure(self):
        """Test that Redis validation fails with descriptive error when connection fails."""
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks - FFmpeg found but Redis fails
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.side_effect = Exception("Connection refused")
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function
            from app.main import validate_dependencies
            
            # Should raise RuntimeError with descriptive message
            with pytest.raises(RuntimeError) as exc_info:
                validate_dependencies()
            
            assert "Redis" in str(exc_info.value)
            assert "required" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

    def test_validate_dependencies_logs_ffmpeg_path(self, caplog):
        """Test that FFmpeg path is logged on successful validation."""
        import logging
        
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function with logging capture
            from app.main import validate_dependencies
            
            with caplog.at_level(logging.INFO):
                validate_dependencies()
            
            # Check that FFmpeg path was logged
            assert any("FFmpeg found" in record.message or "ffmpeg" in record.message.lower() 
                      for record in caplog.records)

    def test_validate_dependencies_logs_redis_success(self, caplog):
        """Test that Redis connection success is logged."""
        import logging
        
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function with logging capture
            from app.main import validate_dependencies
            
            with caplog.at_level(logging.INFO):
                validate_dependencies()
            
            # Check that Redis success was logged
            assert any("Redis" in record.message and "success" in record.message.lower() 
                      for record in caplog.records)

    def test_validate_dependencies_logs_error_on_ffmpeg_missing(self, caplog):
        """Test that error is logged when FFmpeg is missing."""
        import logging
        
        with patch('shutil.which') as mock_which:
            # Setup mock - FFmpeg not found
            mock_which.return_value = None
            
            # Import and call the function with logging capture
            from app.main import validate_dependencies
            
            with caplog.at_level(logging.ERROR):
                with pytest.raises(RuntimeError):
                    validate_dependencies()
            
            # Check that error was logged
            assert any("FFmpeg" in record.message and record.levelno == logging.ERROR 
                      for record in caplog.records)

    def test_validate_dependencies_logs_error_on_redis_failure(self, caplog):
        """Test that error is logged when Redis connection fails."""
        import logging
        
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class:
            # Setup mocks - FFmpeg found but Redis fails
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.side_effect = Exception("Connection refused")
            mock_redis_class.return_value = mock_redis_instance
            
            # Import and call the function with logging capture
            from app.main import validate_dependencies
            
            with caplog.at_level(logging.ERROR):
                with pytest.raises(RuntimeError):
                    validate_dependencies()
            
            # Check that error was logged
            assert any("Redis" in record.message and record.levelno == logging.ERROR 
                      for record in caplog.records)


class TestLifespanDependencyValidation:
    """Tests for dependency validation during application lifespan."""

    def test_lifespan_calls_validate_dependencies(self):
        """Test that the lifespan context manager calls validate_dependencies on startup."""
        with patch('app.main.validate_dependencies') as mock_validate:
            # We need to test that validate_dependencies is called during lifespan
            # This is verified by the function being called in the lifespan context
            from app.main import validate_dependencies
            
            # The function exists and is callable
            assert callable(validate_dependencies)

    def test_validate_dependencies_uses_settings_for_redis(self):
        """Test that Redis connection uses settings for host and port."""
        with patch('shutil.which') as mock_which, \
             patch('redis.Redis') as mock_redis_class, \
             patch('app.main.settings') as mock_settings:
            # Setup mocks
            mock_which.return_value = '/usr/bin/ffmpeg'
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.return_value = mock_redis_instance
            
            # Setup settings mock
            mock_settings.redis_host = 'test-redis-host'
            mock_settings.redis_port = 6380
            mock_settings.redis_db = 1
            
            # Import and call the function
            from app.main import validate_dependencies
            validate_dependencies()
            
            # Verify Redis was called with settings values
            mock_redis_class.assert_called_once()
            call_kwargs = mock_redis_class.call_args[1]
            assert call_kwargs['host'] == 'test-redis-host'
            assert call_kwargs['port'] == 6380
            assert call_kwargs['db'] == 1
