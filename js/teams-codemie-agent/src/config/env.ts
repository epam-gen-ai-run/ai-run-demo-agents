import dotenv from 'dotenv';
import { z } from 'zod';

// Load environment variables
dotenv.config();

const envSchema = z.object({
  PORT: z.string().transform(Number).default('3000'),
  OPENAI_API_KEY: z.string().min(1),
  CODEMIE_API_URL: z.string().url(),
});

type Env = z.infer<typeof envSchema>;

export const env = envSchema.parse(process.env) as Env;