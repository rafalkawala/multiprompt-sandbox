import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { WizardService, WizardFlow } from './wizard.service';

@Component({
  selector: 'app-wizard-selection',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    FormsModule
  ],
  template: `
    <div class="selection-container">
      <div class="close-btn-container">
        <button mat-icon-button (click)="close.emit()">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <header>
        <h1>How would you like to start?</h1>
        <p>Select a path to guide you through the process.</p>
      </header>

      <div class="cards-grid">
        <!-- Flow A: Feasibility -->
        <mat-card class="selection-card"
                  (click)="selectFlow('feasibility')"
                  (keydown.enter)="selectFlow('feasibility')"
                  tabindex="0"
                  role="button"
                  aria-label="Validate Model Feasibility - Check if AI models can answer your question accurately"
                  data-testid="card-feasibility">
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
        <mat-card class="selection-card"
                  (click)="selectFlow('large_dataset')"
                  (keydown.enter)="selectFlow('large_dataset')"
                  tabindex="0"
                  role="button"
                  aria-label="Analyze Large Dataset - Sample a subset to estimate cost and performance"
                  data-testid="card-large-dataset">
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
        <mat-card class="selection-card"
                  (click)="selectFlow('prompt_dev')"
                  (keydown.enter)="selectFlow('prompt_dev')"
                  tabindex="0"
                  role="button"
                  aria-label="Develop and Optimize Prompt - Iterate on a Golden Set of difficult images"
                  data-testid="card-prompt-dev">
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

      <footer>
        <mat-checkbox
          [(ngModel)]="doNotShowAgain"
          (change)="onDoNotShowChange()"
          data-testid="checkbox-do-not-show">
          Do not show this on startup
        </mat-checkbox>
      </footer>
    </div>
  `,
  styles: [`
    .selection-container {
      padding: 24px;
      text-align: center;
      position: relative;
    }

    .close-btn-container {
      position: absolute;
      top: -12px;
      right: -12px;
    }

    header {
      margin-bottom: 32px;
      h1 { font-size: 28px; margin-bottom: 12px; color: #202124; }
      p { font-size: 16px; color: #5f6368; }
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
      text-align: left;
      margin-bottom: 32px;
    }

    .selection-card {
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      height: 100%;
      display: flex;
      flex-direction: column;

      &:hover, &:focus {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        outline: none;
      }

      &:focus-visible {
        outline: 2px solid #1967d2;
        outline-offset: 2px;
      }

      mat-card-content {
        flex: 1;
        padding-top: 16px;
        p { color: #5f6368; line-height: 1.5; margin-bottom: 24px; font-size: 14px; }
      }

      .steps-preview {
        color: #1967d2;
        background: #e8f0fe;
        padding: 6px 10px;
        border-radius: 4px;
        display: inline-block;
        font-size: 12px;
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

    footer {
      margin-top: 24px;
      display: flex;
      justify-content: center;
    }
  `]
})
export class WizardSelectionComponent {
  @Output() flowSelected = new EventEmitter<WizardFlow>();
  @Output() close = new EventEmitter<void>();

  doNotShowAgain = false;

  constructor(private wizardService: WizardService) {
    this.doNotShowAgain = localStorage.getItem('wizard_do_not_show') === 'true';
  }

  selectFlow(flow: WizardFlow) {
    this.wizardService.reset();
    this.flowSelected.emit(flow);
  }

  onDoNotShowChange() {
    if (this.doNotShowAgain) {
      localStorage.setItem('wizard_do_not_show', 'true');
    } else {
      localStorage.removeItem('wizard_do_not_show');
    }
  }
}
