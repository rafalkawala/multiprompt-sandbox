import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ProjectsService } from '../../core/services/projects.service';
import { EvaluationsService } from '../../core/services/evaluations.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatToolbarModule,
    MatMenuModule,
    MatDividerModule,
    RouterLink
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent implements OnInit {
  constructor(
    public authService: AuthService,
    private projectsService: ProjectsService,
    private evaluationsService: EvaluationsService
  ) {}

  ngOnInit() {
    this.loadStats();
  }

  logout(): void {
    this.authService.logout();
  }

  loadStats() {
    forkJoin({
      projects: this.projectsService.getProjects(),
      evaluations: this.evaluationsService.getEvaluations()
    }).subscribe({
      next: (data) => {
        const projects = data.projects;
        const evaluations = data.evaluations;

        // Count total datasets - for now just show project count (datasets not in list)
        const totalDatasets = 0; // TODO: fetch dataset count

        // Calculate average accuracy from completed evaluations
        const completedEvals = evaluations.filter(e => e.status === 'completed' && e.accuracy != null);
        const avgAccuracy = completedEvals.length > 0
          ? completedEvals.reduce((sum, e) => sum + (e.accuracy || 0), 0) / completedEvals.length
          : 0;

        this.stats = [
          { label: 'Projects', value: projects.length.toString(), icon: 'folder' },
          { label: 'Datasets', value: totalDatasets.toString(), icon: 'cloud_upload' },
          { label: 'Evaluations', value: evaluations.length.toString(), icon: 'science' },
          { label: 'Avg Accuracy', value: avgAccuracy > 0 ? `${avgAccuracy.toFixed(1)}%` : '--%', icon: 'analytics' }
        ];
      },
      error: (err) => {
        console.error('Failed to load dashboard stats:', err);
      }
    });
  }

  features = [
    {
      icon: 'folder',
      title: 'Project & Dataset Management',
      description: 'Organize experiments by business use case. Upload up to 500 images per dataset with Cloud Storage integration.',
      route: '/projects',
      color: '#4285f4'
    },
    {
      icon: 'label',
      title: 'Ground Truth Labeling',
      description: 'Fast human labeling interface with keyboard shortcuts. Support for multiple question types and annotation export.',
      route: '/labeling',
      color: '#34a853'
    },
    {
      icon: 'edit_note',
      title: 'Prompt Engineering',
      description: 'Design complex prompt chains with variables. Version control and test on sample images before benchmarking.',
      route: '/prompts',
      color: '#fbbc04'
    },
    {
      icon: 'science',
      title: 'Multi-Model Benchmarking',
      description: 'Run experiments across Gemini Pro, Flash, and Claude. Batch processing with real-time progress tracking.',
      route: '/experiments',
      color: '#ea4335'
    },
    {
      icon: 'analytics',
      title: 'Accuracy & Scoring',
      description: 'Automated accuracy calculation vs ground truth. Confusion matrices, precision, recall, and F1 scores.',
      route: '/results',
      color: '#9334e6'
    },
    {
      icon: 'history',
      title: 'Experiment Repository',
      description: 'Persistent storage of all experiments. Compare results side-by-side and export reports in multiple formats.',
      route: '/results',
      color: '#01ac8d'
    }
  ];

  stats = [
    { label: 'Projects', value: '0', icon: 'folder' },
    { label: 'Datasets', value: '0', icon: 'cloud_upload' },
    { label: 'Experiments', value: '0', icon: 'science' },
    { label: 'Avg Accuracy', value: '--%', icon: 'analytics' }
  ];
}
