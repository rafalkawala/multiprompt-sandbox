import { Component, EventEmitter, Output, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { WizardService } from '../wizard.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-wizard-labeling-step',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule
  ],
  template: `
    <div class="step-content">
      <h3>Create Ground Truth</h3>
      <p>
        To validate AI performance, we need "Ground Truth" - the correct answers.
        Please label the images in your dataset.
      </p>

      <div class="info-box">
        <mat-icon>info</mat-icon>
        @if (wizardService.sampling?.mode === 'random') {
          <p>You selected to label a random sample of <strong>{{ wizardService.sampling?.count }}</strong> images.</p>
        } @else {
          <p>You need to label the images you uploaded.</p>
        }
      </div>

      <div class="action-card">
        <mat-card>
          <mat-card-content>
            <div class="card-content">
              <mat-icon class="large-icon">edit_note</mat-icon>
              <div>
                <h4>Open Labeling Tool</h4>
                <p>Opens in a new window. Return here when finished.</p>
              </div>
              <button mat-raised-button color="primary" (click)="openLabeling()">
                Start Labeling
                <mat-icon>open_in_new</mat-icon>
              </button>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      <div class="actions">
         <div class="status-check">
           <p>Finished labeling?</p>
         </div>
         <button mat-raised-button color="accent" (click)="onContinue()">
           I'm Done, Continue
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

    .info-box {
      background: #e8f0fe;
      color: #1967d2;
      padding: 16px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 24px 0;

      p { margin: 0; }
    }

    .action-card {
      margin: 32px 0;

      .card-content {
        display: flex;
        align-items: center;
        gap: 24px;
        padding: 16px;

        .large-icon {
          font-size: 40px;
          width: 40px;
          height: 40px;
          color: #5f6368;
        }

        div { flex: 1; }

        h4 { margin: 0 0 4px 0; font-size: 18px; }
        p { margin: 0; color: #5f6368; }
      }
    }

    .actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid #e0e0e0;
      padding-top: 24px;
    }
  `]
})
export class WizardLabelingStepComponent {
  @Output() completed = new EventEmitter<void>();

  constructor(public wizardService: WizardService, private router: Router) {}

  openLabeling() {
    const project = this.wizardService.project;
    const dataset = this.wizardService.dataset;
    if (project && dataset) {
      const url = this.router.serializeUrl(
        this.router.createUrlTree(['/projects', project.id, 'datasets', dataset.id, 'annotate'])
      );
      window.open(url, '_blank');
    }
  }

  onContinue() {
    this.completed.emit();
  }
}
