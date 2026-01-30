import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { AnnotationImportDialogComponent } from './annotation-import-dialog.component';
import { EvaluationsService } from '../../../core/services/evaluations.service';

describe('AnnotationImportDialogComponent', () => {
  let component: AnnotationImportDialogComponent;
  let fixture: ComponentFixture<AnnotationImportDialogComponent>;
  let evaluationsServiceSpy: jasmine.SpyObj<EvaluationsService>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<AnnotationImportDialogComponent>>;
  let snackBarSpy: jasmine.SpyObj<MatSnackBar>;

  const mockProjectId = 'project-123';
  const mockDatasetId = 'dataset-123';

  beforeEach(async () => {
    evaluationsServiceSpy = jasmine.createSpyObj('EvaluationsService', [
      'startImportJob',
      'getImportJobStatus'
    ]);
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);
    snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [AnnotationImportDialogComponent],
      providers: [
        { provide: EvaluationsService, useValue: evaluationsServiceSpy },
        { provide: MatDialogRef, useValue: dialogRefSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { projectId: mockProjectId, datasetId: mockDatasetId }
        }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AnnotationImportDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with step 0', () => {
    expect(component.currentStep()).toBe(0);
  });

  describe('File Selection', () => {
    it('should update selectedFile on file selection', () => {
      const file = new File([''], 'test.csv', { type: 'text/csv' });
      const event = { target: { files: [file] } };

      component.onFileSelected(event);

      expect(component.selectedFile()).toBe(file);
    });

    it('should clear file on clearFile', () => {
      const file = new File([''], 'test.csv', { type: 'text/csv' });
      component.selectedFile.set(file);

      const event = new Event('click');
      spyOn(event, 'stopPropagation');

      component.clearFile(event);

      expect(component.selectedFile()).toBeNull();
      expect(event.stopPropagation).toHaveBeenCalled();
    });

    it('should format file size correctly', () => {
      expect(component.formatFileSize(0)).toBe('0 B');
      expect(component.formatFileSize(1024)).toBe('1.0 KB');
      expect(component.formatFileSize(1024 * 1024)).toBe('1.0 MB');
    });
  });

  describe('Import Process', () => {
    it('should start import job successfully', () => {
      const file = new File(['header'], 'test.csv', { type: 'text/csv' });
      component.selectedFile.set(file);
      const jobId = 'job-123';

      evaluationsServiceSpy.startImportJob.and.returnValue(of({ job_id: jobId }));
      // Mock getImportJobStatus to return initial status immediately so polling starts clean
      evaluationsServiceSpy.getImportJobStatus.and.returnValue(of({
        id: jobId,
        status: 'pending',
        total_rows: 0,
        processed_rows: 0,
        created_count: 0,
        updated_count: 0,
        skipped_count: 0,
        error_count: 0,
        errors: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        completed_at: null
      }));

      component.startImport();

      expect(evaluationsServiceSpy.startImportJob).toHaveBeenCalledWith(mockProjectId, mockDatasetId, file);
      expect(component.jobId()).toBe(jobId);
      expect(component.currentStep()).toBe(1);
      expect(component.loading()).toBeFalse();
    });

    it('should handle start import error', () => {
      const file = new File(['header'], 'test.csv', { type: 'text/csv' });
      component.selectedFile.set(file);

      evaluationsServiceSpy.startImportJob.and.returnValue(throwError(() => ({ message: 'Upload failed' })));

      component.startImport();

      expect(component.loading()).toBeFalse();
      expect(snackBarSpy.open).toHaveBeenCalled();
      expect(component.currentStep()).toBe(0);
    });
  });

  describe('Polling and Progress', () => {
    it('should calculate progress percent correctly', () => {
      component.jobStatus.set({
        id: '1',
        status: 'processing',
        total_rows: 100,
        processed_rows: 50,
        created_count: 0,
        updated_count: 0,
        skipped_count: 0,
        error_count: 0,
        errors: [],
        created_at: '',
        updated_at: '',
        completed_at: null
      });

      expect(component.getProgressPercent()).toBe(50);
    });

    it('should return 0 progress if total_rows is 0', () => {
      component.jobStatus.set({
        id: '1',
        status: 'pending',
        total_rows: 0,
        processed_rows: 0,
        created_count: 0,
        updated_count: 0,
        skipped_count: 0,
        error_count: 0,
        errors: [],
        created_at: '',
        updated_at: '',
        completed_at: null
      });

      expect(component.getProgressPercent()).toBe(0);
    });

    it('should identify completed status', () => {
      component.jobStatus.set({
        id: '1',
        status: 'completed',
        total_rows: 10,
        processed_rows: 10,
        created_count: 10,
        updated_count: 0,
        skipped_count: 0,
        error_count: 0,
        errors: [],
        created_at: '',
        updated_at: '',
        completed_at: 'now'
      });

      expect(component.isCompleted()).toBeTrue();
    });
  });
});
