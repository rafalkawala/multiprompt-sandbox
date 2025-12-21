import { Component, OnInit, signal, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { EvaluationsService, ModelConfigListItem } from '../../core/services/evaluations.service';

@Component({
  selector: 'app-models',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatChipsModule
  ],
  template: `
    <div class="models-container">
      <div class="header-row">
        <div>
          <h1>Model Configurations</h1>
          <p class="subtitle">Configure LLM providers via Import/Export (Read-Only)</p>
        </div>
        <div class="actions-row">
          <button mat-stroked-button color="primary" (click)="onExport()">
            <mat-icon>download</mat-icon>
            Export Configs
          </button>
          <button mat-stroked-button color="primary" (click)="triggerImport()">
            <mat-icon>upload</mat-icon>
            Import Configs
          </button>
          <input #fileInput type="file" hidden (change)="onImport($event)" accept=".json">
        </div>
      </div>

      <!-- Config List -->
      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (configs().length === 0) {
        <mat-card class="empty-state">
          <mat-icon>settings</mat-icon>
          <p>No model configurations found. Import a configuration file to get started.</p>
        </mat-card>
      } @else {
        <div class="configs-grid">
          @for (config of configs(); track config.id) {
            <mat-card class="config-card">
              <mat-card-header>
                <mat-card-title>{{ config.name }}</mat-card-title>
                <mat-card-subtitle>
                  <mat-chip-set>
                    <mat-chip [highlighted]="true">{{ getProviderLabel(config.provider) }}</mat-chip>
                    @if (config.auth_type) {
                      <mat-chip>{{ getAuthTypeLabel(config.auth_type) }}</mat-chip>
                    }
                  </mat-chip-set>
                </mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <p><strong>Model:</strong> {{ config.model_name }}</p>
                <p><strong>Created:</strong> {{ config.created_at | date:'short' }}</p>
              </mat-card-content>
              <mat-card-actions>
                <button mat-button (click)="openTest(config)">
                  <mat-icon>play_arrow</mat-icon>
                  Test
                </button>
              </mat-card-actions>
            </mat-card>
          }
        </div>
      }

      <!-- Test Panel -->
      @if (testConfigId) {
        <mat-card class="test-card">
          <mat-card-header>
            <mat-card-title>Test Model</mat-card-title>
            <mat-card-subtitle>{{ getConfigName(testConfigId) }}</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Prompt</mat-label>
              <textarea matInput [(ngModel)]="testPrompt" rows="3" placeholder="Enter a test prompt..."></textarea>
            </mat-form-field>

            @if (testResult) {
              <div class="test-result" [class.success]="testResult.success" [class.error]="!testResult.success">
                <div class="result-header">
                  @if (testResult.success) {
                    <mat-icon>check_circle</mat-icon>
                    <span>Success</span>
                  } @else {
                    <mat-icon>error</mat-icon>
                    <span>Error</span>
                  }
                  @if (testResult.latency_ms) {
                    <span class="latency">{{ testResult.latency_ms }}ms</span>
                  }
                </div>
                <div class="result-content">
                  @if (testResult.response) {
                    <pre>{{ testResult.response }}</pre>
                  }
                  @if (testResult.error) {
                    <pre class="error-text">{{ testResult.error }}</pre>
                  }
                </div>
              </div>
            }
          </mat-card-content>
          <mat-card-actions>
            <button mat-button (click)="closeTest()">Close</button>
            <button mat-raised-button color="primary" (click)="runTest()" [disabled]="!testPrompt || testing()">
              @if (testing()) {
                <mat-spinner diameter="20"></mat-spinner>
              } @else {
                <mat-icon>send</mat-icon>
                Send
              }
            </button>
          </mat-card-actions>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .models-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .actions-row {
      display: flex;
      gap: 12px;
    }

    h1 {
      margin: 0 0 8px;
      color: #202124;
    }

    .subtitle {
      color: #5f6368;
      margin: 0 0 24px;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      color: #5f6368;

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    }

    .configs-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }

    .config-card {
      mat-card-subtitle {
        margin-top: 8px;
      }

      mat-card-content p {
        margin: 8px 0;
        color: #5f6368;
      }
    }

    .test-card {
      margin-top: 24px;
      border: 2px solid #1967d2;
    }

    .full-width {
      width: 100%;
    }

    .test-result {
      margin-top: 16px;
      padding: 16px;
      border-radius: 8px;

      &.success {
        background: #e6f4ea;
        border: 1px solid #34a853;
      }

      &.error {
        background: #fce8e6;
        border: 1px solid #ea4335;
      }

      .result-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        font-weight: 500;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
        }

        .latency {
          margin-left: auto;
          color: #5f6368;
          font-weight: normal;
        }
      }

      .result-content {
        pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: inherit;
          font-size: 14px;
        }

        .error-text {
          color: #c5221f;
        }
      }
    }
  `]
})
export class ModelsComponent implements OnInit {
  configs = signal<any[]>([]);
  loading = signal(true);
  testing = signal(false);
  
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  // Test state
  testConfigId: string | null = null;
  testPrompt = 'Hello! Please respond with a short greeting.';
  testResult: {success: boolean, response?: string, error?: string, latency_ms?: number} | null = null;

  constructor(
    private evaluationsService: EvaluationsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadConfigs();
  }
  
  triggerImport() {
    this.fileInput.nativeElement.click();
  }

  loadConfigs() {
    this.loading.set(true);
    this.evaluationsService.getModelConfigs().subscribe({
      next: (configs: any[]) => {
        this.configs.set(configs);
        this.loading.set(false);
      },
      error: (err: any) => {
        console.error('Failed to load configs:', err);
        this.loading.set(false);
      }
    });
  }

  getProviderLabel(provider: string): string {
    const labels: Record<string, string> = {
      'gemini': 'Google Gemini',
      'openai': 'OpenAI',
      'anthropic': 'Anthropic'
    };
    return labels[provider] || provider;
  }

  getAuthTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      'api_key': 'API Key',
      'google_adc': 'App Account',
      'service_account': 'Service Account'
    };
    return labels[type] || type;
  }

  // Test methods
  openTest(config: ModelConfigListItem) {
    this.testConfigId = config.id;
    this.testResult = null;
  }

  closeTest() {
    this.testConfigId = null;
    this.testResult = null;
  }

  getConfigName(id: string): string {
    const config = this.configs().find(c => c.id === id);
    return config ? `${config.name} (${config.model_name})` : '';
  }

  runTest() {
    if (!this.testConfigId || !this.testPrompt) return;

    this.testing.set(true);
    this.testResult = null;

    this.evaluationsService.testModelConfig(this.testConfigId, this.testPrompt).subscribe({
      next: (result: any) => {
        this.testResult = result;
        this.testing.set(false);
      },
      error: (err: any) => {
        console.error('Test failed:', err);
        this.testResult = {
          success: false,
          error: err.message || 'Unknown error'
        };
        this.testing.set(false);
      }
    });
  }

  onExport() {
    this.evaluationsService.exportModelConfigs().subscribe({
      next: (blob: any) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'model_configs_export.json';
        link.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err: any) => {
        console.error('Export failed:', err);
        this.snackBar.open('Failed to export configurations', 'Close', { duration: 3000 });
      }
    });
  }

  onImport(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.evaluationsService.importModelConfigs(file).subscribe({
        next: (res: any) => {
          this.snackBar.open(res.message, 'Close', { duration: 3000 });
          this.loadConfigs(); // Refresh list
          input.value = ''; // Reset input
        },
        error: (err: any) => {
          console.error('Import failed:', err);
          this.snackBar.open('Failed to import configurations', 'Close', { duration: 3000 });
          input.value = ''; // Reset input
        }
      });
    }
  }
}