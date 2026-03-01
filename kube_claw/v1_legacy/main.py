import os
import asyncio
import logging
from kube_claw.v1_legacy.agent import ClawAgent
from kube_claw.v1_legacy.drivers.discord.communicator import DiscordCommunicator
from kube_claw.v1_legacy.drivers.kubernetes.scheduler import KubernetesJobScheduler
from kube_claw.v1_legacy.drivers.fake.communicator import FakeCommunicator
from kube_claw.v1_legacy.drivers.fake.scheduler import FakeJobScheduler


async def main() -> None:
    """Main entrypoint for the KubeClaw agent service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Switch to 'fake' drivers for local development if CLAW_ENV=dev
    is_dev = os.environ.get("CLAW_ENV", "prod").lower() == "dev"

    if is_dev:
        logger.info("Running in DEV mode with fake drivers...")
        communicator = FakeCommunicator()
        scheduler = FakeJobScheduler(transition_delay=5.0)
    else:
        # Load configuration from environment variables for production
        discord_token = os.environ.get("DISCORD_TOKEN")
        if not discord_token:
            logger.error("DISCORD_TOKEN is not set.")
            return

        # Initialize drivers
        communicator = DiscordCommunicator(token=discord_token)
        scheduler = KubernetesJobScheduler(
            namespace=os.environ.get("KUBE_NAMESPACE", "default"),
            image_name=os.environ.get("AGENT_IMAGE_NAME", "kube-claw-agent:latest"),
        )

    # Initialize and run the main agent loop
    agent = ClawAgent(communicator=communicator, scheduler=scheduler)
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
