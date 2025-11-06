import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    RouterLink
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss'
})
export class HomeComponent {
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
