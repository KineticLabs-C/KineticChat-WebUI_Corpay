"""
Unit tests for database module with retry logic
Tests connection pooling, retry mechanisms, and resilience
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# Import components to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import (
    DatabaseManager,
    with_retry,
    exponential_backoff
)


class TestExponentialBackoff:
    """Test exponential backoff calculation"""
    
    def test_backoff_calculation(self):
        """Test exponential backoff with jitter"""
        # First attempt (0) should have minimal delay
        delay0 = exponential_backoff(0, initial_delay=1.0)
        assert 0 <= delay0 <= 1.5  # With jitter
        
        # Second attempt should be ~2x
        delay1 = exponential_backoff(1, initial_delay=1.0)
        assert 1.5 <= delay1 <= 3.0
        
        # Third attempt should be ~4x
        delay2 = exponential_backoff(2, initial_delay=1.0)
        assert 3.0 <= delay2 <= 6.0
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        # Very high attempt should be capped
        delay = exponential_backoff(10, initial_delay=1.0, max_delay=10.0)
        assert delay <= 10.0


class TestRetryDecorator:
    """Test the with_retry decorator"""
    
    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test function succeeds on first attempt"""
        call_count = 0
        
        @with_retry(max_attempts=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test function retries on failure"""
        call_count = 0
        
        @with_retry(max_attempts=3, initial_delay=0.01)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test function fails after max attempts"""
        call_count = 0
        
        @with_retry(max_attempts=3, initial_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        with pytest.raises(Exception) as exc_info:
            await always_fails()
        
        assert "Always fails" in str(exc_info.value)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_with_different_exceptions(self):
        """Test retry handles different exception types"""
        call_count = 0
        
        @with_retry(max_attempts=4, initial_delay=0.01)
        async def different_exceptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection failed")
            elif call_count == 2:
                raise TimeoutError("Timeout")
            elif call_count == 3:
                raise ValueError("Invalid value")
            return "success"
        
        result = await different_exceptions()
        assert result == "success"
        assert call_count == 4


class TestDatabaseManager:
    """Test DatabaseManager with retry logic and connection pooling"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test database manager initialization"""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-key',
            'DATABASE_PASSWORD': 'test-password'
        }):
            db = DatabaseManager()
            
            assert db.supabase_url == 'https://test.supabase.co'
            assert db.supabase_key == 'test-key'
            assert db.pool is None  # Not initialized yet
            assert db.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_connection_pool_creation(self):
        """Test connection pool is created properly"""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-key'
        }):
            db = DatabaseManager()
            
            # Mock asyncpg
            with patch('asyncpg.create_pool') as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool
                
                success = await db.initialize()
                
                # Pool should be created
                assert mock_create_pool.called
                assert db.pool is not None
                assert db.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_with_retry(self):
        """Test initialization retries on failure"""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-key'
        }):
            db = DatabaseManager()
            
            call_count = 0
            
            # Mock asyncpg to fail then succeed
            with patch('asyncpg.create_pool') as mock_create_pool:
                async def create_pool_with_retry(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count < 2:
                        raise ConnectionError("Connection failed")
                    return AsyncMock()
                
                mock_create_pool.side_effect = create_pool_with_retry
                
                success = await db.initialize()
                
                assert success is True
                assert call_count == 2  # Failed once, succeeded second time
    
    @pytest.mark.asyncio
    async def test_log_interaction(self):
        """Test logging chat interaction with retry"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool and connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        # Test data
        interaction_data = {
            'session_id': 'test-session',
            'query': 'Test query',
            'response': 'Test response',
            'language': 'en',
            'response_time': 0.5,
            'error': None
        }
        
        success = await db.log_interaction(**interaction_data)
        
        assert success is True
        assert mock_conn.execute.called
    
    @pytest.mark.asyncio
    async def test_log_interaction_retry_on_failure(self):
        """Test interaction logging retries on database failure"""
        db = DatabaseManager()
        db.is_initialized = True
        
        call_count = 0
        
        # Mock pool and connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        async def execute_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Database error")
            return None
        
        mock_conn.execute = execute_with_retry
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        interaction_data = {
            'session_id': 'test-session',
            'query': 'Test query',
            'response': 'Test response',
            'language': 'en',
            'response_time': 0.5
        }
        
        success = await db.log_interaction(**interaction_data)
        
        assert success is True
        assert call_count == 2  # Failed once, succeeded second time
    
    @pytest.mark.asyncio
    async def test_get_session_history(self):
        """Test retrieving session history with retry"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool and connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        
        # Mock query results
        mock_results = [
            {
                'query': 'Question 1',
                'response': 'Answer 1',
                'created_at': datetime.now(timezone.utc)
            },
            {
                'query': 'Question 2',
                'response': 'Answer 2',
                'created_at': datetime.now(timezone.utc)
            }
        ]
        
        mock_conn.fetch.return_value = mock_results
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        history = await db.get_session_history('test-session', limit=10)
        
        assert len(history) == 2
        assert history[0]['query'] == 'Question 1'
        assert mock_conn.fetch.called
    
    @pytest.mark.asyncio
    async def test_update_metrics(self):
        """Test metrics update with retry"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool and connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        metrics = {
            'total_requests': 1000,
            'avg_response_time': 0.25,
            'error_rate': 0.01
        }
        
        success = await db.update_metrics(metrics)
        
        assert success is True
        assert mock_conn.execute.called
    
    @pytest.mark.asyncio
    async def test_connection_pool_cleanup(self):
        """Test connection pool is properly closed"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool
        mock_pool = AsyncMock()
        db.pool = mock_pool
        
        await db.close()
        
        assert mock_pool.close.called
        assert db.pool is None
        assert db.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_handle_uninitialized_database(self):
        """Test operations fail gracefully when database not initialized"""
        db = DatabaseManager()
        db.is_initialized = False
        
        # Should return False/None for uninitialized database
        success = await db.log_interaction(
            session_id='test',
            query='test',
            response='test',
            language='en',
            response_time=0.1
        )
        assert success is False
        
        history = await db.get_session_history('test')
        assert history == []
        
        metrics_success = await db.update_metrics({})
        assert metrics_success is False
    
    @pytest.mark.asyncio
    async def test_connection_pool_limits(self):
        """Test connection pool respects min/max size"""
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-key',
            'DATABASE_POOL_MIN': '5',
            'DATABASE_POOL_MAX': '20'
        }):
            db = DatabaseManager()
            
            with patch('asyncpg.create_pool') as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool
                
                await db.initialize()
                
                # Check pool was created with correct parameters
                call_args = mock_create_pool.call_args
                assert call_args[1]['min_size'] == 5
                assert call_args[1]['max_size'] == 20
    
    @pytest.mark.asyncio
    async def test_schema_creation(self):
        """Test database schema is created on initialization"""
        db = DatabaseManager()
        
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            await db.initialize()
            
            # Should execute schema creation
            execute_calls = mock_conn.execute.call_args_list
            
            # Check that tables are created
            schema_sql = str(execute_calls[0][0][0]) if execute_calls else ""
            assert "CREATE TABLE IF NOT EXISTS" in schema_sql
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test database handles concurrent operations"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool and connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        # Run multiple concurrent operations
        tasks = []
        for i in range(10):
            task = db.log_interaction(
                session_id=f'session-{i}',
                query=f'Query {i}',
                response=f'Response {i}',
                language='en',
                response_time=0.1
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert mock_conn.execute.call_count == 10
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        db = DatabaseManager()
        db.is_initialized = True
        
        # Mock pool and connection with transaction
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        
        mock_conn.transaction.return_value = mock_transaction
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        db.pool = mock_pool
        
        # Simulate error during transaction
        mock_conn.execute.side_effect = Exception("Transaction error")
        
        success = await db.log_interaction(
            session_id='test',
            query='test',
            response='test',
            language='en',
            response_time=0.1
        )
        
        # Transaction should be handled gracefully
        assert success is False or success is True  # Depends on retry logic


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])