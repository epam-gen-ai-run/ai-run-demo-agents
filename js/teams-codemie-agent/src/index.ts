import { env } from './config/env';
import { CodeMieBot } from './bot/bot';
import { CodeMieApiClient } from './services/codemie-api-client';

async function main() {
  const codemie = new CodeMieApiClient(env.CODEMIE_API_URL);
  const assistants = await codemie.fetchAssistants();
  console.log(`Found ${assistants.length} assistants`);
  console.log(assistants.map(a => `${a.name} - ${a.agentCardUrl}`));

  const bot = new CodeMieBot(assistants);
  console.log(`Starting CodeMieBot on port ${env.PORT || 3000}`);

  await bot.start(env.PORT || 3000);
}

main().catch(console.error);
