import { App } from '@microsoft/teams.apps';
import { DevtoolsPlugin } from '@microsoft/teams.dev';

export class CodeMieBot {
  private app: App;

  constructor() {
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

  public async start(): Promise<void> {
    try {
      await this.app.start();
    } catch (error) {
      throw error;
    }
  }
}