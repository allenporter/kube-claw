import os
from typing import Any, Dict
from kube_claw.core.base import JobScheduler


class KubernetesJobScheduler(JobScheduler):
    """
    JobScheduler implementation using Kubernetes Jobs.
    Uses the Kubernetes Python Client to interact with the cluster.
    """

    def __init__(
        self, namespace: str = "default", image_name: str = "kube-claw-agent:latest"
    ):
        self.namespace = namespace
        self.image_name = image_name
        # Lazy initialization of Kubernetes client is better for testing/standalone use
        self._batch_v1 = None

    @property
    def batch_v1(self) -> Any:
        if self._batch_v1 is None:
            from kubernetes import client, config

            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
            self._batch_v1 = client.BatchV1Api()
        return self._batch_v1

    async def schedule_job(self, task: str, context: Dict[str, Any]) -> str:
        """
        Schedules a Kubernetes Job to execute a task.
        """
        from kubernetes import client

        job_id = f"kube-claw-{os.urandom(4).hex()}"

        # Define the Kubernetes Job object
        # Note: This is a placeholder for actual job definition logic.
        # It will need to include container specs, volume mounts (PVCs), etc.
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(name=job_id),
            spec=client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="agent",
                                image=self.image_name,
                                command=["python", "-m", "kube_claw.agent_entrypoint"],
                                env=[
                                    client.V1EnvVar(name="CLAW_TASK", value=task),
                                    # Add other context as env vars or a mounted configmap/file
                                ],
                            )
                        ],
                        restart_policy="Never",
                    )
                ),
                backoff_limit=0,  # Fail fast
            ),
        )

        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        return job_id

    async def get_job_status(self, job_id: str) -> str:
        """Checks the status of the Kubernetes Job."""
        job = self.batch_v1.read_namespaced_job_status(
            name=job_id, namespace=self.namespace
        )
        if job.status.succeeded:
            return "completed"
        if job.status.failed:
            return "failed"
        if job.status.active:
            return "running"
        return "pending"

    async def cancel_job(self, job_id: str) -> None:
        """Deletes the Kubernetes Job."""
        self.batch_v1.delete_namespaced_job(
            name=job_id, namespace=self.namespace, propagation_policy="Background"
        )
