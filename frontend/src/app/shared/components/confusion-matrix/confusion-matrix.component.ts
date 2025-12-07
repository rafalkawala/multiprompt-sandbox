import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTooltipModule } from '@angular/material/tooltip';

export interface ConfusionMatrix {
  tp: number;
  tn: number;
  fp: number;
  fn: number;
}

@Component({
  selector: 'app-confusion-matrix',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatTooltipModule],
  template: `
    @if (matrix) {
      <div class="matrix-container">
        <!-- Predicted True Column -->
        <div class="matrix-cell tp" matTooltip="True Positive (Correctly Predicted Yes)">
          <span class="label">TP</span>
          <span class="value">{{ matrix.tp }}</span>
        </div>
        
        <!-- Predicted False Column -->
        <div class="matrix-cell fn" matTooltip="False Negative (Incorrectly Predicted No)">
          <span class="label">FN</span>
          <span class="value">{{ matrix.fn }}</span>
        </div>

        <!-- Row 2 -->
        <div class="matrix-cell fp" matTooltip="False Positive (Incorrectly Predicted Yes)">
          <span class="label">FP</span>
          <span class="value">{{ matrix.fp }}</span>
        </div>
        
        <div class="matrix-cell tn" matTooltip="True Negative (Correctly Predicted No)">
          <span class="label">TN</span>
          <span class="value">{{ matrix.tn }}</span>
        </div>

        <!-- Axis Labels (Absolute positioning or Grid areas could work better, but keeping it simple) -->
        <div class="axis-label x-axis">Predicted</div>
        <div class="axis-label y-axis">Actual</div>
      </div>
    } @else {
      <div class="no-data">No Data</div>
    }
  `,
  styles: [`
    .matrix-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 4px;
      width: 140px;
      height: 140px;
      position: relative;
      background: #f0f0f0;
      padding: 4px;
      border-radius: 4px;
    }

    .matrix-cell {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      font-size: 14px;
      font-weight: bold;
      cursor: help;
      transition: opacity 0.2s;
    }

    .tp { background-color: #e6f4ea; color: #137333; } /* Green */
    .tn { background-color: #e6f4ea; color: #137333; } /* Green */
    .fp { background-color: #fce8e6; color: #c5221f; } /* Red */
    .fn { background-color: #fce8e6; color: #c5221f; } /* Red */

    .label {
      font-size: 10px;
      opacity: 0.7;
      margin-bottom: 2px;
    }

    .value {
      font-size: 16px;
    }

    .no-data {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100px;
      color: #999;
      font-style: italic;
    }
    
    /* Simple Axis labels overlay */
    .axis-label {
      position: absolute;
      font-size: 9px;
      color: #666;
      text-transform: uppercase;
      pointer-events: none;
    }
    
    .x-axis {
      bottom: -14px;
      left: 0;
      right: 0;
      text-align: center;
    }
    
    .y-axis {
      top: 50%;
      left: -20px;
      transform: translateY(-50%) rotate(-90deg);
    }
  `]
})
export class ConfusionMatrixComponent {
  @Input() matrix: ConfusionMatrix | null | undefined = null;
}
