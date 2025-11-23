import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from './core/services/auth.service';
import { LoginComponent } from './features/auth/login/login.component';

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
    MatDividerModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    LoginComponent
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'MLLM Benchmarking Platform';

  menuItems = [
    { icon: 'dashboard', label: 'Dashboard', route: '/home', adminOnly: false },
    { icon: 'folder', label: 'Projects', route: '/projects', adminOnly: false },
    { icon: 'edit_note', label: 'Annotations', route: '/annotations', adminOnly: false },
    { icon: 'science', label: 'Evaluations', route: '/evaluations', adminOnly: false }
  ];

  sidenavCollapsed = false;

  constructor(public authService: AuthService) {}

  toggleSidenav() {
    this.sidenavCollapsed = !this.sidenavCollapsed;
  }

  async logout(): Promise<void> {
    await this.authService.logout();
  }
}
