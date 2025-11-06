import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatDividerModule
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'MLLM Benchmarking Platform';

  menuItems = [
    { icon: 'dashboard', label: 'Dashboard', route: '/home' },
    { icon: 'folder', label: 'Projects', route: '/projects' },
    { icon: 'cloud_upload', label: 'Datasets', route: '/datasets' },
    { icon: 'label', label: 'Labeling', route: '/labeling' },
    { icon: 'edit_note', label: 'Prompts', route: '/prompts' },
    { icon: 'science', label: 'Experiments', route: '/experiments' },
    { icon: 'analytics', label: 'Results', route: '/results' }
  ];
}
