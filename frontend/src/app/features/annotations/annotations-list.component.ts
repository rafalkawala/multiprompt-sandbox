import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { ProjectsService, ProjectListItem, DatasetDetail } from '../../core/services/projects.service';
import { EvaluationsService, AnnotationStats } from '../../core/services/evaluations.service';

interface ProjectWithDatasets extends ProjectListItem {
  datasets: DatasetDetail[];
  stats: { [datasetId: string]: AnnotationStats };
}

@Component({
  selector: 'app-annotations-list',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatChipsModule
  ],
  template: `
    <div class="annotations-container">
      <h1>Annotations</h1>
      <p class="subtitle">Select a project and dataset to annotate images</p>

      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (projects().length === 0) {
        <mat-card class="empty-state">
          <mat-icon>folder_off</mat-icon>
          <p>No projects found. Create a project first to start annotating.</p>
        </mat-card>
      } @else {
        <mat-accordion>
          @for (project of projects(); track project.id) {
            <mat-expansion-panel (opened)="loadProjectDatasets(project.id)">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon>folder</mat-icon>
                  {{ project.name }}
                </mat-panel-title>
                <mat-panel-description>
                  {{ project.dataset_count }} datasets
                </mat-panel-description>
              </mat-expansion-panel-header>

              @if (projectsData()[project.id]?.datasets.length) {
                <div class="datasets-list">
                  @for (dataset of projectsData()[project.id].datasets; track dataset.id) {
                    <mat-card class="dataset-card">
                      <mat-card-header>
                        <mat-card-title>{{ dataset.name }}</mat-card-title>
                        <mat-card-subtitle>{{ dataset.image_count }} images</mat-card-subtitle>
                      </mat-card-header>
                      <mat-card-content>
                        @if (projectsData()[project.id].stats[dataset.id]) {
                          <div class="stats-row">
                            <mat-chip-set>
                              <mat-chip>{{ projectsData()[project.id].stats[dataset.id].annotated }} annotated</mat-chip>
                              <mat-chip>{{ projectsData()[project.id].stats[dataset.id].remaining }} remaining</mat-chip>
                              @if (projectsData()[project.id].stats[dataset.id].flagged > 0) {
                                <mat-chip color="warn" highlighted>{{ projectsData()[project.id].stats[dataset.id].flagged }} flagged</mat-chip>
                              }
                            </mat-chip-set>
                          </div>
                          <div class="progress-bar">
                            <div class="progress-fill" [style.width.%]="(projectsData()[project.id].stats[dataset.id].annotated / projectsData()[project.id].stats[dataset.id].total_images) * 100"></div>
                          </div>
                        }
                      </mat-card-content>
                      <mat-card-actions>
                        <button mat-raised-button color="primary" (click)="startAnnotating(project.id, dataset.id)">
                          <mat-icon>edit_note</mat-icon>
                          Start Annotating
                        </button>
                      </mat-card-actions>
                    </mat-card>
                  }
                </div>
              } @else {
                <p class="no-datasets">No datasets in this project</p>
              }
            </mat-expansion-panel>
          }
        </mat-accordion>
      }
    </div>
  `,
  styles: [`
    .annotations-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 8px;
      color: #202124;
    }

    .subtitle {
      color: #5f6368;
      margin: 0 0 24px;
    }

    .loading {
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

    mat-expansion-panel {
      margin-bottom: 8px;
    }

    mat-panel-title {
      display: flex;
      align-items: center;
      gap: 8px;

      mat-icon {
        color: #1967d2;
      }
    }

    .datasets-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
      padding: 16px 0;
    }

    .dataset-card {
      mat-card-content {
        padding: 16px;
      }
    }

    .stats-row {
      margin-bottom: 12px;
    }

    .progress-bar {
      height: 4px;
      background: #e8eaed;
      border-radius: 2px;
      overflow: hidden;

      .progress-fill {
        height: 100%;
        background: #1967d2;
        transition: width 0.3s ease;
      }
    }

    .no-datasets {
      color: #5f6368;
      padding: 16px;
      text-align: center;
    }
  `]
})
export class AnnotationsListComponent implements OnInit {
  projects = signal<ProjectListItem[]>([]);
  projectsData = signal<{ [id: string]: ProjectWithDatasets }>({});
  loading = signal(true);

  constructor(
    private projectsService: ProjectsService,
    private evaluationsService: EvaluationsService,
    private router: Router
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
        this.loading.set(false);
      }
    });
  }

  loadProjectDatasets(projectId: string) {
    if (this.projectsData()[projectId]) return;

    this.projectsService.getDatasets(projectId).subscribe({
      next: (datasets) => {
        const current = this.projectsData();
        const project = this.projects().find(p => p.id === projectId);
        if (project) {
          current[projectId] = {
            ...project,
            datasets,
            stats: {}
          };
          this.projectsData.set({ ...current });

          // Load stats for each dataset
          datasets.forEach(dataset => {
            this.loadDatasetStats(projectId, dataset.id);
          });
        }
      },
      error: (err) => console.error('Failed to load datasets:', err)
    });
  }

  loadDatasetStats(projectId: string, datasetId: string) {
    this.evaluationsService.getAnnotationStats(projectId, datasetId).subscribe({
      next: (stats) => {
        const current = this.projectsData();
        if (current[projectId]) {
          current[projectId].stats[datasetId] = stats;
          this.projectsData.set({ ...current });
        }
      },
      error: (err) => console.error('Failed to load stats:', err)
    });
  }

  startAnnotating(projectId: string, datasetId: string) {
    this.router.navigate(['/projects', projectId, 'datasets', datasetId, 'annotate']);
  }
}
