# tests/integration/test_utils.py
import pytest

from tests.integration.utils import wait_for_indexing


class TestWaitForIndexing:
    async def test_calls_check_function(self):
        call_count = 0

        async def check():
            nonlocal call_count
            call_count += 1
            return True

        await wait_for_indexing(check, timeout=1.0)
        assert call_count >= 1

    async def test_retries_until_success(self):
        attempts = 0

        async def check():
            nonlocal attempts
            attempts += 1
            return attempts >= 3

        await wait_for_indexing(check, timeout=5.0, interval=0.1)
        assert attempts == 3

    async def test_raises_on_timeout(self):
        async def check():
            return False

        with pytest.raises(TimeoutError):
            await wait_for_indexing(check, timeout=0.2, interval=0.1)


class TestInitializeMattermost:
    def test_returns_test_environment(self):
        # This test is skipped without Docker
        # Actual testing happens in conftest integration
        pytest.skip("Requires Docker - tested via conftest")
