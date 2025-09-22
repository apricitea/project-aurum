export interface ErrorDetails {
  message: string;
  code?: string;
  status?: number;
  details?: any;
  timestamp: string;
  context?: string;
}

export class AppError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details: any;
  public readonly timestamp: string;
  public readonly context: string;

  constructor(
    message: string,
    code: string = 'UNKNOWN_ERROR',
    status: number = 500,
    details?: any,
    context?: string
  ) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.status = status;
    this.details = details;
    this.timestamp = new Date().toISOString();
    this.context = context || 'Unknown';
  }
}

export class ApiError extends AppError {
  constructor(message: string, status: number, details?: any) {
    super(message, 'API_ERROR', status, details, 'API');
  }
}

export class AuthError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 'AUTH_ERROR', 401, details, 'Authentication');
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 'VALIDATION_ERROR', 400, details, 'Validation');
  }
}

export class NetworkError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 'NETWORK_ERROR', 0, details, 'Network');
  }
}