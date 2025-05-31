import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';
import { Assistant } from '../interfaces/types';

export class CodeMieBot {
  private app: App;
  private assistants: Assistant[];


  constructor(assistants: Assistant[]) {
    this.assistants = assistants;
    
    // Initialize Teams app
    this.app = new App({
      plugins: [new DevtoolsPlugin()],
    });

    // Set up message handlers
    this.setupMessageHandlers();
  }

  private setupMessageHandlers(): void {
    this.app.on('message', async ({ send, activity }) => {
        await send({ type: 'typing' });
        await send(`you said "${activity.text}"`);
    });
  }

  public async start(port: number): Promise<void> {
    try {
      await this.app.start(port);
    } catch (error) {
      throw error;
    }
  }
}