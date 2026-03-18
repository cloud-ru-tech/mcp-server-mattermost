# tests/integration/containers.py
"""Testcontainers setup for Mattermost integration tests."""

from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy


class MattermostContainer(DockerContainer):
    """Mattermost server container for integration tests.

    Requires PostgreSQL container to be started first.
    Uses Mattermost Team Edition image.
    """

    MATTERMOST_PORT = 8065

    def __init__(self, image: str = "mattermost/mattermost-enterprise-edition:release-11"):
        super().__init__(image)
        self.with_exposed_ports(self.MATTERMOST_PORT)

    def configure(self, postgres_dsn: str) -> "MattermostContainer":
        """Configure Mattermost with PostgreSQL connection.

        Args:
            postgres_dsn: PostgreSQL connection string from PostgresContainer

        Returns:
            Self for method chaining
        """
        self.with_env("MM_SQLSETTINGS_DRIVERNAME", "postgres")
        self.with_env("MM_SQLSETTINGS_DATASOURCE", postgres_dsn)
        self.with_env("MM_SERVICESETTINGS_SITEURL", f"http://localhost:{self.MATTERMOST_PORT}")
        self.with_env("MM_SERVICESETTINGS_ENABLELOCALMODE", "true")
        self.with_env("MM_SERVICESETTINGS_ENABLELOCALMODESETROLEPREFIX", "true")
        # Disable telemetry for faster startup
        self.with_env("MM_LOGSETTINGS_ENABLEDIAGNOSTICS", "false")
        self.with_env("MM_SERVICESETTINGS_ENABLEDEVELOPER", "true")
        # Enable bot account creation for integration tests
        self.with_env("MM_SERVICESETTINGS_ENABLEBOTACCOUNTCREATION", "true")
        return self

    def start(self) -> "MattermostContainer":
        """Start container and wait for Mattermost to be ready.

        Returns:
            Self for method chaining
        """
        self.waiting_for(LogMessageWaitStrategy("Server is listening").with_startup_timeout(120))
        super().start()
        return self

    def get_base_url(self) -> str:
        """Get Mattermost server URL.

        Returns:
            Base URL for API calls (e.g., http://localhost:32768)
        """
        host = self.get_container_host_ip()
        port = self.get_exposed_port(self.MATTERMOST_PORT)
        return f"http://{host}:{port}"
