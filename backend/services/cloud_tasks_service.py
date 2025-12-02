import logging
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from core.config import settings

logger = logging.getLogger(__name__)


class CloudTasksService:
    """Service for enqueueing background tasks using Google Cloud Tasks"""

    def __init__(self):
        self.client = tasks_v2.CloudTasksClient()
        self.project = settings.GCP_PROJECT_ID
        self.location = settings.REGION  # us-central1
        self.queue = "image-processing-queue"

    def enqueue_dataset_processing(self, project_id: str, dataset_id: str) -> str:
        """
        Enqueue a task to process images in a dataset.

        Args:
            project_id: UUID of the project
            dataset_id: UUID of the dataset to process

        Returns:
            Task name/ID
        """
        try:
            # Validate configuration before attempting to create task
            if not settings.BACKEND_URL:
                raise ValueError("BACKEND_URL is not configured in environment")
            if not self.project:
                raise ValueError("GCP_PROJECT_ID is not configured in environment")

            # Build queue path
            parent = self.client.queue_path(self.project, self.location, self.queue)
            target_url = f"{settings.BACKEND_URL}/api/v1/internal/tasks/process-dataset/{dataset_id}"
            service_account = f"multiprompt-backend-sa@{self.project}.iam.gserviceaccount.com"

            # Log configuration for debugging
            logger.info(f"Creating Cloud Task for dataset {dataset_id}")
            logger.info(f"  Queue: {parent}")
            logger.info(f"  Target URL: {target_url}")
            logger.info(f"  Service Account: {service_account}")

            # Build task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": target_url,
                    "oidc_token": {
                        "service_account_email": service_account
                    }
                }
            }

            # Create the task
            response = self.client.create_task(request={"parent": parent, "task": task})

            logger.info(f"✓ Cloud Task created successfully: {response.name}")
            return response.name

        except Exception as e:
            logger.error(f"✗ Failed to enqueue Cloud Task for dataset {dataset_id}: {str(e)}", exc_info=True)
            logger.error(f"  Configuration: BACKEND_URL={settings.BACKEND_URL}, GCP_PROJECT_ID={self.project}, REGION={self.location}")
            raise

    def enqueue_labelling_job_task(self, job_id: str) -> str:
        """
        Enqueue a task to run a labelling job.

        Args:
            job_id: UUID of the labelling job to run

        Returns:
            Task name/ID
        """
        try:
            # Validate configuration
            if not settings.BACKEND_URL:
                raise ValueError("BACKEND_URL is not configured in environment")
            if not self.project:
                raise ValueError("GCP_PROJECT_ID is not configured in environment")

            # Build queue path
            parent = self.client.queue_path(self.project, self.location, self.queue)
            target_url = f"{settings.BACKEND_URL}/api/v1/internal/tasks/run-labelling-job/{job_id}"
            service_account = f"multiprompt-backend-sa@{self.project}.iam.gserviceaccount.com"

            # Log configuration
            logger.info(f"Creating Cloud Task for labelling job {job_id}")
            logger.info(f"  Queue: {parent}")
            logger.info(f"  Target URL: {target_url}")
            logger.info(f"  Service Account: {service_account}")

            # Build task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": target_url,
                    "oidc_token": {
                        "service_account_email": service_account
                    }
                }
            }

            # Create the task
            response = self.client.create_task(request={"parent": parent, "task": task})

            logger.info(f"✓ Cloud Task created successfully: {response.name}")
            return response.name

        except Exception as e:
            logger.error(f"✗ Failed to enqueue Cloud Task for labelling job {job_id}: {str(e)}", exc_info=True)
            logger.error(f"  Configuration: BACKEND_URL={settings.BACKEND_URL}, GCP_PROJECT_ID={self.project}, REGION={self.location}")
            raise


# Singleton instance
_cloud_tasks_service = None


def get_cloud_tasks_service() -> CloudTasksService:
    """Get the CloudTasksService singleton instance"""
    global _cloud_tasks_service
    if _cloud_tasks_service is None:
        _cloud_tasks_service = CloudTasksService()
    return _cloud_tasks_service
