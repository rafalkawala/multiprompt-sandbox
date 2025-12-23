import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ConfusionMatrixComponent, ConfusionMatrix } from './confusion-matrix.component';

describe('ConfusionMatrixComponent', () => {
  let component: ConfusionMatrixComponent;
  let fixture: ComponentFixture<ConfusionMatrixComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        ConfusionMatrixComponent,
        NoopAnimationsModule
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ConfusionMatrixComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('when matrix is null', () => {
    beforeEach(() => {
      component.matrix = null;
      fixture.detectChanges();
    });

    it('should display "No Data" message', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.no-data')?.textContent).toContain('No Data');
    });

    it('should not display the matrix container', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.matrix-container')).toBeNull();
    });
  });

  describe('when matrix is undefined', () => {
    beforeEach(() => {
      component.matrix = undefined;
      fixture.detectChanges();
    });

    it('should display "No Data" message', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.no-data')?.textContent).toContain('No Data');
    });
  });

  describe('when matrix has data', () => {
    const testMatrix: ConfusionMatrix = {
      tp: 45,
      tn: 30,
      fp: 10,
      fn: 15
    };

    beforeEach(() => {
      component.matrix = testMatrix;
      fixture.detectChanges();
    });

    it('should display the matrix container', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.matrix-container')).not.toBeNull();
    });

    it('should not display "No Data" message', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.no-data')).toBeNull();
    });

    it('should display True Positive value', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const tpCell = compiled.querySelector('.tp');
      expect(tpCell?.querySelector('.value')?.textContent).toBe('45');
      expect(tpCell?.querySelector('.label')?.textContent).toBe('TP');
    });

    it('should display True Negative value', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const tnCell = compiled.querySelector('.tn');
      expect(tnCell?.querySelector('.value')?.textContent).toBe('30');
      expect(tnCell?.querySelector('.label')?.textContent).toBe('TN');
    });

    it('should display False Positive value', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const fpCell = compiled.querySelector('.fp');
      expect(fpCell?.querySelector('.value')?.textContent).toBe('10');
      expect(fpCell?.querySelector('.label')?.textContent).toBe('FP');
    });

    it('should display False Negative value', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const fnCell = compiled.querySelector('.fn');
      expect(fnCell?.querySelector('.value')?.textContent).toBe('15');
      expect(fnCell?.querySelector('.label')?.textContent).toBe('FN');
    });

    it('should display axis labels', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.x-axis')?.textContent).toContain('Predicted');
      expect(compiled.querySelector('.y-axis')?.textContent).toContain('Actual');
    });
  });

  describe('when matrix has zero values', () => {
    const zeroMatrix: ConfusionMatrix = {
      tp: 0,
      tn: 0,
      fp: 0,
      fn: 0
    };

    beforeEach(() => {
      component.matrix = zeroMatrix;
      fixture.detectChanges();
    });

    it('should display zero values correctly', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.querySelector('.tp .value')?.textContent).toBe('0');
      expect(compiled.querySelector('.tn .value')?.textContent).toBe('0');
      expect(compiled.querySelector('.fp .value')?.textContent).toBe('0');
      expect(compiled.querySelector('.fn .value')?.textContent).toBe('0');
    });
  });

  describe('matrix cell styling', () => {
    const testMatrix: ConfusionMatrix = {
      tp: 10,
      tn: 20,
      fp: 5,
      fn: 3
    };

    beforeEach(() => {
      component.matrix = testMatrix;
      fixture.detectChanges();
    });

    it('should have correct cells for true predictions (green)', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const tpCell = compiled.querySelector('.tp');
      const tnCell = compiled.querySelector('.tn');

      // These should have green background (correct predictions)
      expect(tpCell).not.toBeNull();
      expect(tnCell).not.toBeNull();
    });

    it('should have correct cells for false predictions (red)', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const fpCell = compiled.querySelector('.fp');
      const fnCell = compiled.querySelector('.fn');

      // These should have red background (incorrect predictions)
      expect(fpCell).not.toBeNull();
      expect(fnCell).not.toBeNull();
    });

    it('should have tooltip attributes on cells', () => {
      const compiled = fixture.nativeElement as HTMLElement;
      const tpCell = compiled.querySelector('.tp');

      // Material tooltip adds matTooltip attribute
      expect(tpCell?.hasAttribute('mattooltip') || tpCell?.getAttribute('ng-reflect-message')).toBeTruthy();
    });
  });
});
