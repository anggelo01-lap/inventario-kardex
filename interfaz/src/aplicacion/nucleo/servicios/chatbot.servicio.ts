import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../entornos/entorno';
import {
  ChatbotConsultaIn,
  ChatbotConsultaOut,
  ChatbotMessageRequest,
  ChatbotMessageResponse,
  ChatbotResolveOptionRequest,
  ChatbotSuggestion
} from '../modelos/modelos-api';

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private readonly base = `${environment.apiUrl}/chatbot`;

  constructor(private readonly http: HttpClient) {}

  consultar(payload: ChatbotConsultaIn): Observable<ChatbotConsultaOut> {
    return this.http.post<ChatbotConsultaOut>(`${this.base}/consultar`, payload);
  }

  message(payload: ChatbotMessageRequest): Observable<ChatbotMessageResponse> {
    return this.http.post<ChatbotMessageResponse>(`${this.base}/message`, payload);
  }

  resolveOption(payload: ChatbotResolveOptionRequest): Observable<ChatbotMessageResponse> {
    return this.http.post<ChatbotMessageResponse>(`${this.base}/resolve-option`, payload);
  }

  suggestions(): Observable<ChatbotSuggestion[]> {
    return this.http.get<ChatbotSuggestion[]>(`${this.base}/suggestions`);
  }
}
