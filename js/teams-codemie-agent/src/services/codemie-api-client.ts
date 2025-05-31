import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import https from 'https';

import { Assistant } from '../interfaces/types';


// Pagination information
interface Pagination {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

interface GetAssistantsRequest {
  scope: string;
  minimal_response: boolean;
  page: number;
  per_page: number;
}

// Complete API response type
interface GetAssistantsResponse {
  data: Assistant[];
  pagination: Pagination;
}

/**
 * Custom error class for API errors
 */
export class CodeMieApiError extends Error {
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

// Create a custom HTTPS agent that ignores certificate errors
const httpsAgent = new https.Agent({
  rejectUnauthorized: false // WARNING: Only use this in development!
});

/**
 * Service class for handling Assistants API operations
 */
export class CodeMieApiClient {
  private readonly baseUrl: string;
  private readonly apiClient: AxiosInstance;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
    // const cookie1 = '';
    // const cookie2 = '';
    // Create axios instance with default config
    this.apiClient = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
        // 'Cookie': `_oauth2_proxy_0=${cookie1}; _oauth2_proxy_1=${cookie2}`
        // Add any required authentication headers here
      },
      // Add default timeout
      timeout: 10000,
      httpsAgent,
    });

    // Add response interceptor for error handling
    this.apiClient.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError<{ message?: string }>) => {
        if (error.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          throw new CodeMieApiError(
            error.response.data?.message || 'API request failed',
            error.response.status,
            error.code,
            error.response.data
          );
        } else if (error.request) {
          // The request was made but no response was received
          throw new CodeMieApiError(
            'No response received from server',
            undefined,
            error.code
          );
        } else {
          // Something happened in setting up the request
          throw new CodeMieApiError(
            error.message || 'Error setting up request',
            undefined,
            error.code
          );
        }
      }
    );
  }

  async fetchAssistants(): Promise<Assistant[]> {
    try {
      const response = await this.apiClient.get<GetAssistantsResponse>(
        '/assistants',
        { params: { per_page: 100 } }
      );
      return response.data.data.map(a => ({
        ...a,
        agentCardUrl: `${this.baseUrl}/a2a/assistants/${a.id}/.well-known/agent.json`
      }));
    } catch (error) {
      if (error instanceof CodeMieApiError) {
        throw error;
      }
      throw new CodeMieApiError('Failed to fetch assistants');
    }
  }
}
