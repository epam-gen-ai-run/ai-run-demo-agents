import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import https from 'https';

import { Assistant } from '../interfaces/types';

/** Default timeout for API requests in milliseconds */
const DEFAULT_TIMEOUT = 10000;

/** Default number of items per page for paginated requests */
const DEFAULT_PAGE_SIZE = 100;

/** API endpoint definitions */
const API_ENDPOINTS = {
  ASSISTANTS: '/assistants',
  ASSISTANT: (id: string) => `/a2a/assistants/${id}`,
  AGENT_CARD: (id: string) => `/a2a/assistants/${id}/.well-known/agent.json`
} as const;

/**
 * Represents pagination information for API responses
 * @interface
 */
interface Pagination {
  /** Current page number (1-based) */
  page: number;
  /** Number of items per page */
  per_page: number;
  /** Total number of items across all pages */
  total: number;
  /** Total number of pages */
  pages: number;
}

/**
 * Response type for the assistants API endpoint
 * @interface
 */
interface GetAssistantsResponse {
  /** Array of assistant objects */
  data: Assistant[];
  /** Pagination information */
  pagination: Pagination;
}

/**
 * Custom error class for API-related errors
 * @extends {Error}
 */
export class CodeMieApiError extends Error {
  /**
   * Creates a new CodeMieApiError
   * @param message - Error message
   * @param status - HTTP status code (if applicable)
   * @param code - Error code (if applicable)
   * @param data - Additional error data (if applicable)
   */
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public data?: unknown
  ) {
    super(message);
    this.name = 'CodeMieApiError';
  }
}

/**
 * HTTPS agent configuration for development environment
 * @warning Only use in development! Disables certificate validation
 */
const httpsAgent = new https.Agent({
  rejectUnauthorized: false // WARNING: Only use this in development!
});

/**
 * Configuration options for the CodeMieApiClient
 * @interface
 */
interface CodeMieApiClientConfig {
  /** Base URL for the API */
  baseUrl: string;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** OAuth2 proxy cookies for authentication */
  cookies?: string[];
  /** Additional HTTP headers */
  headers?: Record<string, string>;
}

/**
 * Service class for interacting with the CodeMie Assistants API
 * Handles authentication, request/response processing, and error handling
 */
export class CodeMieApiClient {
  private readonly baseUrl: string;
  private readonly apiClient: AxiosInstance;

  /**
   * Creates a new CodeMieApiClient instance
   * @param config - Configuration options for the client
   * @throws {CodeMieApiError} If the client configuration is invalid
   */
  constructor(config: CodeMieApiClientConfig) {
    this.baseUrl = config.baseUrl;
    this.apiClient = axios.create({
      baseURL: config.baseUrl,
      headers: {
        'Content-Type': 'application/json',
        'Cookie': config.cookies?.join(';') ?? '',
        ...config.headers
      },
      timeout: config.timeout ?? DEFAULT_TIMEOUT,
      httpsAgent
    });

    // Add response interceptor for error handling
    this.apiClient.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError<{ message?: string }>) => {
        if (error.response) {
          throw new CodeMieApiError(
            error.response.data?.message || 'API request failed',
            error.response.status,
            error.code,
            error.response.data
          );
        } else if (error.request) {
          throw new CodeMieApiError(
            'No response received from server',
            undefined,
            error.code
          );
        } else {
          throw new CodeMieApiError(
            error.message || 'Error setting up request',
            undefined,
            error.code
          );
        }
      }
    );
  }

  /**
   * Fetches all available assistants from the API
   * @returns {Promise<Assistant[]>} Array of assistant objects with their URLs
   * @throws {CodeMieApiError} If the request fails or response format is invalid
   * @throws {CodeMieApiError} With status 408 if the request times out
   * @throws {CodeMieApiError} With status 404 if the endpoint is not found
   */
  async fetchAssistants(): Promise<Assistant[]> {
    try {
      const response = await this.apiClient.get<GetAssistantsResponse>(
        API_ENDPOINTS.ASSISTANTS,
        { params: { per_page: DEFAULT_PAGE_SIZE } }
      );
      if (!Array.isArray(response.data.data)) {
        throw new CodeMieApiError('Invalid response format: data is not an array');
      }
      return response.data.data.map(a => ({
        ...a,
        url: `${this.baseUrl}${API_ENDPOINTS.ASSISTANT(a.id)}`,
        agentCardUrl: `${this.baseUrl}${API_ENDPOINTS.AGENT_CARD(a.id)}`
      }));
    } catch (error) {
      if (error instanceof AxiosError) {
        if (error.code === 'ECONNABORTED') {
          throw new CodeMieApiError('Request timed out', 408);
        }
        if (error.code === 'ENOTFOUND') {
          throw new CodeMieApiError('API endpoint not found', 404);
        }
      }
      throw error instanceof CodeMieApiError ? error : new CodeMieApiError('Failed to fetch assistants');
    }
  }

  /**
   * Fetches the agent card for a specific assistant
   * @param {string} url - The URL of the agent card to fetch
   * @returns {Promise<string>} The agent card content
   * @throws {CodeMieApiError} If the request fails or the agent card cannot be fetched
   */
  async fetchAssistantAgentCard(url: string): Promise<string> {
    try {
      const response = await this.apiClient.get(url);
      return response.data;
    } catch (error) {
      if (error instanceof CodeMieApiError) {
        throw error;
      }
      throw new CodeMieApiError('Failed to fetch assistant agent card');
    }
  }
}
