# Feature: Bulk Import/Export of Annotations

## Epic Overview
Enable users to manage ground truth labels (annotations) efficiently using familiar tools like Microsoft Excel and Google Sheets. This feature provides offline labeling, bulk corrections, and seamless data migration capabilities.

---

## User Stories

### Story 1: Export Annotations to CSV
**As a** project manager
**I want to** export all annotations for a dataset to CSV
**So that** I can review, edit, and share labels in Excel or Google Sheets

**Acceptance Criteria:**
- [ ] Export button visible on dataset detail page
- [ ] Downloaded CSV includes: image_filename, annotation_value, image_id, dataset_name
- [ ] CSV opens correctly in Excel without formatting issues
- [ ] Empty annotations show as blank cells (not "null" or "None")
- [ ] Filename format: `{project_name}_{dataset_name}_annotations_{timestamp}.csv`

---

### Story 2: Download Sample CSV Template
**As a** new user
**I want to** download a sample CSV template
**So that** I understand the correct format before importing annotations

**Acceptance Criteria:**
- [ ] "Download Template" button available on dataset page
- [ ] Template includes header row with all required columns
- [ ] Template includes 2-3 example rows with sample data
- [ ] Examples match the project's question type (binary/multiple choice/count/text)
- [ ] Template includes helpful comments/instructions for Excel users

---

### Story 3: Import Annotations with Validation
**As a** data annotator
**I want to** upload a CSV with annotations
**So that** I can bulk-update labels without clicking through each image

**Acceptance Criteria:**
- [ ] Import button visible on dataset detail page
- [ ] File upload accepts .csv files
- [ ] Shows validation preview before applying changes
- [ ] Preview displays: total rows, valid annotations, errors, warnings
- [ ] Binary labels accept: yes/no, true/false, 1/0, Y/N (case insensitive)
- [ ] Clear error messages for invalid values
- [ ] Option to download error report CSV

---

### Story 4: Smart Binary Label Normalization
**As a** user importing annotations
**I want** the system to understand multiple formats for binary labels
**So that** I don't have to reformat my data to match a specific format

**Accepted Formats (case insensitive):**
- `yes`, `y`, `true`, `t`, `1` → `true`
- `no`, `n`, `false`, `f`, `0` → `false`
- Empty/blank → no annotation (skipped)

**Acceptance Criteria:**
- [ ] All formats normalize correctly
- [ ] Import preview shows normalized values
- [ ] Invalid values (e.g., "maybe", "2") flagged as errors
- [ ] Works regardless of Excel's auto-formatting

---

### Story 5: Review and Confirm Import
**As a** user importing annotations
**I want to** review changes before they're applied
**So that** I can catch mistakes before overwriting existing data

**Acceptance Criteria:**
- [ ] Two-step import: Preview → Confirm
- [ ] Preview shows: new annotations, updates, no changes, errors
- [ ] Can cancel after preview without changes
- [ ] Shows which images will be updated vs created
- [ ] Clear warning if overwriting existing annotations

---

## Technical Implementation Plan

### Phase 1: Backend - Export (2-3 hours)

#### 1.1 Add pandas to requirements
**File:** `backend/requirements.txt`
```python
pandas==2.1.4
```

#### 1.2 Create CSV export endpoint
**File:** `backend/api/v1/annotations.py`

```python
@router.get("/{project_id}/datasets/{dataset_id}/annotations/export")
async def export_annotations(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all annotations for a dataset to CSV"""

    # Verify access
    project = verify_project_access(db, project_id, current_user.id)
    dataset = verify_dataset_access(db, dataset_id, project_id)

    # Get all images with annotations
    images = db.query(Image).filter(
        Image.dataset_id == dataset_id
    ).all()

    # Build CSV data
    rows = []
    for img in images:
        annotation_value = ""
        if img.annotation:
            # Extract value based on question type
            annotation_value = extract_annotation_value(
                img.annotation,
                project.question_type
            )

        rows.append({
            "image_id": str(img.id),
            "image_filename": img.filename,
            "annotation_value": annotation_value,
            "dataset_name": dataset.name
        })

    # Create CSV
    df = pd.DataFrame(rows)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project.name}_{dataset.name}_annotations_{timestamp}.csv"
    filename = sanitize_filename(filename)

    # Return as streaming response
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')  # BOM for Excel
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
```

#### 1.3 Create sample template endpoint
**File:** `backend/api/v1/annotations.py`

```python
@router.get("/{project_id}/datasets/{dataset_id}/annotations/template")
async def get_template(
    project_id: str,
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a sample CSV template based on project type"""

    project = verify_project_access(db, project_id, current_user.id)
    dataset = verify_dataset_access(db, dataset_id, project_id)

    # Generate sample rows based on question type
    samples = generate_sample_rows(project.question_type, project.question_options)

    df = pd.DataFrame(samples)

    filename = f"{project.name}_{dataset.name}_template.csv"
    filename = sanitize_filename(filename)

    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
```

### Phase 2: Backend - Import with Validation (4-5 hours)

#### 2.1 Create validation service
**File:** `backend/services/annotation_import_service.py`

```python
class AnnotationImportService:
    """Service for importing and validating CSV annotations"""

    BINARY_TRUE_VALUES = {'yes', 'y', 'true', 't', '1', '1.0'}
    BINARY_FALSE_VALUES = {'no', 'n', 'false', 'f', '0', '0.0'}

    def __init__(self, project, dataset, db_session):
        self.project = project
        self.dataset = dataset
        self.db = db_session

    def normalize_binary(self, value: str) -> Optional[bool]:
        """Normalize binary value to True/False/None"""
        if pd.isna(value) or value == '':
            return None

        value_lower = str(value).strip().lower()

        if value_lower in self.BINARY_TRUE_VALUES:
            return True
        elif value_lower in self.BINARY_FALSE_VALUES:
            return False
        else:
            raise ValueError(f"Invalid binary value: '{value}'")

    def validate_row(self, row: dict) -> dict:
        """Validate a single row and return validation result"""
        result = {
            'row_number': row.get('_row_number'),
            'image_filename': row.get('image_filename'),
            'annotation_value': row.get('annotation_value'),
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'normalized_value': None,
            'image_id': None
        }

        # Find image by ID or filename
        image = self.find_image(row)
        if not image:
            result['status'] = 'error'
            result['errors'].append('Image not found in dataset')
            return result

        result['image_id'] = str(image.id)

        # Validate annotation value
        try:
            normalized = self.validate_value(
                row.get('annotation_value'),
                self.project.question_type,
                self.project.question_options
            )
            result['normalized_value'] = normalized

            # Check if updating existing annotation
            if image.annotation:
                result['warnings'].append('Will overwrite existing annotation')

        except ValueError as e:
            result['status'] = 'error'
            result['errors'].append(str(e))

        return result

    def validate_csv(self, file: UploadFile) -> dict:
        """Validate entire CSV and return preview"""
        df = pd.read_csv(file.file)

        # Add row numbers for error reporting
        df['_row_number'] = df.index + 2  # +2 for header and 0-index

        results = []
        for _, row in df.iterrows():
            result = self.validate_row(row.to_dict())
            results.append(result)

        # Generate summary
        summary = {
            'total_rows': len(results),
            'valid': sum(1 for r in results if r['status'] == 'valid'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'warnings': sum(1 for r in results if r['warnings']),
            'results': results
        }

        return summary
```

#### 2.2 Create import endpoints
**File:** `backend/api/v1/annotations.py`

```python
@router.post("/{project_id}/datasets/{dataset_id}/annotations/import/preview")
async def preview_import(
    project_id: str,
    dataset_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Preview CSV import with validation (dry run)"""

    project = verify_project_access(db, project_id, current_user.id)
    dataset = verify_dataset_access(db, dataset_id, project_id)

    import_service = AnnotationImportService(project, dataset, db)

    try:
        preview = import_service.validate_csv(file)
        return preview
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse CSV: {str(e)}"
        )


@router.post("/{project_id}/datasets/{dataset_id}/annotations/import/confirm")
async def confirm_import(
    project_id: str,
    dataset_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_write_access),
    db: Session = Depends(get_db)
):
    """Apply CSV import after validation"""

    project = verify_project_access(db, project_id, current_user.id)
    dataset = verify_dataset_access(db, dataset_id, project_id)

    import_service = AnnotationImportService(project, dataset, db)

    # Validate first
    preview = import_service.validate_csv(file)

    if preview['errors'] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot import: {preview['errors']} errors found"
        )

    # Apply changes
    await file.seek(0)  # Reset file pointer
    result = import_service.apply_import(file, current_user.id)

    db.commit()

    return result
```

### Phase 3: Frontend UI (3-4 hours)

#### 3.1 Add import/export buttons to dataset page
**File:** `frontend/src/app/features/projects/project-detail.component.html`

```html
<!-- In dataset card actions -->
<div class="dataset-actions">
  <button mat-raised-button color="primary" (click)="uploadImages(dataset.id)">
    <mat-icon>upload</mat-icon>
    Upload Images
  </button>

  <button mat-button (click)="exportAnnotations(dataset.id)">
    <mat-icon>download</mat-icon>
    Export CSV
  </button>

  <button mat-button (click)="downloadTemplate(dataset.id)">
    <mat-icon>description</mat-icon>
    Download Template
  </button>

  <button mat-raised-button color="accent" (click)="importAnnotations(dataset.id)">
    <mat-icon>publish</mat-icon>
    Import CSV
  </button>
</div>
```

#### 3.2 Create import dialog component
**File:** `frontend/src/app/features/annotations/import-dialog.component.ts`

```typescript
@Component({
  selector: 'app-import-dialog',
  template: `
    <h2 mat-dialog-title>Import Annotations</h2>

    <mat-dialog-content>
      <mat-stepper [linear]="true" #stepper>
        <!-- Step 1: Upload File -->
        <mat-step [completed]="!!previewData">
          <ng-template matStepLabel>Upload CSV</ng-template>

          <div class="upload-area">
            <input type="file" #fileInput accept=".csv"
                   (change)="onFileSelected($event)" hidden>

            <button mat-raised-button color="primary"
                    (click)="fileInput.click()">
              <mat-icon>upload_file</mat-icon>
              Choose CSV File
            </button>

            <p *ngIf="selectedFile">{{ selectedFile.name }}</p>

            <button mat-raised-button color="accent"
                    [disabled]="!selectedFile || loading"
                    (click)="previewImport()">
              Validate & Preview
            </button>
          </div>
        </mat-step>

        <!-- Step 2: Review Preview -->
        <mat-step [completed]="imported">
          <ng-template matStepLabel>Review Changes</ng-template>

          <div *ngIf="previewData" class="preview-summary">
            <mat-card class="summary-card">
              <h3>Import Summary</h3>
              <div class="stats">
                <div class="stat">
                  <span class="label">Total Rows:</span>
                  <span class="value">{{ previewData.total_rows }}</span>
                </div>
                <div class="stat valid">
                  <span class="label">Valid:</span>
                  <span class="value">{{ previewData.valid }}</span>
                </div>
                <div class="stat error" *ngIf="previewData.errors > 0">
                  <span class="label">Errors:</span>
                  <span class="value">{{ previewData.errors }}</span>
                </div>
                <div class="stat warning" *ngIf="previewData.warnings > 0">
                  <span class="label">Warnings:</span>
                  <span class="value">{{ previewData.warnings }}</span>
                </div>
              </div>
            </mat-card>

            <!-- Error List -->
            <mat-card *ngIf="previewData.errors > 0" class="errors-card">
              <h4>Errors Found</h4>
              <mat-list>
                <mat-list-item *ngFor="let result of getErrorRows()">
                  <mat-icon color="warn">error</mat-icon>
                  <div class="error-details">
                    <strong>Row {{ result.row_number }}:</strong>
                    {{ result.image_filename }}
                    <ul>
                      <li *ngFor="let error of result.errors">{{ error }}</li>
                    </ul>
                  </div>
                </mat-list-item>
              </mat-list>

              <button mat-button color="warn" (click)="downloadErrorReport()">
                <mat-icon>download</mat-icon>
                Download Error Report
              </button>
            </mat-card>

            <!-- Action Buttons -->
            <div class="actions">
              <button mat-button (click)="stepper.previous()">
                Back
              </button>

              <button mat-raised-button color="primary"
                      [disabled]="previewData.errors > 0 || loading"
                      (click)="confirmImport()">
                Import {{ previewData.valid }} Annotations
              </button>
            </div>
          </div>
        </mat-step>

        <!-- Step 3: Complete -->
        <mat-step>
          <ng-template matStepLabel>Complete</ng-template>

          <div class="success-message">
            <mat-icon color="primary">check_circle</mat-icon>
            <h3>Import Successful!</h3>
            <p>{{ importResult?.updated }} annotations imported.</p>

            <button mat-raised-button color="primary"
                    [mat-dialog-close]="true">
              Close
            </button>
          </div>
        </mat-step>
      </mat-stepper>
    </mat-dialog-content>
  `
})
export class ImportDialogComponent {
  selectedFile: File | null = null;
  previewData: any = null;
  importResult: any = null;
  loading = false;
  imported = false;

  constructor(
    private dialogRef: MatDialogRef<ImportDialogComponent>,
    private annotationsService: AnnotationsService,
    @Inject(MAT_DIALOG_DATA) public data: { projectId: string, datasetId: string }
  ) {}

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
  }

  async previewImport() {
    if (!this.selectedFile) return;

    this.loading = true;
    try {
      this.previewData = await this.annotationsService.previewImport(
        this.data.projectId,
        this.data.datasetId,
        this.selectedFile
      );
    } catch (error) {
      // Handle error
    } finally {
      this.loading = false;
    }
  }

  async confirmImport() {
    this.loading = true;
    try {
      this.importResult = await this.annotationsService.confirmImport(
        this.data.projectId,
        this.data.datasetId,
        this.selectedFile!
      );
      this.imported = true;
    } finally {
      this.loading = false;
    }
  }

  getErrorRows() {
    return this.previewData?.results.filter((r: any) => r.status === 'error') || [];
  }

  downloadErrorReport() {
    const errors = this.getErrorRows();
    const csv = this.generateErrorCSV(errors);
    this.downloadCSV(csv, 'import_errors.csv');
  }
}
```

### Phase 4: Testing & Polish (2 hours)

#### Test Cases:
1. **Export Tests**
   - [ ] Export empty dataset (0 annotations)
   - [ ] Export dataset with mix of annotated/unannotated images
   - [ ] Export with special characters in filenames
   - [ ] Open exported CSV in Excel - verify no formatting issues
   - [ ] Open exported CSV in Google Sheets - verify compatibility

2. **Import Tests**
   - [ ] Import binary labels: yes/no, true/false, 1/0, Y/N
   - [ ] Import with missing image_id (match by filename)
   - [ ] Import with invalid values (should show errors)
   - [ ] Import with duplicate filenames (should flag warning)
   - [ ] Import CSV edited in Excel (Windows-1252 encoding)
   - [ ] Import CSV edited in Google Sheets (UTF-8 with BOM)

3. **Edge Cases**
   - [ ] CSV with extra columns (should ignore)
   - [ ] CSV with missing required columns (should error)
   - [ ] CSV with 1000+ rows (performance test)
   - [ ] Simultaneous import attempts (concurrency)

---

## Implementation Sequence

### Sprint 1: Export & Template (1-2 days)
1. Add pandas to backend
2. Implement export endpoint
3. Implement template endpoint
4. Add export/template buttons to UI
5. Test Excel/Sheets compatibility

### Sprint 2: Import Preview (2-3 days)
1. Create validation service
2. Implement binary normalization
3. Create preview endpoint
4. Build import dialog UI
5. Add error reporting

### Sprint 3: Import Confirmation (1-2 days)
1. Implement confirm endpoint
2. Add transaction safety
3. Complete import dialog flow
4. Add success feedback

### Sprint 4: Testing & Polish (1 day)
1. End-to-end testing
2. Excel/Sheets compatibility testing
3. Error message improvements
4. Documentation

---

## Success Metrics

- [ ] Users can export/import without errors
- [ ] CSV opens correctly in Excel and Google Sheets
- [ ] All binary format variants (yes/no, 1/0, true/false) work correctly
- [ ] Import validation catches 100% of invalid data
- [ ] Average import time < 5 seconds for 100 annotations
- [ ] Zero data loss incidents during import

---

## Future Enhancements

1. **Bulk Operations**
   - Select multiple datasets to export at once
   - Merge imports from multiple CSVs

2. **Advanced Validation**
   - Image hash verification
   - Duplicate detection
   - Data quality scoring

3. **API Integration**
   - REST API for automated imports
   - Webhook support for external labeling tools
   - Watch folder for automated CSV processing
