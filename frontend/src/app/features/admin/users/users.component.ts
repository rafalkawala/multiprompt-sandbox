import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { AdminService, AdminUser } from '../../../core/services/admin.service';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCardModule,
    MatChipsModule,
    MatTooltipModule,
    MatDialogModule,
    MatInputModule,
    MatFormFieldModule
  ],
  template: `
    <div class="admin-container">
      <mat-card>
        <mat-card-header>
          <mat-card-title>User Management</mat-card-title>
          <mat-card-subtitle>Manage user roles and access</mat-card-subtitle>
        </mat-card-header>

        <!-- Add User Form -->
        <div class="add-user-form">
          <mat-form-field appearance="outline">
            <mat-label>Email</mat-label>
            <input matInput [(ngModel)]="newUserEmail" placeholder="user@example.com">
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Role</mat-label>
            <mat-select [(ngModel)]="newUserRole">
              <mat-option value="admin">Admin</mat-option>
              <mat-option value="user">User</mat-option>
              <mat-option value="viewer">Viewer</mat-option>
            </mat-select>
          </mat-form-field>
          <button mat-raised-button color="primary" (click)="addUser()" [disabled]="!newUserEmail">
            <mat-icon>person_add</mat-icon>
            Add User
          </button>
        </div>
        <mat-card-content>
          @if (loading()) {
            <div class="loading-container">
              <mat-spinner diameter="40"></mat-spinner>
            </div>
          } @else {
            <table mat-table [dataSource]="users()" class="users-table">
              <ng-container matColumnDef="email">
                <th mat-header-cell *matHeaderCellDef>Email</th>
                <td mat-cell *matCellDef="let user">{{ user.email }}</td>
              </ng-container>

              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef>Name</th>
                <td mat-cell *matCellDef="let user">{{ user.name || '-' }}</td>
              </ng-container>

              <ng-container matColumnDef="role">
                <th mat-header-cell *matHeaderCellDef>Role</th>
                <td mat-cell *matCellDef="let user">
                  <mat-select
                    [value]="user.role"
                    (selectionChange)="onRoleChange(user, $event.value)"
                    class="role-select">
                    <mat-option value="admin">Admin</mat-option>
                    <mat-option value="user">User</mat-option>
                    <mat-option value="viewer">Viewer</mat-option>
                  </mat-select>
                </td>
              </ng-container>

              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let user">
                  <mat-chip [class.active]="user.is_active" [class.inactive]="!user.is_active">
                    {{ user.is_active ? 'Active' : 'Inactive' }}
                  </mat-chip>
                </td>
              </ng-container>

              <ng-container matColumnDef="lastLogin">
                <th mat-header-cell *matHeaderCellDef>Last Login</th>
                <td mat-cell *matCellDef="let user">
                  {{ user.last_login_at ? (user.last_login_at | date:'short') : 'Never' }}
                </td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Actions</th>
                <td mat-cell *matCellDef="let user">
                  <button
                    mat-icon-button
                    [color]="user.is_active ? 'warn' : 'primary'"
                    (click)="toggleActive(user)"
                    [matTooltip]="user.is_active ? 'Deactivate' : 'Activate'">
                    <mat-icon>{{ user.is_active ? 'block' : 'check_circle' }}</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          }
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .admin-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .add-user-form {
      display: flex;
      gap: 16px;
      align-items: center;
      padding: 16px 24px;
      background: #f5f5f5;
      margin: 0 -16px;
    }

    .add-user-form mat-form-field {
      flex: 1;
    }

    .users-table {
      width: 100%;
    }

    .role-select {
      width: 100px;
    }

    mat-chip.active {
      background-color: #e8f5e9 !important;
      color: #2e7d32 !important;
    }

    mat-chip.inactive {
      background-color: #ffebee !important;
      color: #c62828 !important;
    }

    th.mat-header-cell {
      font-weight: 600;
    }
  `]
})
export class AdminUsersComponent implements OnInit {
  users = signal<AdminUser[]>([]);
  loading = signal(true);
  displayedColumns = ['email', 'name', 'role', 'status', 'lastLogin', 'actions'];

  newUserEmail = '';
  newUserRole = 'user';

  constructor(
    private adminService: AdminService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.adminService.getUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load users:', err);
        this.snackBar.open('Failed to load users', 'Close', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  onRoleChange(user: AdminUser, newRole: string) {
    this.adminService.updateUser(user.id, { role: newRole }).subscribe({
      next: (updated) => {
        const currentUsers = this.users();
        const index = currentUsers.findIndex(u => u.id === user.id);
        if (index !== -1) {
          currentUsers[index] = updated;
          this.users.set([...currentUsers]);
        }
        this.snackBar.open(`Role updated for ${user.email}`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to update role:', err);
        this.snackBar.open('Failed to update role', 'Close', { duration: 3000 });
        this.loadUsers(); // Reload to reset
      }
    });
  }

  toggleActive(user: AdminUser) {
    this.adminService.updateUser(user.id, { is_active: !user.is_active }).subscribe({
      next: (updated) => {
        const currentUsers = this.users();
        const index = currentUsers.findIndex(u => u.id === user.id);
        if (index !== -1) {
          currentUsers[index] = updated;
          this.users.set([...currentUsers]);
        }
        this.snackBar.open(
          `User ${updated.is_active ? 'activated' : 'deactivated'}`,
          'Close',
          { duration: 3000 }
        );
      },
      error: (err) => {
        console.error('Failed to toggle user status:', err);
        this.snackBar.open('Failed to update user status', 'Close', { duration: 3000 });
      }
    });
  }

  addUser() {
    if (!this.newUserEmail) return;

    this.adminService.createUser(this.newUserEmail, this.newUserRole).subscribe({
      next: (user) => {
        this.users.set([user, ...this.users()]);
        this.newUserEmail = '';
        this.newUserRole = 'user';
        this.snackBar.open(`User ${user.email} created`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to create user:', err);
        this.snackBar.open(err.error?.detail || 'Failed to create user', 'Close', { duration: 3000 });
      }
    });
  }
}
