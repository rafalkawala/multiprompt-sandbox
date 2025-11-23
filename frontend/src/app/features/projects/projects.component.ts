import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { ProjectsService, ProjectListItem, CreateProjectRequest } from '../../core/services/projects.service';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCardModule,
    MatChipsModule,
    MatTooltipModule,
    MatDialogModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule
  ],
  template: `
    <div class="projects-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Projects</mat-card-title>
          <mat-card-subtitle>Manage your benchmarking projects and datasets</mat-card-subtitle>
        </mat-card-header>

        <!-- Create Project Form -->
        <div class="create-project-form">
          <mat-form-field appearance="outline" class="name-field">
            <mat-label>Project Name</mat-label>
            <input matInput [(ngModel)]="newProject.name" placeholder="My Project">
          </mat-form-field>
          <mat-form-field appearance="outline" class="question-field">
            <mat-label>Question</mat-label>
            <input matInput [(ngModel)]="newProject.question_text" placeholder="Is this a defect?">
          </mat-form-field>
          <mat-form-field appearance="outline" class="type-field">
            <mat-label>Type</mat-label>
            <mat-select [(ngModel)]="newProject.question_type">
              <mat-option value="binary">Binary (Yes/No)</mat-option>
              <mat-option value="multiple_choice">Multiple Choice</mat-option>
              <mat-option value="text">Free Text</mat-option>
              <mat-option value="count">Count</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-raised-button color="primary" (click)="createProject()"
                  [disabled]="!newProject.name || !newProject.question_text">
            <mat-icon>add</mat-icon>
            Create
          </button>
        </div>

        <mat-card-content>
          @if (loading()) {
            <div class="loading-container">
              <mat-spinner diameter="40"></mat-spinner>
            </div>
          } @else if (projects().length === 0) {
            <div class="empty-state">
              <mat-icon>folder_open</mat-icon>
              <p>No projects yet. Create your first project above.</p>
            </div>
          } @else {
            <table mat-table [dataSource]="projects()" class="projects-table">
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef>Name</th>
                <td mat-cell *matCellDef="let project">
                  <a [routerLink]="['/projects', project.id]" class="project-link">
                    {{ project.name }}
                  </a>
                </td>
              </ng-container>

              <ng-container matColumnDef="description">
                <th mat-header-cell *matHeaderCellDef>Description</th>
                <td mat-cell *matCellDef="let project">{{ project.description || '-' }}</td>
              </ng-container>

              <ng-container matColumnDef="question_type">
                <th mat-header-cell *matHeaderCellDef>Question Type</th>
                <td mat-cell *matCellDef="let project">
                  <mat-chip class="type-chip">{{ formatQuestionType(project.question_type) }}</mat-chip>
                </td>
              </ng-container>

              <ng-container matColumnDef="dataset_count">
                <th mat-header-cell *matHeaderCellDef>Datasets</th>
                <td mat-cell *matCellDef="let project">{{ project.dataset_count }}</td>
              </ng-container>

              <ng-container matColumnDef="created_at">
                <th mat-header-cell *matHeaderCellDef>Created</th>
                <td mat-cell *matCellDef="let project">
                  {{ project.created_at | date:'shortDate' }}
                </td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Actions</th>
                <td mat-cell *matCellDef="let project">
                  <button mat-icon-button [routerLink]="['/projects', project.id]" matTooltip="View">
                    <mat-icon>visibility</mat-icon>
                  </button>
                  <button mat-icon-button color="warn" (click)="deleteProject(project)" matTooltip="Delete">
                    <mat-icon>delete</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          }
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .projects-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      color: #5f6368;

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    }

    .create-project-form {
      display: flex;
      gap: 16px;
      align-items: center;
      padding: 16px 24px;
      background: #f5f5f5;
      margin: 0 -16px;
      flex-wrap: wrap;
    }

    .name-field {
      flex: 1;
      min-width: 200px;
    }

    .question-field {
      flex: 2;
      min-width: 250px;
    }

    .type-field {
      width: 180px;
    }

    .projects-table {
      width: 100%;
    }

    .project-link {
      color: #1967d2;
      text-decoration: none;
      font-weight: 500;

      &:hover {
        text-decoration: underline;
      }
    }

    .type-chip {
      font-size: 11px;
      min-height: 24px;
    }

    th.mat-header-cell {
      font-weight: 600;
    }
  `]
})
export class ProjectsComponent implements OnInit {
  projects = signal<ProjectListItem[]>([]);
  loading = signal(true);
  displayedColumns = ['name', 'description', 'question_type', 'dataset_count', 'created_at', 'actions'];

  newProject: CreateProjectRequest = {
    name: '',
    question_text: '',
    question_type: 'binary'
  };

  constructor(
    private projectsService: ProjectsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loading.set(true);
    this.projectsService.getProjects().subscribe({
      next: (projects) => {
        this.projects.set(projects);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load projects:', err);
        this.snackBar.open('Failed to load projects', 'Close', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  createProject() {
    if (!this.newProject.name || !this.newProject.question_text) return;

    this.projectsService.createProject(this.newProject).subscribe({
      next: (project) => {
        this.projects.set([{
          id: project.id,
          name: project.name,
          description: project.description,
          question_type: project.question_type,
          created_at: project.created_at,
          updated_at: project.updated_at,
          dataset_count: 0
        }, ...this.projects()]);

        this.newProject = {
          name: '',
          question_text: '',
          question_type: 'binary'
        };
        this.snackBar.open(`Project "${project.name}" created`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to create project:', err);
        this.snackBar.open(err.error?.detail || 'Failed to create project', 'Close', { duration: 3000 });
      }
    });
  }

  deleteProject(project: ProjectListItem) {
    if (!confirm(`Delete project "${project.name}"? This will also delete all datasets and images.`)) {
      return;
    }

    this.projectsService.deleteProject(project.id).subscribe({
      next: () => {
        this.projects.set(this.projects().filter(p => p.id !== project.id));
        this.snackBar.open(`Project "${project.name}" deleted`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to delete project:', err);
        this.snackBar.open('Failed to delete project', 'Close', { duration: 3000 });
      }
    });
  }

  formatQuestionType(type: string): string {
    const types: Record<string, string> = {
      'binary': 'Binary',
      'multiple_choice': 'Multiple Choice',
      'text': 'Free Text',
      'count': 'Count'
    };
    return types[type] || type;
  }
}
