import { Injectable, signal } from '@angular/core';
import { Project, DatasetDetail } from '../../core/services/projects.service';

export type WizardFlow = 'feasibility' | 'large_dataset' | 'prompt_dev';

export interface WizardState {
  flow: WizardFlow | null;
  project: Project | null;
  dataset: DatasetDetail | null;
  sampling: {
    mode: 'all' | 'random' | 'manual';
    count?: number;
    percent?: number;
  };
}

@Injectable({
  providedIn: 'root'
})
export class WizardService {
  private initialState: WizardState = {
    flow: null,
    project: null,
    dataset: null,
    sampling: { mode: 'all' }
  };

  state = signal<WizardState>({ ...this.initialState });

  setFlow(flow: WizardFlow) {
    this.state.update(s => ({ ...s, flow }));
  }

  setProject(project: Project) {
    this.state.update(s => ({ ...s, project }));
  }

  setDataset(dataset: DatasetDetail) {
    this.state.update(s => ({ ...s, dataset }));
  }

  setSampling(sampling: WizardState['sampling']) {
    this.state.update(s => ({ ...s, sampling }));
  }

  reset() {
    this.state.set({ ...this.initialState });
  }

  // Helpers to get current state values
  get flow() { return this.state().flow; }
  get project() { return this.state().project; }
  get dataset() { return this.state().dataset; }
  get sampling() { return this.state().sampling; }
}
