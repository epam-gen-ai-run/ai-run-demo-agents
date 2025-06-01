import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { ChatPrompt, ObjectSchema } from '@microsoft/teams.ai';
import { OpenAIChatModelOptions, OpenAIChatModel } from '@microsoft/teams.openai';
import { env } from '../config/env';
import { CodeMieApiClient } from '../services/codemie-api-client';
import { AgentManager, AgentCard } from '@microsoft/teams.a2a';
import { v4 as uuidv4 } from 'uuid';
import { Assistant } from '../interfaces/types';

const BOT_CONFIG = {
  TYPING_DELAY: 1000,
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000,
  DEFAULT_ERROR_MESSAGE: "I'm sorry, I couldn't process that request."
} as const;

const describeAssistantSchema = {
  type: 'object',
  properties: {
      assistantName: {
          type: 'string',
          description: 'the name of the assistant to describe',
      },
  },
  required: ['assistantName'],
} as ObjectSchema;

const sendRequestSchema = {
  type: 'object',
  properties: {
      assistantName: {
          type: 'string',
          description: 'the name of the assistant to call',
      },
      request: {
          type: 'string',
          description: 'the request to send to the assistant',
      },
  },
  required: ['assistantName', 'request'],
} as ObjectSchema;

// Add custom error types
class AssistantNotFoundError extends Error {
  constructor(assistantName: string) {
    super(`Assistant "${assistantName}" not found`);
    this.name = 'AssistantNotFoundError';
  }
}

// Add proper return types for functions
interface TaskResponse {
  id: string;
  status: 'success' | 'error';
  message: string;
  url?: string;
}

class AssistantManager {
  private assistants: Map<string, Assistant> = new Map();
  private agentManager: AgentManager;

  constructor(private codemie: CodeMieApiClient) {
    this.agentManager = new AgentManager();
  }

  async initialize(): Promise<void> {
    const assistants = await this.codemie.fetchAssistants();
    console.log(`Found ${assistants.length} assistants`);
  }

  findAssistant(name: string): Assistant | undefined {
    return this.assistants.get(name);
  }

  getAllAssistants(): Assistant[] {
    return Array.from(this.assistants.values());
  }

  async getAssistantAgentCard(name: string): Promise<AgentCard> {
    const assistant = this.findAssistant(name);
    if (!assistant) {
      throw new AssistantNotFoundError(name);
    }
    return this.codemie.fetchAssistantAgentCard(assistant.url);
  }

  async sendTaskToAssistant(name: string, request: string): Promise<TaskResponse> {
    const assistant = this.findAssistant(name);
    if (!assistant) {
      throw new AssistantNotFoundError(name);
    }

    const taskId = uuidv4();
    const task = await this.codemie.fetchAssistantAgentCard(assistant.url)
      .then(agentCard => {
        console.log(`Agent card: ${JSON.stringify(agentCard)}`);

        this.agentManager.use(assistant.id, agentCard.url, agentCard);
        return this.agentManager.sendTask(
          assistant.id,
          {
            id: taskId,
            message: {
              role: 'user',
              parts: [{ type: 'text' as const, text: request }],
            },
          }
        )
      }).catch(error => {
        console.error(`Error sending task: ${error}`);
        throw error;
      });

    console.log(`Task: ${JSON.stringify(task)}`);

    return {
      id: taskId,
      status: 'success',
      message: `Assistant "${assistant.name}" has been requested to perform the task: "${request}"`,
      url: assistant.url
    };
  }
}

class MessageProcessor {
  private prompt?: ChatPrompt;

  constructor(
    private assistantManager: AssistantManager,
    private openaiConfig: { model: string; apiKey: string }
  ) {}

  async initialize(): Promise<void> {
    const assistants = this.assistantManager.getAllAssistants();
    this.prompt = await this.createPrompt(assistants);
  }

  private async createPrompt(assistants: Assistant[]): Promise<ChatPrompt> {
    return new ChatPrompt({
      instructions: [
        'You are a helpful assistant that connects users with specialized AI ',
        'assistants from the CodeMie platform. Your role is to:',
        '',
        '1. Help users discover and understand available assistants',
        '2. Route specific requests to the appropriate assistant',
        '3. Provide clear, concise responses',
        '',
        'To use a specific assistant, users can:',
        '- Ask about available assistants using "list assistants" or "what can you do?"',
        '- Get details about an assistant using "tell me about [assistant name]"',
        '- Send direct request to an assistant using "@[assistant name] [request]"',
        '',
        'Available assistants:',
        assistants.map(assistant => `- ${assistant.name}`).join('\n'),
        '',
        'Always be helpful, clear, and concise in your responses. If you\'re unsure ',
        'about a request, ask for clarification.',
      ].join('\n'),
      model: new OpenAIChatModel({
        model: this.openaiConfig.model,
        apiKey: this.openaiConfig.apiKey,
      } as OpenAIChatModelOptions),
    }).function(
      'describe_assistant',
      'describes the assistant, including its name, description, skills, and capabilities',
      describeAssistantSchema,
      async ({ assistantName }: { assistantName: string }) => {
        return this.assistantManager.getAssistantAgentCard(assistantName);
      }
    ).function(
      'list_assistants',
      'returns the list of available assistants',
      () => this.assistantManager.getAllAssistants().map(a => a.name)
    ).function(
      'send_request',
      'sends a request to an assistant',
      sendRequestSchema,
      async ({ assistantName, request }: { assistantName: string, request: string }) => {
        return this.assistantManager.sendTaskToAssistant(assistantName, request);
      }
    );
  }

  async processMessage(text: string): Promise<string> {
    if (!this.prompt) {
      throw new Error('MessageProcessor not initialized. Call initialize() first.');
    }
    const response = await this.prompt.send(text);
    return response.content ?? BOT_CONFIG.DEFAULT_ERROR_MESSAGE;
  }
}

export class CodeMieBot {
  private app: App;
  private assistantManager: AssistantManager;
  private messageProcessor: MessageProcessor;

  constructor(codemie: CodeMieApiClient) {
    this.assistantManager = new AssistantManager(codemie);
    this.messageProcessor = new MessageProcessor(
      this.assistantManager,
      { model: env.OPENAI_MODEL, apiKey: env.OPENAI_API_KEY }
    );

    this.app = new App({
      plugins: [new DevtoolsPlugin()],
    });

    this.initMessageHandlers();
  }

  private initMessageHandlers(): void {
    this.app.on('message', async ({ send, activity }) => {
      try {
        await send({ type: 'typing' });
        const response = await this.messageProcessor.processMessage(activity.text);
        await send(response);
      } catch (error) {
        console.error('Error processing message:', error);
        await send('I encountered an error processing your request. Please try again.');
      }
    });
  }

  public async start(port: number): Promise<void> {
    try {
      await this.assistantManager.initialize();
      await this.messageProcessor.initialize();
      await this.app.start(port);
    } catch (error) {
      throw error;
    }
  }
}
