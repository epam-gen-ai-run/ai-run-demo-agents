/**
 * Sample data for demonstration purposes
 * These assistants represent different types of helpful AI assistants
 * that could be used in a Teams environment
 */

import { Assistant } from '../interfaces/types';
import { v4 as uuidv4 } from 'uuid';

// Using fixed UUIDs to ensure consistency across application restarts
const ASSISTANT_IDS = {
    CODE_REVIEWER: '123e4567-e89b-12d3-a456-426614174000',
    DOC_HELPER: '123e4567-e89b-12d3-a456-426614174001',
    TEST_GENERATOR: '123e4567-e89b-12d3-a456-426614174002',
    BUG_ANALYZER: '123e4567-e89b-12d3-a456-426614174003',
    ARCH_ADVISOR: '123e4567-e89b-12d3-a456-426614174004',
    SECURITY_SCANNER: '123e4567-e89b-12d3-a456-426614174005',
    PERF_OPTIMIZER: '123e4567-e89b-12d3-a456-426614174006',
    API_DESIGNER: '123e4567-e89b-12d3-a456-426614174007',
    DB_EXPERT: '123e4567-e89b-12d3-a456-426614174008',
    DEVOPS_ASSISTANT: '123e4567-e89b-12d3-a456-426614174009'
} as const;

export const sampleAssistants: Assistant[] = [
    {
        id: ASSISTANT_IDS.CODE_REVIEWER,
        name: 'Code Reviewer',
        slug: 'code-reviewer',
        agentCardUrl: 'https://example.com/code-reviewer/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.DOC_HELPER,
        name: 'Documentation Helper',
        slug: 'documentation-helper',
        agentCardUrl: 'https://example.com/documentation-helper/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.TEST_GENERATOR,
        name: 'Test Generator',
        slug: 'test-generator',
        agentCardUrl: 'https://example.com/test-generator/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.BUG_ANALYZER,
        name: 'Bug Analyzer',
        slug: 'bug-analyzer',
        agentCardUrl: 'https://example.com/bug-analyzer/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.ARCH_ADVISOR,
        name: 'Architecture Advisor',
        slug: 'architecture-advisor',
        agentCardUrl: 'https://example.com/architecture-advisor/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.SECURITY_SCANNER,
        name: 'Security Scanner',
        slug: 'security-scanner',
        agentCardUrl: 'https://example.com/security-scanner/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.PERF_OPTIMIZER,
        name: 'Performance Optimizer',
        slug: 'performance-optimizer',
        agentCardUrl: 'https://example.com/performance-optimizer/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.API_DESIGNER,
        name: 'API Designer',
        slug: 'api-designer',
        agentCardUrl: 'https://example.com/api-designer/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.DB_EXPERT,
        name: 'Database Expert',
        slug: 'database-expert',
        agentCardUrl: 'https://example.com/database-expert/.well-known/agent.json'
    },
    {
        id: ASSISTANT_IDS.DEVOPS_ASSISTANT,
        name: 'DevOps Assistant',
        slug: 'devops-assistant',
        agentCardUrl: 'https://example.com/devops-assistant/.well-known/agent.json'
    }
];

/**
 * Helper function to get a random assistant
 * Useful for testing and demonstration
 */
export const getRandomAssistant = (): Assistant => {
    const randomIndex = Math.floor(Math.random() * sampleAssistants.length);
    return sampleAssistants[randomIndex];
};

/**
 * Helper function to get an assistant by ID
 */
export const getAssistantById = (id: string): Assistant | undefined => {
    return sampleAssistants.find(assistant => assistant.id === id);
};

// Export the ID constants for use in other parts of the application
export { ASSISTANT_IDS }; 