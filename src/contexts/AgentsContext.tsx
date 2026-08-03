import React, { createContext, useContext, useState } from 'react';

export type AgentStatus = 'idle' | 'working' | 'debating' | 'moving' | 'thinking' | 'resting' | 'waiting';

// 💡 엔진 타입 세분화 (Flash/Pro/Claude-CLI 하이브리드 지원)
export type EngineType = 'Gemini-Flash' | 'Gemini-Pro' | 'Claude-CLI' | 'Claude' | 'GPT-4';

export interface Agent {
    id: string;
    name: string;
    engine: EngineType;
    role: string;           // 💡 커스텀 역할 지원을 위해 string으로 변경 (기존: 'backend' | 'frontend' | 'leader')
    persona?: string;       // 💡 사용자 정의 페르소나 (역할/행동 지침 프롬프트)
    status: AgentStatus;
    spriteAsset: string;
    message?: string;
    assignedProjects: string[];
    isActive: boolean;
    stress?: number;        // 💡 업무 스트레스 지수 (0 ~ 100)
    totalTokens?: number;    // 💡 당일 누적 토큰 처리량
    customPosition?: { x: number, y: number }; // 💡 드래그 앤 드롭 수동 지정 위치
}

export interface Project {
    id: string;
    name: string;
}

interface AgentsContextType {
    agents: Agent[];
    projects: Project[];
    updateAgentStatus: (id: string, status: AgentStatus, message?: string) => void;
    assignProjectToAgent: (agentId: string, projectId: string) => void;
    toggleAgentActive: (id: string) => void;
    resetAllAgents: () => void;
    addAgent: (agent: Agent) => void;
    updateAgent: (agent: Agent) => void;
    deleteAgent: (id: string) => void;
    addProject: (project: Project) => void;
    updateProject: (project: Project) => void;
    deleteProject: (id: string) => void;
    increaseAgentLoad: (id: string, tokens: number) => void; // 💡 분석량(토큰) 증가 및 스트레스 누적
    reduceAgentStress: (id: string, amount: number) => void;  // 💡 커피 등으로 스트레스 경감
    updateAgentPosition: (id: string, position: { x: number, y: number } | undefined) => void;
    clearAgentProjects: (agentId: string) => void;
}

const AgentsContext = createContext<AgentsContextType | undefined>(undefined);

export const AgentsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [projects, setProjects] = useState<Project[]>([
        { id: 'echo-frontend', name: 'echo-frontend (화면단/MiPlatform)' },
        { id: 'annapurna', name: 'annapurna (메인 API/스프링)' },
        { id: 'chooyu', name: 'chooyu (고객관리 API/스프링)' },
        { id: 'member-batch', name: 'member-batch (배치 작업)' },
        { id: 'db_meta', name: 'db_meta (MDS 데이터베이스 스키마 엑셀)' },
        { id: 'manaslu', name: '마나스루' },
        { id: 'smtc-batch-cst', name: '고객배치' },
        { id: 'pis-epr-batch_git', name: '유효기간제 배치' },
    ]);

    const [agents, setAgents] = useState<Agent[]>([
        {
            id: 'agent_be1',
            name: '백엔드/DB 에이전트1',
            engine: 'Claude-CLI', // 💡 초기 셋팅 Claude-CLI로 설정
            role: 'backend',
            status: 'idle',
            spriteAsset: '👨‍💻',
            assignedProjects: [],
            isActive: true,
            stress: 0,
            totalTokens: 0
        },
        {
            id: 'agent_be2',
            name: '백엔드/DB 에이전트2',
            engine: 'Gemini-Flash', // 💡 초기 셋팅 Flash로 변경
            role: 'backend',
            status: 'idle',
            spriteAsset: '🧙‍♂️',
            assignedProjects: [],
            isActive: true,
            stress: 0,
            totalTokens: 0
        },
        {
            id: 'agent_fe',
            name: '프론트엔드 에이전트',
            engine: 'Gemini-Flash', // 💡 초기 셋팅 Flash로 변경
            role: 'frontend',
            status: 'idle',
            spriteAsset: '👩‍💻',
            assignedProjects: [],
            isActive: true,
            stress: 0,
            totalTokens: 0
        },
        {
            id: 'agent_leader',
            name: '팀장',
            engine: 'Gemini-Flash', // 💡 초기 셋팅 Gemini-Flash로 설정 (Claude-CLI는 필요 시 선택)
            role: 'leader',
            status: 'idle',
            spriteAsset: '👔',
            assignedProjects: [],
            isActive: true,
            stress: 0,
            totalTokens: 0
        }
    ]);

    const updateAgentStatus = (id: string, status: AgentStatus, message?: string) => {
        setAgents(prev => prev.map(agent =>
            agent.id === id ? { ...agent, status, message } : agent
        ));
    };

    const increaseAgentLoad = (id: string, tokens: number) => {
        setAgents(prev => prev.map(agent => {
            if (agent.id !== id) return agent;
            const currentStress = agent.stress ?? 0;
            const currentTokens = agent.totalTokens ?? 0;
            // 토큰량의 0.3% 만큼 스트레스 지수 누적 (최대 100)
            const addedStress = Math.round(tokens * 0.003);
            return {
                ...agent,
                totalTokens: currentTokens + tokens,
                stress: Math.min(100, currentStress + addedStress)
            };
        }));
    };

    const reduceAgentStress = (id: string, amount: number) => {
        setAgents(prev => prev.map(agent => {
            if (agent.id !== id) return agent;
            const currentStress = agent.stress ?? 0;
            return {
                ...agent,
                stress: Math.max(0, currentStress - amount)
            };
        }));
    };

    const updateAgentPosition = (id: string, position: { x: number, y: number } | undefined) => {
        setAgents(prev => prev.map(agent =>
            agent.id === id ? { ...agent, customPosition: position } : agent
        ));
    };

    const assignProjectToAgent = (agentId: string, projectId: string) => {
        setAgents(prev => prev.map(agent => {
            if (agent.id !== agentId) return agent;
            const isAssigned = agent.assignedProjects.includes(projectId);
            return {
                ...agent,
                assignedProjects: isAssigned
                    ? agent.assignedProjects.filter(id => id !== projectId)
                    : [...agent.assignedProjects, projectId]
            };
        }));
    };

    const clearAgentProjects = (agentId: string) => {
        setAgents(prev => prev.map(agent => 
            agent.id === agentId ? { ...agent, assignedProjects: [] } : agent
        ));
    };

    const toggleAgentActive = (id: string) => {
        setAgents(prev => prev.map(agent =>
            agent.id === id ? { ...agent, isActive: !agent.isActive, status: 'idle', message: undefined } : agent
        ));
    };

    const resetAllAgents = () => {
        setAgents(prev => prev.map(agent => ({
            ...agent,
            status: 'idle',
            message: undefined,
            assignedProjects: [],
            isActive: true,
            stress: 0,
            totalTokens: 0
        })));
    };

    const addAgent = (newAgent: Agent) => {
        setAgents(prev => [...prev, newAgent]);
    };

    const updateAgent = (updatedAgent: Agent) => {
        setAgents(prev => prev.map(agent =>
            agent.id === updatedAgent.id ? updatedAgent : agent
        ));
    };

    const deleteAgent = (id: string) => {
        setAgents(prev => prev.filter(agent => agent.id !== id));
    };

    const addProject = (newProject: Project) => {
        setProjects(prev => [...prev, newProject]);
    };

    const updateProject = (updatedProject: Project) => {
        setProjects(prev => prev.map(p =>
            p.id === updatedProject.id ? updatedProject : p
        ));
    };

    const deleteProject = (id: string) => {
        setProjects(prev => prev.filter(p => p.id !== id));
        // 프로젝트 삭제 시 에이전트들의 할당 목록에서도 제거
        setAgents(prev => prev.map(agent => ({
            ...agent,
            assignedProjects: agent.assignedProjects.filter(projectId => projectId !== id)
        })));
    };

    return (
        <AgentsContext.Provider value={{
            agents, projects, updateAgentStatus, assignProjectToAgent, toggleAgentActive, resetAllAgents, addAgent, updateAgent, deleteAgent, addProject, updateProject, deleteProject, increaseAgentLoad, reduceAgentStress, updateAgentPosition, clearAgentProjects
        }}>
            {children}
        </AgentsContext.Provider>
    );
};

export const useAgents = () => {
    const context = useContext(AgentsContext);
    if (!context) throw new Error('Context 스펙 에러');
    return context;
};