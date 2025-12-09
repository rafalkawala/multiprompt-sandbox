import { Component, OnInit, signal } from '@angular/core';
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
import { MatExpansionModule } from '@angular/material/expansion';
import { EvaluationsService, ModelConfigListItem, CreateModelConfig, PricingConfig } from '../../core/services/evaluations.service';

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
    MatChipsModule,
    MatExpansionModule
  ],
  template: `
    <div class="models-container">
      <h1>Model Configurations</h1>
      <p class="subtitle">Configure LLM providers for running evaluations</p>

      <!-- Create/Edit Config Form -->
      <mat-card class="create-card">
        <mat-card-header>
          <mat-card-title>{{ editingConfigId ? 'Edit Model' : 'Add New Model' }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Name</mat-label>
              <input matInput [(ngModel)]="newConfig.name" placeholder="My GPT-4o Config">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Provider</mat-label>
              <mat-select [(ngModel)]="newConfig.provider">
                <mat-option value="gemini">Google Gemini</mat-option>
                <mat-option value="openai">OpenAI</mat-option>
                <mat-option value="anthropic">Anthropic</mat-option>
              </mat-select>
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Model Name</mat-label>
              <input matInput [(ngModel)]="newConfig.model_name" [placeholder]="getModelPlaceholder()">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>API Key (optional for Gemini with service account)</mat-label>
              <input matInput [(ngModel)]="newConfig.api_key" type="password" placeholder="Leave empty to use service account">
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Temperature</mat-label>
              <input matInput type="number" [(ngModel)]="newConfig.temperature" min="0" max="2" step="0.1">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Max Tokens</mat-label>
              <input matInput type="number" [(ngModel)]="newConfig.max_tokens" min="1" max="4096">
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Concurrency</mat-label>
              <input matInput type="number" [(ngModel)]="newConfig.concurrency" min="1" max="100" step="1">
              <mat-hint>Number of parallel API calls (1-100, recommended: 3-10)</mat-hint>
            </mat-form-field>
          </div>

          <!-- Pricing Configuration -->
          <mat-expansion-panel class="pricing-panel">
            <mat-expansion-panel-header>
              <mat-panel-title>
                <mat-icon class="panel-icon">attach_money</mat-icon>
                Pricing & Cost Estimation
              </mat-panel-title>
              <mat-panel-description>
                Configure token rates for cost estimation
              </mat-panel-description>
            </mat-expansion-panel-header>

            <div class="pricing-actions">
              <button mat-stroked-button color="primary" (click)="loadPricingDefaults()">
                <mat-icon>download</mat-icon>
                Load Defaults for {{ getProviderLabel(newConfig.provider) }}
              </button>
            </div>

            <div class="form-row" *ngIf="newConfig.pricing_config">
              <mat-form-field appearance="outline">
                <mat-label>Input Price ($ per 1M tokens)</mat-label>
                <input matInput type="number" [(ngModel)]="newConfig.pricing_config.input_price_per_1m" step="0.01">
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Output Price ($ per 1M tokens)</mat-label>
                <input matInput type="number" [(ngModel)]="newConfig.pricing_config.output_price_per_1m" step="0.01">
              </mat-form-field>
            </div>

            <div class="form-row" *ngIf="newConfig.pricing_config">
              <mat-form-field appearance="outline">
                <mat-label>Image Pricing Mode</mat-label>
                <mat-select [(ngModel)]="newConfig.pricing_config.image_price_mode">
                  <mat-option value="per_image">Per Image</mat-option>
                  <mat-option value="per_tile">Per Tile (OpenAI)</mat-option>
                  <mat-option value="per_token">Per Token</mat-option>
                </mat-select>
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Image Price Value</mat-label>
                <input matInput type="number" [(ngModel)]="newConfig.pricing_config.image_price_val" step="0.00001">
                <mat-hint>Cost per image OR cost per 1M tokens (depending on mode)</mat-hint>
              </mat-form-field>
            </div>

            <div class="form-row" *ngIf="newConfig.pricing_config">
              <mat-form-field appearance="outline">
                <mat-label>Discount (%)</mat-label>
                <input matInput type="number" [(ngModel)]="newConfig.pricing_config.discount_percent" min="0" max="100">
                <mat-hint>Apply discount to total cost (e.g. for batch processing)</mat-hint>
              </mat-form-field>
            </div>
          </mat-expansion-panel>
        </mat-card-content>
        <mat-card-actions>
          @if (editingConfigId) {
            <button mat-button (click)="cancelEdit()">Cancel</button>
            <button mat-raised-button color="primary" (click)="saveConfig()" [disabled]="!isFormValid()">
              <mat-icon>save</mat-icon>
              Update Configuration
            </button>
          } @else {
            <button mat-raised-button color="primary" (click)="saveConfig()" [disabled]="!isFormValid()">
              <mat-icon>add</mat-icon>
              Add Configuration
            </button>
          }
        </mat-card-actions>
      </mat-card>

      <!-- Config List -->
      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (configs().length === 0) {
        <mat-card class="empty-state">
          <mat-icon>settings</mat-icon>
          <p>No model configurations yet. Add your first one above.</p>
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
                  </mat-chip-set>
                </mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <p><strong>Model:</strong> {{ config.model_name }}</p>
                <p><strong>Created:</strong> {{ config.created_at | date:'short' }}</p>
              </mat-card-content>
              <mat-card-actions>
                <button mat-button (click)="editConfig(config)">
                  <mat-icon>edit</mat-icon>
                  Edit
                </button>
                <button mat-button (click)="openTest(config)">
                  <mat-icon>play_arrow</mat-icon>
                  Test
                </button>
                <button mat-button color="warn" (click)="deleteConfig(config)">
                  <mat-icon>delete</mat-icon>
                  Delete
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

    h1 {
      margin: 0 0 8px;
      color: #202124;
    }

    .subtitle {
      color: #5f6368;
      margin: 0 0 24px;
    }

    .create-card {
      margin-bottom: 24px;
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 8px;

      mat-form-field {
        flex: 1;
      }
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

    .pricing-panel {
      margin-top: 16px;
      background: #f8f9fa;
    }

    .panel-icon {
      margin-right: 8px;
      color: #1a73e8;
    }

    .pricing-actions {
      margin-bottom: 16px;
      display: flex;
      justify-content: flex-end;
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
  configs = signal<ModelConfigListItem[]>([]);
  loading = signal(true);
  testing = signal(false);
  editingConfigId: string | null = null;

  newConfig: CreateModelConfig = {
    name: '',
    provider: 'gemini',
    model_name: '',
    api_key: '',
    temperature: 0,
    max_tokens: 1024,
    concurrency: 3,
    pricing_config: {
      input_price_per_1m: 0,
      output_price_per_1m: 0,
      image_price_mode: 'per_image',
      image_price_val: 0,
      discount_percent: 0
    }
  };

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

  loadConfigs() {
    this.loading.set(true);
    this.evaluationsService.getModelConfigs().subscribe({
      next: (configs) => {
        this.configs.set(configs);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load configs:', err);
        this.loading.set(false);
      }
    });
  }

  isFormValid(): boolean {
    return !!(this.newConfig.name && this.newConfig.provider && this.newConfig.model_name);
  }

  getModelPlaceholder(): string {
    switch (this.newConfig.provider) {
      case 'gemini': return 'gemini-1.5-pro';
      case 'openai': return 'gpt-4o';
      case 'anthropic': return 'claude-3-sonnet-20240229';
      default: return '';
    }
  }

  getProviderLabel(provider: string): string {
    const labels: Record<string, string> = {
      'gemini': 'Google Gemini',
      'openai': 'OpenAI',
      'anthropic': 'Anthropic'
    };
    return labels[provider] || provider;
  }

  editConfig(config: ModelConfigListItem) {
    this.editingConfigId = config.id;
    // Fetch full config details to get all fields
    this.evaluationsService.getModelConfig(config.id).subscribe({
      next: (fullConfig) => {
        this.newConfig = {
          name: fullConfig.name,
          provider: fullConfig.provider,
          model_name: fullConfig.model_name,
          api_key: '', // Don't populate API key for security
          temperature: fullConfig.temperature,
          max_tokens: fullConfig.max_tokens,
          concurrency: fullConfig.concurrency,
          pricing_config: fullConfig.pricing_config || {
            input_price_per_1m: 0,
            output_price_per_1m: 0,
            image_price_mode: 'per_image',
            image_price_val: 0,
            discount_percent: 0
          }
        };
      },
      error: (err) => {
        console.error('Failed to load config:', err);
        this.snackBar.open('Failed to load configuration', 'Close', { duration: 3000 });
      }
    });
  }

  cancelEdit() {
    this.editingConfigId = null;
    this.resetForm();
  }

  saveConfig() {
    if (!this.isFormValid()) return;

    if (this.editingConfigId) {
      // Update existing config
      this.evaluationsService.updateModelConfig(this.editingConfigId, this.newConfig).subscribe({
        next: (config) => {
          const index = this.configs().findIndex(c => c.id === config.id);
          if (index !== -1) {
            const updated = [...this.configs()];
            updated[index] = {
              id: config.id,
              name: config.name,
              provider: config.provider,
              model_name: config.model_name,
              is_active: config.is_active,
              created_at: config.created_at
            };
            this.configs.set(updated);
          }
          this.editingConfigId = null;
          this.resetForm();
          this.snackBar.open('Configuration updated', 'Close', { duration: 3000 });
        },
        error: (err) => {
          console.error('Failed to update config:', err);
          this.snackBar.open('Failed to update configuration', 'Close', { duration: 3000 });
        }
      });
    } else {
      // Create new config
      this.evaluationsService.createModelConfig(this.newConfig).subscribe({
        next: (config) => {
          this.configs.set([{
            id: config.id,
            name: config.name,
            provider: config.provider,
            model_name: config.model_name,
            is_active: config.is_active,
            created_at: config.created_at
          }, ...this.configs()]);
          this.resetForm();
          this.snackBar.open('Configuration created', 'Close', { duration: 3000 });
        },
        error: (err) => {
          console.error('Failed to create config:', err);
          this.snackBar.open('Failed to create configuration', 'Close', { duration: 3000 });
        }
      });
    }
  }

  deleteConfig(config: ModelConfigListItem) {
    if (!confirm(`Delete "${config.name}"?`)) return;

    this.evaluationsService.deleteModelConfig(config.id).subscribe({
      next: () => {
        this.configs.set(this.configs().filter(c => c.id !== config.id));
        this.snackBar.open('Configuration deleted', 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to delete config:', err);
        this.snackBar.open('Failed to delete configuration', 'Close', { duration: 3000 });
      }
    });
  }

  resetForm() {
    this.editingConfigId = null;
    this.newConfig = {
      name: '',
      provider: 'gemini',
      model_name: '',
      api_key: '',
      temperature: 0,
      max_tokens: 1024,
      concurrency: 3,
      pricing_config: {
        input_price_per_1m: 0,
        output_price_per_1m: 0,
        image_price_mode: 'per_image',
        image_price_val: 0,
        discount_percent: 0
      }
    };
  }

  loadPricingDefaults() {
    const provider = this.newConfig.provider;
    const model = this.newConfig.model_name.toLowerCase();

    if (!this.newConfig.pricing_config) {
      this.newConfig.pricing_config = {
        input_price_per_1m: 0,
        output_price_per_1m: 0,
        image_price_mode: 'per_image',
        image_price_val: 0,
        discount_percent: 0
      };
    }

    const pc = this.newConfig.pricing_config;

    if (provider === 'openai') {
      // GPT-4o
      if (model.includes('gpt-4o')) {
        pc.input_price_per_1m = 2.50;
        pc.output_price_per_1m = 10.00;
        pc.image_price_mode = 'per_tile';
        pc.image_price_val = 2.50; // Input price used for tiles
      } else if (model.includes('mini')) {
        pc.input_price_per_1m = 0.15;
        pc.output_price_per_1m = 0.60;
        pc.image_price_mode = 'per_tile';
        pc.image_price_val = 0.15;
      }
    } else if (provider === 'gemini') {
      // Gemini 1.5 Pro
      if (model.includes('pro')) {
        pc.input_price_per_1m = 3.50;
        pc.output_price_per_1m = 10.50;
        pc.image_price_mode = 'per_image';
        pc.image_price_val = 0.001315;
      } else if (model.includes('flash')) {
        pc.input_price_per_1m = 0.075;
        pc.output_price_per_1m = 0.30;
        pc.image_price_mode = 'per_image';
        pc.image_price_val = 0.00002;
      }
    } else if (provider === 'anthropic') {
      // Claude 3.5 Sonnet
      if (model.includes('sonnet')) {
        pc.input_price_per_1m = 3.00;
        pc.output_price_per_1m = 15.00;
        pc.image_price_mode = 'per_token'; // Approx
        pc.image_price_val = 3.00; // Use input price for tokens
      } else if (model.includes('haiku')) {
        pc.input_price_per_1m = 0.80;
        pc.output_price_per_1m = 4.00;
        pc.image_price_mode = 'per_token';
        pc.image_price_val = 0.80;
      }
    }

    this.snackBar.open(`Loaded pricing defaults for ${provider}`, 'Close', { duration: 2000 });
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
      next: (result) => {
        this.testResult = result;
        this.testing.set(false);
      },
      error: (err) => {
        console.error('Test failed:', err);
        this.testResult = {
          success: false,
          error: err.message || 'Unknown error'
        };
        this.testing.set(false);
      }
    });
  }
}
