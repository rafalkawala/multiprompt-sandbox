import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { WizardSelectionComponent } from './wizard-selection.component';
import { WizardShellComponent } from './wizard-shell.component';
import { WizardService, WizardFlow } from './wizard.service';

@Component({
  selector: 'app-wizard-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    WizardSelectionComponent,
    WizardShellComponent
  ],
  template: `
    <div class="wizard-dialog-content">
      @if (mode === 'selection') {
        <app-wizard-selection
          (flowSelected)="onFlowSelected($event)"
          (close)="closeDialog()">
        </app-wizard-selection>
      } @else {
        <app-wizard-shell (close)="closeDialog()"></app-wizard-shell>
      }
    </div>
  `,
  styles: [`
    .wizard-dialog-content {
      height: 100%;
      width: 100%;
      overflow-y: auto;
    }
  `]
})
export class WizardDialogComponent {
  mode: 'selection' | 'shell' = 'selection';

  constructor(
    private dialogRef: MatDialogRef<WizardDialogComponent>,
    private wizardService: WizardService
  ) {}

  onFlowSelected(flow: WizardFlow) {
    this.wizardService.setFlow(flow);
    this.mode = 'shell';
  }

  closeDialog() {
    this.dialogRef.close();
  }
}
