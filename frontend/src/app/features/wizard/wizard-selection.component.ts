import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { WizardService, WizardFlow } from './wizard.service';

@Component({
  selector: 'app-wizard-selection',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="selection-container">
      <header>
        <h1>How would you like to start?</h1>
        <p>Select a path to guide you through the process.</p>
      </header>

      <div class="cards-grid">
        <!-- Flow A: Feasibility -->
        <mat-card class="selection-card" (click)="selectFlow('feasibility')">
          <mat-card-header>
            <div mat-card-avatar class="avatar-icon feasibility">
              <mat-icon>check_circle</mat-icon>
            </div>
            <mat-card-title>Validate Model Feasibility</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <p>I have a dataset and a specific question. I want to check if AI models can answer it accurately before I invest more time.</p>
            <div class="steps-preview">
              <small>Steps: Upload • Label • Benchmark</small>
            </div>
          </mat-card-content>
          <mat-card-actions>
            <button mat-button color="primary">Start Validation</button>
          </mat-card-actions>
        </mat-card>

        <!-- Flow B: Large Dataset -->
        <mat-card class="selection-card" (click)="selectFlow('large_dataset')">
          <mat-card-header>
            <div mat-card-avatar class="avatar-icon large-data">
              <mat-icon>filter_list</mat-icon>
            </div>
            <mat-card-title>Analyze Large Dataset</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <p>I have a massive collection of images. I want to sample a subset to estimate cost and performance for the whole batch.</p>
            <div class="steps-preview">
              <small>Steps: Upload • <strong>Sample</strong> • Label • Eval</small>
            </div>
          </mat-card-content>
          <mat-card-actions>
            <button mat-button color="primary">Start Analysis</button>
          </mat-card-actions>
        </mat-card>

        <!-- Flow C: Prompt Dev -->
        <mat-card class="selection-card" (click)="selectFlow('prompt_dev')">
          <mat-card-header>
            <div mat-card-avatar class="avatar-icon prompt-dev">
              <mat-icon>psychology</mat-icon>
            </div>
            <mat-card-title>Develop & Optimize Prompt</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <p>I want to craft the perfect prompt for an automated workflow. Iterate on a "Golden Set" of difficult images.</p>
            <div class="steps-preview">
              <small>Steps: Upload • Label (Golden Set) • <strong>Iterate</strong></small>
            </div>
          </mat-card-content>
          <mat-card-actions>
            <button mat-button color="primary">Start Developing</button>
          </mat-card-actions>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .selection-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 48px 24px;
      text-align: center;
    }

    header {
      margin-bottom: 48px;
      h1 { font-size: 32px; margin-bottom: 16px; color: #202124; }
      p { font-size: 18px; color: #5f6368; }
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 24px;
      text-align: left;
    }

    .selection-card {
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      height: 100%;
      display: flex;
      flex-direction: column;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
      }

      mat-card-content {
        flex: 1;
        padding-top: 16px;
        p { color: #5f6368; line-height: 1.5; margin-bottom: 24px; }
      }

      .steps-preview {
        color: #1967d2;
        background: #e8f0fe;
        padding: 8px 12px;
        border-radius: 4px;
        display: inline-block;
      }
    }

    .avatar-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      color: white;

      &.feasibility { background-color: #34a853; }
      &.large-data { background-color: #fbbc04; color: #3c4043; }
      &.prompt-dev { background-color: #ea4335; }
    }
  `]
})
export class WizardSelectionComponent {
  constructor(private wizardService: WizardService, private router: Router) {}

  selectFlow(flow: WizardFlow) {
    this.wizardService.reset(); // Clear previous state
    this.wizardService.setFlow(flow);
    this.router.navigate(['/wizard/flow']);
  }
}
