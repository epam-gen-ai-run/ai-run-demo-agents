import { env } from './config/env';
import { CodeMieBot } from './bot/bot';
import { CodeMieApiClient } from './services/codemie-api-client';

async function main() {
  const codemie = new CodeMieApiClient({
    baseUrl: env.CODEMIE_API_URL,
    cookies: [
      env.OAUTH2_PROXY_0,
      env.OAUTH2_PROXY_1,
    ]
  });
  const bot = new CodeMieBot(codemie);
  console.log(`Starting CodeMieBot on port ${env.PORT || 3000}`);

  await bot.start(env.PORT || 3000);
}

main().catch(console.error);
