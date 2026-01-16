import { TestBed } from '@angular/core/testing';
import { WizardService } from './wizard.service';

describe('WizardService', () => {
  let service: WizardService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(WizardService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should have initial state null', () => {
    const state = service.state();
    expect(state.flow).toBeNull();
    expect(state.project).toBeNull();
    expect(state.dataset).toBeNull();
    expect(state.sampling.mode).toBe('all');
  });

  it('should set flow', () => {
    service.setFlow('feasibility');
    expect(service.flow).toBe('feasibility');
  });

  it('should set project', () => {
    const mockProject: any = { id: '123', name: 'Test' };
    service.setProject(mockProject);
    expect(service.project).toEqual(mockProject);
  });

  it('should set dataset', () => {
    const mockDataset: any = { id: '456', name: 'DS' };
    service.setDataset(mockDataset);
    expect(service.dataset).toEqual(mockDataset);
  });

  it('should set sampling', () => {
    service.setSampling({ mode: 'random', count: 100 });
    expect(service.sampling).toEqual({ mode: 'random', count: 100 });
  });

  it('should reset state', () => {
    service.setFlow('large_dataset');
    service.reset();
    expect(service.flow).toBeNull();
    expect(service.project).toBeNull();
  });
});
