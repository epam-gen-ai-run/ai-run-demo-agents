import { config } from 'dotenv';
import { z } from 'zod';

// Load environment variables from .env file
config();

// Environment variable schema
const envSchema = z.object({
  PORT: z.string().transform(Number).default('3000'),
  OPENAI_API_KEY: z.string().min(1),
  OPENAI_MODEL: z.string().min(1).default('gpt-4o'),
  CODEMIE_API_URL: z.string().url(),
  OAUTH2_PROXY_0: z.string().min(1),
  OAUTH2_PROXY_1: z.string().min(1),
});

type Env = z.infer<typeof envSchema>;

export const env = envSchema.parse(process.env) as Env;