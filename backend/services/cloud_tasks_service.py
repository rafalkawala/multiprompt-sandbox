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
            # Build queue path
            parent = self.client.queue_path(self.project, self.location, self.queue)

            # Build task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": f"{settings.BACKEND_URL}/api/v1/internal/tasks/process-dataset/{dataset_id}",
                    "oidc_token": {
                        "service_account_email": f"multiprompt-backend-sa@{self.project}.iam.gserviceaccount.com"
                    }
                }
            }

            logger.info(f"Enqueueing dataset processing task for dataset {dataset_id}")

            # Create the task
            response = self.client.create_task(request={"parent": parent, "task": task})

            logger.info(f"Task created: {response.name}")
            return response.name

        except Exception as e:
            logger.error(f"Failed to enqueue task for dataset {dataset_id}: {str(e)}", exc_info=True)
            raise


# Singleton instance
_cloud_tasks_service = None


def get_cloud_tasks_service() -> CloudTasksService:
    """Get the CloudTasksService singleton instance"""
    global _cloud_tasks_service
    if _cloud_tasks_service is None:
        _cloud_tasks_service = CloudTasksService()
    return _cloud_tasks_service
