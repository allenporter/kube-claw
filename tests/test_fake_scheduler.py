import asyncio
import pytest
from kube_claw.drivers.fake.scheduler import FakeJobScheduler


@pytest.mark.asyncio
async def test_fake_scheduler_lifecycle():
    # Set transition_delay to 0.1 for faster tests
    scheduler = FakeJobScheduler(transition_delay=0.1)

    # Schedule a job
    job_id = await scheduler.schedule_job("test_task", {"foo": "bar"})
    assert job_id.startswith("fake-")

    # Initial status should be pending or already running
    status = await scheduler.get_job_status(job_id)
    assert status in ["pending", "running"]

    # Wait for status to become 'running' (0.5s in code)
    # We should wait a bit longer to be safe
    await asyncio.sleep(0.6)
    status = await scheduler.get_job_status(job_id)
    assert status == "running"

    # Wait for status to become 'completed' (transition_delay=0.1)
    await asyncio.sleep(0.2)
    status = await scheduler.get_job_status(job_id)
    assert status == "completed"


@pytest.mark.asyncio
async def test_fake_scheduler_cancel():
    scheduler = FakeJobScheduler(transition_delay=1.0)
    job_id = await scheduler.schedule_job("cancel_task", {})

    await scheduler.cancel_job(job_id)
    status = await scheduler.get_job_status(job_id)
    assert status == "failed"


@pytest.mark.asyncio
async def test_fake_scheduler_get_all_jobs():
    scheduler = FakeJobScheduler()
    job_id1 = await scheduler.schedule_job("task1", {})
    job_id2 = await scheduler.schedule_job("task2", {})

    all_jobs = await scheduler.get_all_jobs()
    assert len(all_jobs) == 2
    assert job_id1 in all_jobs
    assert job_id2 in all_jobs


@pytest.mark.asyncio
async def test_fake_scheduler_not_found():
    scheduler = FakeJobScheduler()
    status = await scheduler.get_job_status("non-existent")
    assert status == "not_found"
