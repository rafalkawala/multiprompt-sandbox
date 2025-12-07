import { Component, signal } from '@angular/core';
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
import { BreakpointObserver } from '@angular/cdk/layout';
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
    { icon: 'science', label: 'Evaluations', route: '/evaluations', adminOnly: false },
    { icon: 'compare_arrows', label: 'Compare Evals', route: '/evaluations/compare', adminOnly: false },
    { icon: 'work_outline', label: 'Labelling Jobs', route: '/labelling-jobs', adminOnly: false }
  ];

  sidenavCollapsed = false;
  isMobile = signal(false);
  isTablet = signal(false);

  constructor(
    public authService: AuthService,
    private breakpointObserver: BreakpointObserver
  ) {
    // Observe mobile and tablet breakpoints
    this.breakpointObserver.observe([
      '(max-width: 767px)',
      '(min-width: 768px) and (max-width: 1023px)'
    ]).subscribe(result => {
      this.isMobile.set(result.breakpoints['(max-width: 767px)']);
      this.isTablet.set(result.breakpoints['(min-width: 768px) and (max-width: 1023px)']);
    });
  }

  // Sidenav should be 'over' mode on mobile, 'side' on desktop
  get sidenavMode(): 'side' | 'over' {
    return this.isMobile() ? 'over' : 'side';
  }

  // Sidenav should be closed by default on mobile, open on desktop
  get sidenavOpened(): boolean {
    return !this.isMobile();
  }

  toggleSidenav() {
    this.sidenavCollapsed = !this.sidenavCollapsed;
  }

  async logout(): Promise<void> {
    await this.authService.logout();
  }
}
