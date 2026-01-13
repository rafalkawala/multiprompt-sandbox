import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { WizardService } from '../wizard.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-wizard-result-step',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="step-content">
      <div class="success-header">
        <div class="icon-circle">
          <mat-icon>check</mat-icon>
        </div>
        <h3>Ready to Validate!</h3>
        <p>You have set up your project, data, and ground truth.</p>
      </div>

      <div class="action-grid">
        <!-- Action: Run Evaluation -->
        <div class="action-item" (click)="runEvaluation()">
          <mat-icon class="action-icon">analytics</mat-icon>
          <h4>Run Benchmark</h4>
          <p>Test models (Gemini, Claude) against your labels to measure accuracy.</p>
          <button mat-button color="primary">Go to Evaluation</button>
        </div>

        <!-- Action: Prompt Sandbox (For Dev Flow) -->
        <div class="action-item" (click)="goToSandbox()">
          <mat-icon class="action-icon">build</mat-icon>
          <h4>Refine Prompt</h4>
          <p>Iterate on your prompt using your labeled examples.</p>
          <button mat-button color="primary">Go to Sandbox</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .step-content {
      max-width: 800px;
      margin: 0 auto;
      padding: 24px;
      text-align: center;
    }

    .success-header {
      margin-bottom: 48px;

      .icon-circle {
        width: 80px;
        height: 80px;
        background: #34a853;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 24px;
        color: white;

        mat-icon { font-size: 40px; width: 40px; height: 40px; }
      }

      h3 { font-size: 28px; margin: 0 0 8px; }
      p { color: #5f6368; font-size: 18px; margin: 0; }
    }

    .action-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 24px;
    }

    .action-item {
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 32px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        border-color: #1967d2;
      }

      .action-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #1967d2;
        margin-bottom: 16px;
      }

      h4 { margin: 0 0 8px; font-size: 20px; }
      p { color: #5f6368; margin-bottom: 24px; min-height: 40px; }
    }
  `]
})
export class WizardResultStepComponent {
  constructor(public wizardService: WizardService, private router: Router) {}

  runEvaluation() {
    const project = this.wizardService.project;
    const dataset = this.wizardService.dataset;
    if (project && dataset) {
      this.router.navigate(['/evaluations'], {
        queryParams: {
          projectId: project.id,
          datasetId: dataset.id,
          create: true, // Hint to open creation dialog
          // If we had sampling config, we might pass it or handle it in the service
        }
      });
    }
  }

  goToSandbox() {
    // Since Sandbox isn't fully separate, we go to Evaluations but maybe with a hint?
    // Or back to project view.
    const project = this.wizardService.project;
    if (project) {
        this.router.navigate(['/projects', project.id]);
    }
  }
}
