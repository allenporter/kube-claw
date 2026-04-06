import asyncio
import logging
import sys
from pathlib import Path
from adk_claw.host.host import ClawHost
from adk_claw.domain.models import EventType

# Configure logging to see the lane-based queuing in action
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("stress-test")

async def run_lane_task(host: ClawHost, lane_id: int, session_id: str, results: list):
    """Simulate a single user message in a specific lane."""
    message = f"Task {lane_id}: Echo 'Start {lane_id}', wait 1s, echo 'End {lane_id}'"
    logger.info(f"🚀 Sending Task {lane_id} to lane {session_id}")
    
    events_received = []
    try:
        # We use the same channel/author to force the SAME lane key
        async for event in host.handle_message(
            text=message,
            protocol="stress-test",
            channel_id="stress-channel",
            author_id="stress-author",
        ):
            if event.type == EventType.TOKEN:
                events_received.append(event.content)
            elif event.type == EventType.ERROR:
                logger.error(f"❌ Task {lane_id} failed: {event.content}")
                results.append((lane_id, "ERROR", event.content))
                return

        logger.info(f"✅ Task {lane_id} completed successfully")
        results.append((lane_id, "SUCCESS", "".join(events_received)))
    except Exception as e:
        logger.exception(f"💥 Task {lane_id} crashed")
        results.append((lane_id, "CRASH", str(e)))

async def main():
    # Setup workspace
    workspace = Path("/tmp/claw-stress-test")
    workspace.mkdir(exist_ok=True)
    
    # Initialize Host
    from adk_claw.config import ClawConfig, AgentConfig
    # Use gemini-2.5-flash which is confirmed to exist and be stable
    config = ClawConfig(agent=AgentConfig(model="gemini-2.5-flash"))
    host = ClawHost(workspace_path=str(workspace), config=config)
    
    # Setup the binding
    await host.setup_default_binding(
        protocol="stress-test",
        channel_id="stress-channel",
        author_id="stress-author",
    )
    
    session_id = "stress-session-1"
    results = []
    
    # THE HAMMER: Launch 5 tasks simultaneously for the SAME lane
    # If queuing works, they should finish one by one (serialized)
    # If queuing is broken, we'll see 'last_update_time' errors immediately
    tasks = [
        run_lane_task(host, i, session_id, results) 
        for i in range(1, 6)
    ]
    
    logger.info("🔥 Launching 5 concurrent tasks on the same lane...")
    await asyncio.gather(*tasks)
    
    # Analyze results
    successes = [r for r in results if r[1] == "SUCCESS"]
    errors = [r for r in results if r[1] == "ERROR"]
    crashes = [r for r in results if r[1] == "CRASH"]
    
    print("\n" + "="*40)
    print("STRESS TEST SUMMARY")
    print("="*40)
    print(f"Total Tasks: {len(results)}")
    print(f"Successes:   {len(successes)}")
    print(f"Errors:      {len(errors)}")
    print(f"Crashes:     {len(crashes)}")
    
    if errors:
        print("\nFirst Error Detail:")
        print(errors[0][2])
        sys.exit(1)
    
    if len(successes) == len(results):
        print("\n🏆 PASS: All tasks serialized and completed without session conflicts.")
        sys.exit(0)
    else:
        print("\n❌ FAIL: Some tasks did not complete as expected.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
