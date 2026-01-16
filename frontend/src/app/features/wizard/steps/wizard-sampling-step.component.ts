import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatRadioModule } from '@angular/material/radio';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { WizardService } from '../wizard.service';

@Component({
  selector: 'app-wizard-sampling-step',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatRadioModule,
    MatInputModule,
    MatFormFieldModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="step-content">
      <h3>Sample your Data</h3>
      <p>Your dataset is large. Select a strategy to pick a subset for labeling and initial evaluation.</p>

      <mat-radio-group [(ngModel)]="mode" class="mode-group">
        <mat-radio-button value="all">
          <div class="radio-label">
            <strong>Use All Images</strong>
            <small>Label and evaluate everything (may be slow/expensive)</small>
          </div>
        </mat-radio-button>

        <mat-radio-button value="random">
          <div class="radio-label">
            <strong>Random Sample</strong>
            <small>Pick a random subset</small>
          </div>
        </mat-radio-button>
      </mat-radio-group>

      @if (mode === 'random') {
        <div class="random-settings">
          <mat-form-field appearance="outline">
            <mat-label>Number of images</mat-label>
            <input matInput type="number" [(ngModel)]="count" min="1">
          </mat-form-field>
        </div>
      }

      <div class="actions">
        <button mat-raised-button color="primary" (click)="submit()">
          Apply Sampling
          <mat-icon>arrow_forward</mat-icon>
        </button>
      </div>
    </div>
  `,
  styles: [`
    .step-content {
      max-width: 600px;
      margin: 0 auto;
      padding: 24px;
    }

    .mode-group {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin: 24px 0;
    }

    .radio-label {
      display: flex;
      flex-direction: column;
      margin-left: 8px;

      strong { font-size: 16px; }
      small { color: #5f6368; }
    }

    .random-settings {
      margin-left: 32px;
      margin-bottom: 24px;
    }

    .actions {
      display: flex;
      justify-content: flex-end;
    }
  `]
})
export class WizardSamplingStepComponent {
  @Output() completed = new EventEmitter<void>();

  mode: 'all' | 'random' = 'random';
  count = 50;

  constructor(private wizardService: WizardService) {}

  submit() {
    this.wizardService.setSampling({
      mode: this.mode,
      count: this.mode === 'random' ? this.count : undefined
    });
    this.completed.emit();
  }
}
