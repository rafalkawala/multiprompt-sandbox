import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ProjectsService } from '../../../core/services/projects.service';
import { WizardService } from '../wizard.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-wizard-project-step',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="step-content">
      <h3>Define your Problem</h3>
      <p>Start by giving your project a name and defining the type of question you want to answer.</p>

      <form [formGroup]="form" (ngSubmit)="submit()">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Project Name</mat-label>
          <input matInput formControlName="name" placeholder="e.g. Shelf Availability Audit">
          <mat-error *ngIf="form.get('name')?.hasError('required')">Project name is required</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Question to Answer</mat-label>
          <input matInput formControlName="question_text" placeholder="e.g. Is the product in stock?">
          <mat-error *ngIf="form.get('question_text')?.hasError('required')">Question is required</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Answer Type</mat-label>
          <mat-select formControlName="question_type">
            <mat-option value="binary">Binary (Yes/No)</mat-option>
            <mat-option value="multiple_choice">Multiple Choice</mat-option>
            <mat-option value="text">Free Text</mat-option>
            <mat-option value="count">Count</mat-option>
          </mat-select>
        </mat-form-field>

        <div class="actions">
          <button mat-raised-button color="primary" type="submit" [disabled]="form.invalid || loading">
            <mat-icon>arrow_forward</mat-icon>
            Create Project & Continue
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [`
    .step-content {
      max-width: 600px;
      margin: 0 auto;
      padding: 24px;
    }
    .full-width {
      width: 100%;
      margin-bottom: 16px;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 24px;
    }
  `]
})
export class WizardProjectStepComponent {
  @Output() completed = new EventEmitter<void>();

  form: FormGroup;
  loading = false;

  constructor(
    private fb: FormBuilder,
    private projectsService: ProjectsService,
    private wizardService: WizardService,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      name: ['', Validators.required],
      question_text: ['', Validators.required],
      question_type: ['binary', Validators.required]
    });
  }

  submit() {
    if (this.form.invalid) return;

    this.loading = true;
    const val = this.form.value;

    this.projectsService.createProject({
      name: val.name,
      question_text: val.question_text,
      question_type: val.question_type
    }).subscribe({
      next: (project) => {
        this.wizardService.setProject(project);
        this.loading = false;
        this.completed.emit();
      },
      error: (err) => {
        console.error('Project creation failed', err);
        this.snackBar.open('Failed to create project', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
  }
}
