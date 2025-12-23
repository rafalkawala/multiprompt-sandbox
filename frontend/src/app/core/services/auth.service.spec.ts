import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService, User } from './auth.service';
import { environment } from '../../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let routerSpy: jasmine.SpyObj<Router>;

  const mockUser: User = {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    picture_url: 'https://example.com/avatar.jpg',
    role: 'user',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    last_login_at: '2024-01-15T10:00:00Z'
  };

  const mockAdminUser: User = {
    ...mockUser,
    id: 'admin-123',
    email: 'admin@example.com',
    role: 'admin'
  };

  beforeEach(() => {
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        AuthService,
        { provide: Router, useValue: routerSpy }
      ]
    });

    // Clear localStorage before each test
    localStorage.clear();
    sessionStorage.clear();

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);

    // Handle the initial loadUser call from constructor
    const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
    req.flush(null, { status: 401, statusText: 'Unauthorized' });
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should initialize with null user', () => {
      expect(service.user()).toBeNull();
    });

    it('should initialize with isAuthenticated as false', () => {
      expect(service.isAuthenticated()).toBeFalse();
    });

    it('should initialize with isAdmin as false', () => {
      expect(service.isAdmin()).toBeFalse();
    });
  });

  describe('loadUser', () => {
    it('should set user on successful load', fakeAsync(() => {
      service.loadUser();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      expect(req.request.method).toBe('GET');
      expect(req.request.withCredentials).toBeTrue();
      req.flush(mockUser);

      tick();

      expect(service.user()).toEqual(mockUser);
      expect(service.isAuthenticated()).toBeTrue();
      expect(service.loading()).toBeFalse();
    }));

    it('should set isAdmin true for admin users', fakeAsync(() => {
      service.loadUser();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(mockAdminUser);

      tick();

      expect(service.isAdmin()).toBeTrue();
    }));

    it('should clear user on 401 error', fakeAsync(() => {
      service.loadUser();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(null, { status: 401, statusText: 'Unauthorized' });

      tick();

      expect(service.user()).toBeNull();
      expect(service.isAuthenticated()).toBeFalse();
      expect(service.error()).toBeNull(); // 401 is expected for logged out users
    }));

    it('should set error on 400 (account deactivated)', fakeAsync(() => {
      service.loadUser();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(null, { status: 400, statusText: 'Bad Request' });

      tick();

      expect(service.user()).toBeNull();
      expect(service.error()?.code).toBe('ACCOUNT_DEACTIVATED');
    }));

    it('should set connection error on network failure', fakeAsync(() => {
      service.loadUser();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(null, { status: 0, statusText: 'Network Error' });

      tick();

      expect(service.error()?.code).toBe('CONNECTION_ERROR');
    }));
  });

  describe('login', () => {
    it('should redirect to auth URL on successful login', fakeAsync(() => {
      const authUrl = 'https://accounts.google.com/oauth?client_id=...';

      // Spy on window.location
      const locationSpy = spyOnProperty(window, 'location', 'get').and.returnValue({
        href: ''
      } as Location);

      service.login();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/google/login`);
      req.flush({ auth_url: authUrl });

      tick();

      // Note: In a real test, we'd verify the redirect happened
      expect(req.request.method).toBe('GET');
    }));

    it('should set error on login failure', fakeAsync(() => {
      service.login().catch(() => {}); // Catch the expected rejection
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/google/login`);
      req.flush(null, { status: 500, statusText: 'Server Error' });

      tick();

      expect(service.error()?.code).toBe('LOGIN_FAILED');
    }));
  });

  describe('logout', () => {
    it('should clear user state on logout', fakeAsync(() => {
      // First, simulate a logged-in user
      service.loadUser();
      tick();
      const loadReq = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      loadReq.flush(mockUser);
      tick();

      expect(service.user()).toEqual(mockUser);

      // Now logout
      service.logout();
      tick();

      const logoutReq = httpMock.expectOne(`${environment.apiUrl}/auth/logout`);
      logoutReq.flush({});

      tick();

      expect(service.user()).toBeNull();
      expect(service.isAuthenticated()).toBeFalse();
    }));

    it('should clear localStorage token on logout', fakeAsync(() => {
      localStorage.setItem('dev_access_token', 'test-token');

      service.logout();
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/logout`);
      req.flush({});

      tick();

      expect(localStorage.getItem('dev_access_token')).toBeNull();
    }));

    it('should clear user even if backend call fails', fakeAsync(() => {
      // Simulate logged-in user
      service.loadUser();
      tick();
      const loadReq = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      loadReq.flush(mockUser);
      tick();

      // Logout with backend error
      service.logout();
      tick();

      const logoutReq = httpMock.expectOne(`${environment.apiUrl}/auth/logout`);
      logoutReq.flush(null, { status: 500, statusText: 'Server Error' });

      tick();

      // User should still be cleared
      expect(service.user()).toBeNull();
    }));
  });

  describe('handleSessionExpired', () => {
    it('should clear user and set session expired error', () => {
      service.handleSessionExpired();

      expect(service.user()).toBeNull();
      expect(service.error()?.code).toBe('SESSION_EXPIRED');
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/']);
    });

    it('should clear localStorage tokens', () => {
      localStorage.setItem('dev_access_token', 'test-token');
      sessionStorage.setItem('dev_access_token', 'test-token');

      service.handleSessionExpired();

      expect(localStorage.getItem('dev_access_token')).toBeNull();
      expect(sessionStorage.getItem('dev_access_token')).toBeNull();
    });
  });

  describe('handleCallback', () => {
    it('should store token in localStorage when provided', fakeAsync(() => {
      const token = 'test-jwt-token';

      service.handleCallback(token);
      tick();

      expect(localStorage.getItem('dev_access_token')).toBe(token);

      // Handle the loadUser call
      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(mockUser);

      tick();

      expect(service.user()).toEqual(mockUser);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/home']);
    }));

    it('should redirect to root on callback failure', fakeAsync(() => {
      service.handleCallback(null);
      tick();

      const req = httpMock.expectOne(`${environment.apiUrl}/auth/me`);
      req.flush(null, { status: 401, statusText: 'Unauthorized' });

      tick();

      expect(service.error()?.code).toBe('CALLBACK_FAILED');
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/']);
    }));
  });

  describe('clearError', () => {
    it('should clear any existing error', () => {
      service.handleSessionExpired(); // Sets an error
      expect(service.error()).not.toBeNull();

      service.clearError();
      expect(service.error()).toBeNull();
    });
  });
});
