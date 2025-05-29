import { config } from 'dotenv';
import { CodeMieBot } from './bot/bot';

config();

const bot = new CodeMieBot();

(async () => {
  await bot.start();
})();
