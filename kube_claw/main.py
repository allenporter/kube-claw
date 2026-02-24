import os
import asyncio
import logging
from kube_claw.agent import ClawAgent
from kube_claw.drivers.discord.communicator import DiscordCommunicator
from kube_claw.drivers.kubernetes.scheduler import KubernetesJobScheduler


async def main() -> None:
    """Main entrypoint for the KubeClaw agent service."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Load configuration from environment variables
    discord_token = os.environ.get("DISCORD_TOKEN")
    if not discord_token:
        logger.error("DISCORD_TOKEN is not set.")
        return

    # Initialize drivers
    # Note: These parameters should ideally come from configuration
    communicator = DiscordCommunicator(token=discord_token)
    scheduler = KubernetesJobScheduler(
        namespace=os.environ.get("KUBE_NAMESPACE", "default"),
        image_name=os.environ.get("AGENT_IMAGE_NAME", "kube-claw-agent:latest"),
    )

    # Initialize and run the main agent loop
    agent = ClawAgent(communicator=communicator, scheduler=scheduler)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
