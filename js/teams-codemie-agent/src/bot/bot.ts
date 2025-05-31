import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { ChatPrompt, ObjectSchema } from '@microsoft/teams.ai';
import { OpenAIChatModelOptions, OpenAIChatModel } from '@microsoft/teams.openai';
import { env } from '../config/env';

import { CodeMieApiClient } from '../services/codemie-api-client';

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

export class CodeMieBot {
  private app: App;
  private codemie: CodeMieApiClient
  private prompt!: ChatPrompt;

  constructor(codemie: CodeMieApiClient) {
    this.codemie = codemie;
    
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
  
    return new ChatPrompt(
      {
          instructions: [
            'You are an intelligent multi-assistant that helps to access specialized intelligent assistants managed by the CodeMie platform through natural conversation.',
            'The following assistants are available to you:',
            assistants.map(assistant => `- ${assistant.name}`).join('\n'),
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
      }).function(
        'get_assistants',
        'returns the list of available assistants',
        () => {
          console.log(`Getting available assistants`);
          return assistants.map(a => a.name);
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
