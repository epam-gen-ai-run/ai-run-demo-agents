import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { ChatPrompt, ObjectSchema } from '@microsoft/teams.ai';
import { OpenAIChatModelOptions, OpenAIChatModel } from '@microsoft/teams.openai';
import { env } from '../config/env';

import { CodeMieApiClient } from '../services/codemie-api-client';
import { AgentManager } from '@microsoft/teams.a2a';
import { v4 as uuidv4 } from 'uuid';

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

export class CodeMieBot {
  private app: App;
  private codemie: CodeMieApiClient
  private prompt!: ChatPrompt;
  private agentManager: AgentManager;

  constructor(codemie: CodeMieApiClient) {
    this.codemie = codemie;
    this.agentManager = new AgentManager();

    // Initialize Teams app
    this.app = new App({
      plugins: [new DevtoolsPlugin()],
    });

    // Set up message handlers
    this.initMessageHandlers();
  }

  private initMessageHandlers(): void {
    this.app.on('message', async ({ send, activity }) => {
        await send({ type: 'typing' });
        const response = await this.prompt.send(activity.text);
        await send(response.content ?? "I'm sorry, I couldn't process that request.");
    });
  }

  async initPrompt(): Promise<ChatPrompt> {
    const assistants = await this.codemie.fetchAssistants();
    console.log(`Found ${assistants.length} assistants`);
    console.log(assistants.map(a => a.name));

    assistants.forEach(async (assistant) => {
      this.agentManager.use(assistant.id, assistant.url);
    });
  
    return new ChatPrompt(
      {
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
            model: env.OPENAI_MODEL,
            apiKey: env.OPENAI_API_KEY,
        } as OpenAIChatModelOptions),
      },
    ).function(
      'describe_assistant',
      'describes the assistant, including its name, description, skills, and capabilities',
      describeAssistantSchema,
      async ({ assistantName }: { assistantName: string }) => {
          console.log(`Looking for assistant "${assistantName}"`);
          const assistant = assistants.find(assistant => assistant.name === assistantName);
          if (!assistant) {
              throw new Error(`Assistant "${assistantName}" not found`);
          }
          const agentCard = await this.codemie.fetchAssistantAgentCard(assistant.agentCardUrl);
          return agentCard;
      }
    ).function(
      'list_assistants',
      'returns the list of available assistants',
      () => {
        console.log(`Getting available assistants`);
        return assistants.map(a => a.name);
      }
    ).function(
      'send_request',
      'sends a request to an assistant',
      sendRequestSchema,
      async ({ assistantName, request }: { assistantName: string, request: string }) => {
        console.log(`Requesting assistant "${assistantName}" to perform task: "${request}"`);
        const assistant = assistants.find(assistant => assistant.name === assistantName);
        if (!assistant) {
            throw new Error(`Assistant "${assistantName}" not found`);
        }

        const taskId = uuidv4();
        const task = await this.agentManager.sendTask(
          assistant.id,
          {
            id: taskId,
            message: {
              role: 'user',
              parts: [{ type: 'text' as const, text: request }],
            },
          }
        ).catch(error => {
          console.error(`Error sending task: ${error}`);
          throw error;
        });
        console.log(`Task received: ${task}`);

        console.log(`Assistant "${assistant.name}" has been requested to perform the task: "${request}" via the A2A API ${assistant.url}`);
        return `Assistant "${assistant.name}" has been requested to perform the task: "${request}" via the A2A API ${assistant.url}`;
      }
    );
  }

  public async start(port: number): Promise<void> {
    try {
      this.prompt = await this.initPrompt();
      await this.app.start(port);
    } catch (error) {
      throw error;
    }
  }
}
