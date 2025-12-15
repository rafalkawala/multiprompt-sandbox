import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class BaseApiService {
  protected readonly API_URL = environment.apiUrl;

  constructor(protected http: HttpClient) {}

  protected get<T>(path: string, params?: any): Observable<T> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
          httpParams = httpParams.append(key, params[key]);
        }
      });
    }
    return this.http.get<T>(`${this.API_URL}${path}`, { params: httpParams });
  }

  protected post<T>(path: string, body: any, options?: any): Observable<T> {
    return this.http.post<T>(`${this.API_URL}${path}`, body, options);
  }

  protected patch<T>(path: string, body: any): Observable<T> {
    return this.http.patch<T>(`${this.API_URL}${path}`, body);
  }

  protected put<T>(path: string, body: any): Observable<T> {
    return this.http.put<T>(`${this.API_URL}${path}`, body);
  }

  protected delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(`${this.API_URL}${path}`);
  }
}
