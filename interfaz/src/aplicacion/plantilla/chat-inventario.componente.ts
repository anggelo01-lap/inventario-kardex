import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import {
  ChatbotHistorialItem,
  ChatbotMessageResponse,
  ChatbotOption,
  ChatbotSuggestion
} from '../nucleo/modelos/modelos-api';
import { AuthService } from '../nucleo/servicios/autenticacion.servicio';
import { ChatbotService } from '../nucleo/servicios/chatbot.servicio';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  html: SafeHtml;
  time: string;
  options?: ChatbotOption[];
}

@Component({
  selector: 'app-inventory-chat',
  templateUrl: './chat-inventario.componente.html',
  styleUrls: ['./chat-inventario.componente.scss'],
  standalone: false
})
export class ChatInventarioComponente implements OnInit {
  @ViewChild('messageList') private readonly messageList?: ElementRef<HTMLDivElement>;
  @ViewChild('promptInput') private readonly promptInput?: ElementRef<HTMLInputElement>;

  opened = false;
  loading = false;
  prompt = new FormControl('', { nonNullable: true, validators: [Validators.required] });
  suggestions: ChatbotSuggestion[] = [];
  showSuggestions = true;

  messages: ChatMessage[] = [
    this.buildMessage(
      'assistant',
      '👋 ¡Hola! Soy tu asistente de inventario. Puedo consultar stock, kardex, ventas, rankings y mucho más. ¿Qué necesitas?'
    )
  ];

  private contextoProductoId: number | null = null;
  private contextoProductoNombre: string | null = null;
  private readonly sessionId = this.loadSessionId();

  constructor(
    private readonly chatbot: ChatbotService,
    private readonly auth: AuthService,
    private readonly sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.chatbot.suggestions().subscribe({
      next: (items) => (this.suggestions = items),
      error: () => (this.suggestions = [])
    });
  }

  toggle(): void {
    this.opened = !this.opened;
    if (this.opened) {
      this.focusPrompt();
      this.scrollToBottom();
    }
  }

  send(event?: Event): void {
    event?.preventDefault();
    event?.stopPropagation();

    if (this.prompt.invalid || this.loading) {
      this.prompt.markAsTouched();
      return;
    }

    const pregunta = this.prompt.getRawValue().trim();
    if (!pregunta) {
      return;
    }

    this.sendMessage(pregunta);
  }

  useSuggestion(suggestion: ChatbotSuggestion): void {
    if (this.loading) return;
    this.sendMessage(suggestion.label);
    this.showSuggestions = false;
  }

  selectOption(option: ChatbotOption): void {
    if (this.loading) {
      return;
    }
    const userId = this.auth.getCurrentUser()?.id ?? 0;
    this.loading = true;
    this.messages = [...this.messages, this.buildMessage('user', `Selecciono: ${option.label}`)];
    this.chatbot
      .resolveOption({
        session_id: this.sessionId,
        selected_option_id: option.id,
        user_id: userId
      })
      .subscribe({
        next: (res: ChatbotMessageResponse) => this.handleChatbotResponse(res),
        error: () => {
          this.loading = false;
          this.messages = [
            ...this.messages,
            this.buildMessage('assistant', '❌ No pude resolver la opción seleccionada. Intenta nuevamente.')
          ];
          this.scrollToBottom();
          this.focusPrompt();
        }
      });
  }

  /** Convierte markdown básico a HTML seguro para renderizar en las burbujas */
  formatMarkdown(text: string): SafeHtml {
    let html = this.escapeHtml(text);

    // Saltos de línea
    html = html.replace(/\n/g, '<br>');

    // Negritas **texto**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Itálica _texto_
    html = html.replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>');

    // Viñetas con •
    html = html.replace(/^• /gm, '<span class="md-bullet">•</span> ');

    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private sendMessage(pregunta: string): void {
    this.messages = [...this.messages, this.buildMessage('user', pregunta)];
    this.prompt.setValue('');
    this.loading = true;
    this.showSuggestions = false;
    this.scrollToBottom();

    const historial: ChatbotHistorialItem[] = this.messages.slice(-8).map((message) => ({
      role: message.role,
      text: message.text
    }));

    const userId = this.auth.getCurrentUser()?.id ?? 0;
    this.chatbot
      .message({
        message: pregunta,
        session_id: this.sessionId,
        user_id: userId,
        historial,
        contexto_producto_id: this.contextoProductoId,
        contexto_producto_nombre: this.contextoProductoNombre
      })
      .subscribe({
        next: (res: ChatbotMessageResponse) => this.handleChatbotResponse(res),
        error: () => {
          this.loading = false;
          this.messages = [
            ...this.messages,
            this.buildMessage('assistant', '❌ No pude responder ahora mismo. Intenta de nuevo en unos segundos.')
          ];
          this.scrollToBottom();
          this.focusPrompt();
        }
      });
  }

  private buildMessage(role: ChatMessage['role'], text: string): ChatMessage {
    return {
      role,
      text,
      html: this.formatMarkdown(text),
      time: new Intl.DateTimeFormat('es-PE', {
        hour: '2-digit',
        minute: '2-digit'
      }).format(new Date())
    };
  }

  private handleChatbotResponse(res: ChatbotMessageResponse): void {
    this.loading = false;
    this.contextoProductoId = res.contexto_producto_id ?? this.contextoProductoId;
    this.contextoProductoNombre = res.contexto_producto_nombre ?? this.contextoProductoNombre;
    this.messages = [...this.messages, { ...this.buildMessage('assistant', res.answer), options: res.options ?? [] }];
    this.scrollToBottom();
    this.focusPrompt();
  }

  private loadSessionId(): string {
    const key = 'chatbot_session_id';
    const existing = localStorage.getItem(key);
    if (existing) {
      return existing;
    }
    const next = `chat_${Date.now()}`;
    localStorage.setItem(key, next);
    return next;
  }

  private focusPrompt(): void {
    setTimeout(() => this.promptInput?.nativeElement.focus(), 0);
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const container = this.messageList?.nativeElement;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }, 0);
  }
}
