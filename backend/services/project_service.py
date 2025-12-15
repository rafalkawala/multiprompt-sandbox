from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import structlog

from models.project import Project, Dataset
from models.user import User

logger = structlog.get_logger(__name__)

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def list_projects(self) -> List[Project]:
        """List all projects ordered by creation date desc"""
        return self.db.query(Project).order_by(Project.created_at.desc()).all()

    def get_project(self, project_id: str) -> Project:
        """Get project by ID"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        return project

    def create_project(self, project_data, current_user: User) -> Project:
        """Create a new project"""
        # Validate question_type
        valid_types = ['binary', 'multiple_choice', 'text', 'count']
        if project_data.question_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question_type. Must be one of: {valid_types}"
            )

        # Multiple choice requires options
        if project_data.question_type == 'multiple_choice' and not project_data.question_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_options required for multiple_choice type"
            )

        project = Project(
            name=project_data.name,
            description=project_data.description,
            question_text=project_data.question_text,
            question_type=project_data.question_type,
            question_options=project_data.question_options,
            created_by_id=current_user.id
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        logger.info(f"Created project: {project.name} by user: {current_user.email}")
        return project

    def update_project(self, project_id: str, project_data, current_user: User) -> Project:
        """Update project"""
        project = self.get_project(project_id)

        # Only the project owner can edit their project
        if str(project.created_by_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own projects"
            )

        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.question_text is not None:
            project.question_text = project_data.question_text
        if project_data.question_type is not None:
            valid_types = ['binary', 'multiple_choice', 'text', 'count']
            if project_data.question_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid question_type. Must be one of: {valid_types}"
                )
            project.question_type = project_data.question_type
        if project_data.question_options is not None:
            project.question_options = project_data.question_options

        self.db.commit()
        self.db.refresh(project)

        logger.info(f"Updated project: {project.name}")
        return project

    def delete_project(self, project_id: str, current_user: User) -> str:
        """Delete project and return its name"""
        project = self.get_project(project_id)

        # Only the project owner can delete their project
        if str(project.created_by_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own projects"
            )

        project_name = project.name
        self.db.delete(project)
        self.db.commit()

        logger.info(f"Deleted project: {project_name}")
        return project_name
