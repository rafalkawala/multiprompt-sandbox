import { Component, OnInit, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatStepperModule, MatStepper } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { WizardService } from './wizard.service';
import { WizardProjectStepComponent } from './steps/wizard-project-step.component';
import { WizardUploadStepComponent } from './steps/wizard-upload-step.component';
import { WizardSamplingStepComponent } from './steps/wizard-sampling-step.component';
import { WizardLabelingStepComponent } from './steps/wizard-labeling-step.component';
import { WizardResultStepComponent } from './steps/wizard-result-step.component';

@Component({
  selector: 'app-wizard-shell',
  standalone: true,
  imports: [
    CommonModule,
    MatStepperModule,
    MatButtonModule,
    MatIconModule,
    WizardProjectStepComponent,
    WizardUploadStepComponent,
    WizardSamplingStepComponent,
    WizardLabelingStepComponent,
    WizardResultStepComponent
  ],
  template: `
    <div class="wizard-shell">
      <header>
        <button mat-icon-button (click)="cancel()">
          <mat-icon>close</mat-icon>
        </button>
        <h2>{{ getFlowTitle() }}</h2>
      </header>

      <mat-stepper linear #stepper>
        <!-- Step 1: Project Setup -->
        <mat-step [stepControl]="projectStep.form" label="Define Problem">
          <app-wizard-project-step #projectStep (completed)="stepper.next()"></app-wizard-project-step>
        </mat-step>

        <!-- Step 2: Upload Data -->
        <mat-step [completed]="!!wizardService.dataset" label="Upload Data">
           <app-wizard-upload-step (completed)="stepper.next()"></app-wizard-upload-step>
        </mat-step>

        <!-- Step 3: Sampling (Only for Large Dataset Flow) -->
        @if (wizardService.flow === 'large_dataset') {
          <mat-step label="Sample Data">
            <app-wizard-sampling-step (completed)="stepper.next()"></app-wizard-sampling-step>
          </mat-step>
        }

        <!-- Step 4: Labeling -->
        <mat-step label="Ground Truth">
           <app-wizard-labeling-step (completed)="stepper.next()"></app-wizard-labeling-step>
        </mat-step>

        <!-- Step 5: Results / Action -->
        <mat-step label="Next Steps">
           <app-wizard-result-step></app-wizard-result-step>
        </mat-step>
      </mat-stepper>
    </div>
  `,
  styles: [`
    .wizard-shell {
      max-width: 1000px;
      margin: 0 auto;
      padding: 24px;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;

      h2 { margin: 0; }
    }

    mat-stepper {
      flex: 1;
      background: transparent;
    }
  `]
})
export class WizardShellComponent implements OnInit {
  @ViewChild('stepper') stepper!: MatStepper;

  constructor(public wizardService: WizardService, private router: Router) {}

  ngOnInit() {
    if (!this.wizardService.flow) {
      this.router.navigate(['/wizard']);
    }
  }

  getFlowTitle(): string {
    switch (this.wizardService.flow) {
      case 'feasibility': return 'Validate Model Feasibility';
      case 'large_dataset': return 'Analyze Large Dataset';
      case 'prompt_dev': return 'Develop & Optimize Prompt';
      default: return 'New Experiment';
    }
  }

  cancel() {
    if (confirm('Are you sure you want to exit the wizard? Progress may be lost.')) {
      this.router.navigate(['/']);
    }
  }
}
