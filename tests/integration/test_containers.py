# tests/integration/test_containers.py
import pytest

from tests.integration.utils import setup_docker_host


DOCKER_AVAILABLE = setup_docker_host()


pytestmark = pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")


class TestMattermostContainer:
    def test_creates_with_default_image(self):
        from tests.integration.containers import MattermostContainer

        container = MattermostContainer()
        assert "mattermost/mattermost-enterprise-edition" in container.image

    def test_creates_with_custom_image(self):
        from tests.integration.containers import MattermostContainer

        container = MattermostContainer("mattermost/mattermost-team-edition:10.0")
        assert "10.0" in container.image

    def test_exposes_port_8065(self):
        from tests.integration.containers import MattermostContainer

        container = MattermostContainer()
        assert 8065 in container.ports
