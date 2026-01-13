import { Routes } from '@angular/router';
import { WizardSelectionComponent } from './wizard-selection.component';
import { WizardShellComponent } from './wizard-shell.component';

export const WIZARD_ROUTES: Routes = [
  { path: '', component: WizardSelectionComponent },
  { path: 'flow', component: WizardShellComponent }
];
