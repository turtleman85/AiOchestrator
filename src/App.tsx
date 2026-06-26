import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import { useAgents, AgentsProvider, type Agent } from './contexts/AgentsContext';
import {
    Terminal, Cpu, Play, RefreshCw, UserPlus, LogOut, PlusCircle,
    Edit2, Trash2, X, Users, Crown, Bot, Zap, MessageSquare, Save, FileText, CheckCircle2, AlertCircle
} from 'lucide-react';

const getCharacterPreset = (agentId: string, index: number) => {
    const presets = [
        { name: '강철두', hairColor: '#22c55e', clothesColor: '#1e293b', isBald: false, mohawk: false },
        { name: '김노을', hairColor: '#ef4444', clothesColor: '#0f172a', isBald: true, mohawk: true },
        { name: '하니', hairColor: '#eab308', clothesColor: '#be123c', isBald: false, mohawk: false },
        { name: '조이', hairColor: '#c084fc', clothesColor: '#701a75', isBald: false, mohawk: false },
        { name: '레오', hairColor: '#3b82f6', clothesColor: '#1e40af', isBald: false, mohawk: false },
    ];
    if (agentId === 'agent_be1') return presets[0];
    if (agentId === 'agent_be2') return presets[1];
    if (agentId === 'agent_fe') return presets[2];
    return presets[index % presets.length];
};

const getAgentDirection = (agent: any, index: number, isAutoMode: boolean, step?: string, presenterId?: string | null) => {
    const isMeetingPhase = agent.status === 'debating' || (isAutoMode && step === 'reviewing');
    if (isMeetingPhase && presenterId) {
        if (agent.id === presenterId) return 'down'; // Presenter faces down from whiteboard
        return 'up'; // Listeners face up to whiteboard
    }
    if (isAutoMode) {
        const currentStep = step || 'idle';
        if (currentStep === 'planning') return 'down';
        if (currentStep === 'analyzing') return 'up';
        if (currentStep === 'reviewing') return index % 2 === 0 ? 'left' : 'right';
        return 'down';
    }
    if (!agent.isActive) return 'down';
    if (agent.status === 'working' || agent.status === 'thinking') return 'up';
    if (agent.role === 'leader') return 'down';
    if (agent.assignedProjects.length === 0) return 'down';
    return 'down';
};

const renderPixelSprite = (direction: 'up' | 'down' | 'left' | 'right', preset: any, isDebating?: boolean) => {
    const { hairColor, clothesColor, isBald, mohawk } = preset;
    const skin = isDebating ? '#f87171' : '#ffd3b6';
    const pants = '#3b82f6';
    const shoes = '#334155';
    
    const pixels: React.ReactNode[] = [];
    const drawRect = (x: number, y: number, w: number, h: number, color: string) => {
        pixels.push(<rect key={`${x}-${y}-${color}`} x={x} y={y} width={w} height={h} fill={color} />);
    };
    
    if (direction === 'up') {
        if (!isBald) {
            drawRect(4, 2, 8, 6, hairColor);
            drawRect(3, 3, 10, 5, hairColor);
        } else {
            drawRect(4, 3, 8, 5, skin);
            if (mohawk) drawRect(7, 2, 2, 6, hairColor);
        }
        drawRect(4, 8, 8, 6, clothesColor);
        drawRect(2, 8, 2, 4, clothesColor);
        drawRect(12, 8, 2, 4, clothesColor);
        drawRect(4, 14, 3, 2, pants);
        drawRect(9, 14, 3, 2, pants);
        drawRect(4, 16, 3, 1, shoes);
        drawRect(9, 16, 3, 1, shoes);
    } else if (direction === 'down') {
        if (!isBald) {
            drawRect(4, 2, 8, 6, hairColor);
            drawRect(3, 3, 10, 5, hairColor);
            drawRect(4, 4, 8, 4, skin);
        } else {
            drawRect(4, 3, 8, 5, skin);
            drawRect(4, 4, 8, 4, skin);
            if (mohawk) drawRect(7, 2, 2, 6, hairColor);
        }
        drawRect(5, 5, 2, 1, '#1e293b');
        drawRect(9, 5, 2, 1, '#1e293b');
        drawRect(4, 8, 8, 6, clothesColor);
        drawRect(2, 8, 2, 4, clothesColor);
        drawRect(12, 8, 2, 4, clothesColor);
        drawRect(4, 14, 3, 2, pants);
        drawRect(9, 14, 3, 2, pants);
        drawRect(4, 16, 3, 1, shoes);
        drawRect(9, 16, 3, 1, shoes);
    } else if (direction === 'left') {
        if (!isBald) {
            drawRect(5, 2, 6, 6, hairColor);
            drawRect(4, 3, 7, 4, hairColor);
            drawRect(10, 4, 2, 4, skin);
            drawRect(9, 5, 1, 1, '#1e293b');
        } else {
            drawRect(5, 3, 6, 5, skin);
            drawRect(10, 4, 1, 4, skin);
            drawRect(9, 5, 1, 1, '#1e293b');
            if (mohawk) drawRect(7, 2, 2, 6, hairColor);
        }
        drawRect(6, 8, 6, 6, clothesColor);
        drawRect(8, 8, 2, 4, clothesColor);
        drawRect(6, 14, 3, 2, pants);
        drawRect(6, 16, 3, 1, shoes);
    } else if (direction === 'right') {
        if (!isBald) {
            drawRect(5, 2, 6, 6, hairColor);
            drawRect(5, 3, 7, 4, hairColor);
            drawRect(4, 4, 2, 4, skin);
            drawRect(6, 5, 1, 1, '#1e293b');
        } else {
            drawRect(5, 3, 6, 5, skin);
            drawRect(5, 4, 1, 4, skin);
            drawRect(6, 5, 1, 1, '#1e293b');
            if (mohawk) drawRect(7, 2, 2, 6, hairColor);
        }
        drawRect(4, 8, 6, 6, clothesColor);
        drawRect(6, 8, 2, 4, clothesColor);
        drawRect(7, 14, 3, 2, pants);
        drawRect(7, 16, 3, 1, shoes);
    }
    
    return (
        <svg viewBox="0 0 16 18" className="w-12 h-14 drop-shadow-md" style={{ shapeRendering: 'crispEdges' }}>
            {pixels}
        </svg>
    );
};

const renderLeaderSprite = (direction: 'up' | 'down' | 'left' | 'right') => {
    const hairColor = '#8b5a2b';
    const clothesColor = '#1e293b';
    const skin = '#ffd3b6';
    const pants = '#0f172a';
    const shoes = '#334155';
    
    const pixels: React.ReactNode[] = [];
    const drawRect = (x: number, y: number, w: number, h: number, color: string) => {
        pixels.push(<rect key={`${x}-${y}-${color}`} x={x} y={y} width={w} height={h} fill={color} />);
    };
    
    if (direction === 'up') {
        drawRect(4, 2, 8, 6, hairColor);
        drawRect(3, 3, 10, 5, hairColor);
        drawRect(4, 8, 8, 6, clothesColor);
        drawRect(2, 8, 2, 4, clothesColor);
        drawRect(12, 8, 2, 4, clothesColor);
        drawRect(4, 14, 3, 2, pants);
        drawRect(9, 14, 3, 2, pants);
        drawRect(4, 16, 3, 1, shoes);
        drawRect(9, 16, 3, 1, shoes);
    } else {
        drawRect(4, 2, 8, 2, hairColor);
        drawRect(3, 3, 10, 2, hairColor);
        drawRect(3, 5, 2, 3, hairColor);
        drawRect(11, 5, 2, 3, hairColor);
        drawRect(5, 4, 6, 4, skin);
        drawRect(4, 5, 8, 3, skin);
        drawRect(5, 6, 2, 1, '#1e293b');
        drawRect(9, 6, 2, 1, '#1e293b');
        drawRect(4, 8, 8, 6, clothesColor);
        drawRect(2, 8, 2, 4, clothesColor);
        drawRect(12, 8, 2, 4, clothesColor);
        drawRect(4, 14, 3, 2, pants);
        drawRect(9, 14, 3, 2, pants);
        drawRect(4, 16, 3, 1, shoes);
        drawRect(9, 16, 3, 1, shoes);
    }
    
    return (
        <svg viewBox="0 0 16 18" className="w-12 h-14 drop-shadow-md" style={{ shapeRendering: 'crispEdges' }}>
            {pixels}
        </svg>
    );
};

const renderPixelFace = (agentId: string, index: number, size: number = 32) => {
    const preset = getCharacterPreset(agentId, index);
    const { hairColor, isBald, mohawk } = preset;
    const skin = '#ffd3b6';
    
    const pixels: React.ReactNode[] = [];
    const drawRect = (x: number, y: number, w: number, h: number, color: string) => {
        pixels.push(<rect key={`${x}-${y}-${color}`} x={x} y={y} width={w} height={h} fill={color} />);
    };
    
    if (!isBald) {
        drawRect(2, 2, 12, 4, hairColor);
        drawRect(1, 3, 14, 4, hairColor);
        drawRect(2, 6, 12, 8, skin);
    } else {
        drawRect(2, 3, 12, 11, skin);
        if (mohawk) drawRect(6, 1, 4, 3, hairColor);
    }
    drawRect(4, 8, 2, 2, '#1e293b');
    drawRect(10, 8, 2, 2, '#1e293b');
    
    return (
        <svg viewBox="0 0 16 16" style={{ width: `${size}px`, height: `${size}px`, shapeRendering: 'crispEdges' }}>
            <rect width="16" height="16" fill="#0f172a" rx="2" />
            {pixels}
        </svg>
    );
};

const renderPottedTree = (x: number, y: number) => (
    <div className="absolute select-none flex flex-col items-center z-10 drop-shadow-lg" style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' }}>
        <div className="relative w-8 h-8 flex items-center justify-center">
            <div className="absolute w-7 h-7 bg-[#4ade80] rounded-full opacity-90" />
            <div className="absolute w-5 h-5 bg-[#22c55e] rounded-full bottom-0 left-0" />
        </div>
        <div className="w-1.5 h-2 bg-[#78350f]" />
        <div className="w-4 h-3 bg-[#475569] border border-slate-500 rounded-sm" />
    </div>
);

function Dashboard() {
    const {
        agents, projects, updateAgentStatus, assignProjectToAgent, toggleAgentActive, resetAllAgents,
        addAgent, updateAgent, deleteAgent, addProject, deleteProject,
        increaseAgentLoad, reduceAgentStress, updateAgentPosition, clearAgentProjects
    } = useAgents();

    const [draggingAgentId, setDraggingAgentId] = useState<string | null>(null);
    const officeRef = useRef<HTMLDivElement>(null);
    const [localDirectories, setLocalDirectories] = useState<string[]>([]);

    const [agentPanelTab, setAgentPanelTab] = useState<'manual' | 'auto'>('manual');
    const [logInput, setLogInput] = useState('');
    const [attachedImages, setAttachedImages] = useState<string[]>([]);
    
    const handlePaste = (e: React.ClipboardEvent) => {
        const items = e.clipboardData?.items;
        if (!items) return;
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const file = items[i].getAsFile();
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        const base64Str = event.target?.result as string;
                        setAttachedImages(prev => [...prev, base64Str]);
                    };
                    reader.readAsDataURL(file);
                }
            }
        }
    };

    const removeImage = (indexToRemove: number) => {
        setAttachedImages(prev => prev.filter((_, idx) => idx !== indexToRemove));
    };

    const [jiraKey, setJiraKey] = useState('');
    const [runDevelopment, setRunDevelopment] = useState(false);
    const [individualInputs, setIndividualInputs] = useState<Record<string, {jiraKey: string, logInput: string}>>({});
    const [createBranch, setCreateBranch] = useState(false);
    const [requireLeaderFeedback, setRequireLeaderFeedback] = useState(false);
    const [runTesting, setRunTesting] = useState(false);
    const [requestMode, setRequestMode] = useState<'unified' | 'individual'>('unified');
    const [individualRequests, setIndividualRequests] = useState<Record<string, {jiraKey: string, logInput: string}>>({});
    
    const [isAddingProject, setIsAddingProject] = useState(false);
    const [newProjectName, setNewProjectName] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    
    const [leaderStatus, setLeaderStatus] = useState<any>({ step: 'idle', message: '대기 중' });
    const [autoPlan, setAutoPlan] = useState<any>(null);
    const [meetingTick, setMeetingTick] = useState(0);

    const [editingAgent, setEditingAgent] = useState<Agent | null>(null);

    const [finalReport, setFinalReport] = useState('');
    const [currentReportHtml, setCurrentReportHtml] = useState('');
    const [currentReportText, setCurrentReportText] = useState('');
    const [agentReports, setAgentReports] = useState<Record<string, any>>({});
    const [reportViewTab, setReportViewTab] = useState<'visual' | 'markdown'>('visual');
    const [selectedReportAgentId, setSelectedReportAgentId] = useState<string>('merged');
    const [lastTokenUsage, setLastTokenUsage] = useState<any>(null);
    const [loadingLogs, setLoadingLogs] = useState<string[]>([]);

    useEffect(() => {
        if (!isAnalyzing) {
            setLoadingLogs([]);
            return;
        }
        const logs = [
            "프로젝트 워크스페이스 마운트 중...",
            "소스코드 트리 구조 스캔 중...",
            "의존성 패키지 및 설정 파일 분석 중...",
            "LLM 컨텍스트 윈도우 최적화 중...",
            "AI 에이전트 간 역할 동기화 중...",
            "데이터베이스 스키마 맵핑 중...",
            "프론트엔드 라우팅 및 컴포넌트 분석 중...",
            "주요 비즈니스 로직 추적 중...",
            "에이전트별 분석 리포트 통합 중...",
            "거의 다 왔습니다... 보고서 생성 중..."
        ];
        let idx = 0;
        const interval = setInterval(() => {
            if (idx < logs.length) {
                setLoadingLogs(prev => {
                    const nextLogs = [...prev, logs[idx]];
                    return nextLogs.length > 5 ? nextLogs.slice(nextLogs.length - 5) : nextLogs;
                });
                idx++;
            }
        }, 2500);
        return () => clearInterval(interval);
    }, [isAnalyzing]);

    useEffect(() => {
        const hasMeeting = agents.some(a => a.status === 'debating') || (agentPanelTab === 'auto' && leaderStatus?.step === 'reviewing');
        if (!hasMeeting) return;
        const interval = setInterval(() => setMeetingTick(t => t + 1), 3000);
        return () => clearInterval(interval);
    }, [agents, agentPanelTab, leaderStatus?.step]);

    // Auto Mode (AI Orchestrator) Logic
    useEffect(() => {
        if (agentPanelTab !== 'auto') {
            if (leaderStatus?.step !== 'idle') setLeaderStatus({ step: 'idle', message: '대기 중' });
            return;
        }

        const step = leaderStatus?.step || 'idle';
        let timeoutId: ReturnType<typeof setTimeout>;

        // 'idle' 상태에서는 사용자가 "업무 지시" 버튼을 누르기 전까지 아무것도 하지 않습니다.
        if (step === 'idle') {
            // 대기
        } else if (step === 'planning') {
            timeoutId = setTimeout(() => setLeaderStatus({ step: 'analyzing', message: '작업 배분 및 지시 중...' }), 3000);
        } else if (step === 'analyzing') {
            timeoutId = setTimeout(() => {
                agents.forEach(agent => {
                    if (agent.isActive && agent.role !== 'leader') {
                        if (agent.assignedProjects.length === 0 && projects.length > 0) {
                            assignProjectToAgent(agent.id, projects[0].id);
                        }
                        updateAgentStatus(agent.id, 'working');
                    }
                });
                updateAgentStatus('agent_leader', 'working');
                setLeaderStatus({ step: 'developing', message: '에이전트 병렬 작업 진행 중...' });
            }, 3000);
        } else if (step === 'developing') {
            // 에이전트들이 각자 작업을 끝내고 라운지나 회의실로 이동하는 시뮬레이션
            agents.forEach((agent, index) => {
                if (agent.isActive && agent.role !== 'leader') {
                    // 3초 ~ 6초 사이에 개별적으로 작업 완료 후 이동
                    setTimeout(() => {
                        updateAgentStatus(agent.id, index % 2 === 0 ? 'resting' : 'waiting');
                    }, 3000 + Math.random() * 3000);
                }
            });

            timeoutId = setTimeout(() => {
                agents.forEach(agent => {
                    if (agent.isActive) updateAgentStatus(agent.id, 'debating');
                });
                setLeaderStatus({ step: 'reviewing', message: '결과물 통합 리뷰 회의 중...' });
                setFinalReport(prev => prev + '\n\n[리뷰 회의]\n- 모든 에이전트가 개별 분석을 마쳤습니다.\n- 팀장 주도 하에 회의실에서 통합 리뷰 및 토론을 진행합니다.');
            }, 8000);
        } else if (step === 'reviewing') {
            timeoutId = setTimeout(() => {
                agents.forEach(agent => {
                    if (agent.isActive) {
                        updateAgentStatus(agent.id, 'idle');
                        clearAgentProjects(agent.id);
                    }
                });
                setLeaderStatus({ step: 'completed', message: '모든 프로젝트 완수!' });
            }, 6000);
        } else if (step === 'completed') {
            timeoutId = setTimeout(() => {
                setLeaderStatus({ step: 'idle', message: '새 프로젝트 대기 중...' });
            }, 5000);
        }

        return () => clearTimeout(timeoutId);
    }, [agentPanelTab, leaderStatus?.step, projects.length]);

    const isAgentSimulatingIdle = (agent: Agent) => {
        // 팀장은 시뮬레이션으로 방황하지 않고 항상 제자리를 지킴
        if (agent.role === 'leader') return false;
        
        return agent.isActive && agent.status === 'idle' && agentPanelTab === 'manual';
    };

    const activeDebaters = agents.filter(a => a.isActive && (a.status === 'debating' || (agentPanelTab === 'auto' && leaderStatus?.step === 'reviewing')));
    const presenterId = activeDebaters.length > 0 ? activeDebaters[meetingTick % activeDebaters.length].id : null;

    useEffect(() => {
        if (isAddingProject && localDirectories.length === 0) {
            fetch('http://localhost:8000/api/v1/projects/directories')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        setLocalDirectories(data.directories);
                    }
                })
                .catch(err => console.error("디렉토리 목록 조회 실패", err));
        }
    }, [isAddingProject]);

    const handleMouseMove = (e: MouseEvent) => {
        if (!draggingAgentId || !officeRef.current) return;
        const rect = officeRef.current.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        updateAgentPosition(draggingAgentId, { x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) });
    };

    const handleMouseUp = () => {
        setDraggingAgentId(null);
    };

    useEffect(() => {
        if (draggingAgentId) {
            window.addEventListener('mouseup', handleMouseUp);
            window.addEventListener('mousemove', handleMouseMove);
        } else {
            window.removeEventListener('mouseup', handleMouseUp);
            window.removeEventListener('mousemove', handleMouseMove);
        }
        return () => {
            window.removeEventListener('mouseup', handleMouseUp);
            window.removeEventListener('mousemove', handleMouseMove);
        };
    }, [draggingAgentId]);

    const handleMouseDown = (e: React.MouseEvent, agentId: string) => {
        setDraggingAgentId(agentId);
        e.preventDefault();
    };

    const handleAddProject = () => {
        if (newProjectName.trim()) {
            const trimmed = newProjectName.trim();
            addProject({ id: trimmed, name: trimmed });
            setNewProjectName('');
            setIsAddingProject(false);
        }
    };
    
    const handleSaveAgent = () => {
        if (!editingAgent) return;
        if (agents.find(a => a.id === editingAgent.id)) {
            updateAgent(editingAgent);
        } else {
            addAgent(editingAgent);
        }
        setEditingAgent(null);
    };

    const handleCreateNewAgent = () => {
        const newId = `agent_${Date.now()}`;
        setEditingAgent({
            id: newId,
            name: '신규 에이전트',
            engine: 'Gemini-Flash',
            role: 'backend',
            status: 'idle',
            spriteAsset: '👨‍💻',
            assignedProjects: [],
            isActive: false,
            stress: 0,
            totalTokens: 0
        });
    };
    
    // Coordinates mapping for 3-Room Layout
    const getLoungePos = (idx: number) => {
        const positions = [{ x: 80, y: 80 }, { x: 74, y: 74 }, { x: 88, y: 74 }, { x: 74, y: 86 }, { x: 88, y: 86 }];
        return positions[idx % positions.length];
    };
    
    const getMeetingPos = (idx: number) => {
        const positions = [{ x: 78, y: 18 }, { x: 86, y: 18 }, { x: 73, y: 32 }, { x: 91, y: 32 }, { x: 78, y: 45 }, { x: 86, y: 45 }];
        return positions[idx % positions.length];
    };
    
    const getAgentOfficePosition = (agent: any, index: number, isAutoMode: boolean) => {
        if (agent.customPosition) return { ...agent.customPosition, isManual: true }; // 💡 드래그된 수동 위치 최우선 적용
        
        const isPresenter = agent.id === presenterId;
        const isMeetingPhase = agent.status === 'debating' || (isAutoMode && leaderStatus?.step === 'reviewing');
        
        // Presenter in meeting room (near whiteboard)
        if (isPresenter && isMeetingPhase) return { x: 82, y: 15, isManual: false };
        
        // 책상 중심 좌표 (Main Workspace가 65% 너비이므로 x좌표에 0.65를 곱해 완벽히 정렬)
        const workspacePositions = [
            { x: 12 * 0.65, y: 15, isManual: false }, { x: 36 * 0.65, y: 15, isManual: false }, { x: 60 * 0.65, y: 15, isManual: false }, { x: 84 * 0.65, y: 15, isManual: false }, // Row 1
            { x: 12 * 0.65, y: 40, isManual: false }, { x: 36 * 0.65, y: 40, isManual: false }, { x: 60 * 0.65, y: 40, isManual: false }, { x: 84 * 0.65, y: 40, isManual: false }, // Row 2
            { x: 12 * 0.65, y: 65, isManual: false }, { x: 36 * 0.65, y: 65, isManual: false }, { x: 60 * 0.65, y: 65, isManual: false }, { x: 84 * 0.65, y: 65, isManual: false }, // Row 3
        ];
        
        if (agent.role === 'leader') {
            if (isAutoMode) {
                const step = leaderStatus?.step || 'idle';
                if (step === 'reviewing') return getMeetingPos(index);
                return { x: 48 * 0.65, y: 80, isManual: false }; // Leader desk
            }
            if (!agent.isActive) return getLoungePos(index);
            if (agent.status === 'debating') return getMeetingPos(index);
            return { x: 48 * 0.65, y: 80, isManual: false }; // Leader desk
        }
        
        const deskPos = workspacePositions[index % workspacePositions.length];
        
        if (isAutoMode) {
            const step = leaderStatus?.step || 'idle';
            if (step === 'planning') return getLoungePos(index);
            if (step === 'analyzing' || step === 'developing') {
                if (agent.status === 'resting') return getLoungePos(index);
                if (agent.status === 'waiting') return getMeetingPos(index);
                return deskPos;
            }
            if (step === 'reviewing') return getMeetingPos(index);
            if (step === 'completed') return index % 2 === 0 ? deskPos : getLoungePos(index);
            return getLoungePos(index);
        }
        
        if (!agent.isActive || agent.assignedProjects.length === 0) return getLoungePos(index);
        if (agent.status === 'resting') return getLoungePos(index);
        if (agent.status === 'waiting' || agent.status === 'debating') return getMeetingPos(index);
        return deskPos;
    };

    const getDeskAgent = (deskX: number, deskY: number) => {
        const activeTeam = agents.filter(a => a.isActive && a.role !== 'leader');
        return activeTeam.find((a, idx) => {
            const pos = getAgentOfficePosition(a, idx, agentPanelTab === 'auto');
            // deskX는 Main Workspace 내부(65% 너비) 기준이므로 전체 너비 기준으로 0.65를 곱해 비교해야 함
            return Math.abs(pos.x - deskX * 0.65) < 5 && Math.abs(pos.y - deskY) < 5;
        });
    };

    const isDeskWorking = (deskAgent: any) => {
        if (!deskAgent) return false;
        return deskAgent.status === 'working' || deskAgent.status === 'thinking' || deskAgent.status === 'debating';
    };

    const handleStartOrchestration = async () => {
        if (agentPanelTab === 'auto' && leaderStatus?.step !== 'idle') return; // 이미 실행 중이면 무시
        if (agentPanelTab === 'manual' && isAnalyzing) return;
        
        // 수동 모드일 때 에이전트 배정 검사
        if (agentPanelTab === 'manual') {
            const activeTeam = agents.filter(a => a.isActive && a.assignedProjects.length > 0 && a.role !== 'leader');
            if (activeTeam.length === 0) {
                alert("업무 배정이 되지 않았습니다. 기동 전 좌측 프로젝트 패널에서 에이전트에게 프로젝트를 할당해주세요.");
                return;
            }
        }
        
        setIsAnalyzing(true);
        setFinalReport('');
        setCurrentReportHtml('');
        setCurrentReportText('');
        setAgentReports({});
        setLastTokenUsage(null);
        if (agentPanelTab === 'auto') {
            setLeaderStatus({ step: 'planning', message: '요청 사항 분석 및 계획 수립 중...' });
            setFinalReport(`[오케스트레이션 자동 가동]\n- 분석할 요청 사항: ${logInput || '없음'}\n\n팀장이 요청을 분석하여 에이전트들에게 업무를 자동 배분합니다...`);
            setTimeout(() => setIsAnalyzing(false), 2000);
        } else {
            // 수동 모드: 배정된 에이전트들을 작업 상태로 변경
            let assignedCount = 0;
            const activeTeam = agents.filter(a => a.isActive && a.assignedProjects.length > 0 && a.role !== 'leader');
            activeTeam.forEach((agent, index) => {
                updateAgentStatus(agent.id, 'working');
                assignedCount++;
            });
            setFinalReport(`[에이전트 수동 기동 완료]\n- ${assignedCount}명의 에이전트가 할당된 프로젝트 분석 작업을 시작했습니다...\n- 백엔드 오케스트레이터를 호출합니다.`);
            
            // 1. API 통신 프로미스
            const apiCallPromise = (async () => {
                const response = await fetch('http://127.0.0.1:8000/api/v1/orchestrate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        jira_key: jiraKey.trim(),
                        log_text: logInput,
                        log_images: attachedImages,
                        working_agents: activeTeam,
                        projects: Array.from(new Set(activeTeam.flatMap(a => a.assignedProjects))),
                        run_development: runDevelopment,
                        create_branch: createBranch,
                        require_leader_feedback: requireLeaderFeedback,
                        run_testing: runTesting,
                        use_verify_loop: true
                    })
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || '백엔드 에러 발생');
                }
                return data;
            })();

            let simulationTimeoutId: number | null = null;
            let meetingTimeoutId: number | null = null;

            // 2. UI 시뮬레이션 프로미스 (실시간 병렬)
            const simulationPromise = new Promise<{ finished: boolean }>((resolveSim) => {
                const analysisDuration = 3000 + Math.random() * 2000;
                
                // 지정된 시간 후 회의실(debating)로 모임
                simulationTimeoutId = window.setTimeout(() => {
                    activeTeam.forEach(agent => {
                        updateAgentStatus(agent.id, 'debating');
                    });
                    setFinalReport(prev => prev + '\n\n[통합 리뷰]\n- 개별 분석을 마치고 회의실에서 토론을 시작합니다.');
                    
                    // 회의실에서 최소 3초 대기
                    meetingTimeoutId = window.setTimeout(() => {
                        resolveSim({ finished: true });
                    }, 3000);
                }, analysisDuration);
            });

            try {
                // 두 프로미스가 모두 끝날 때까지 대기 (회의실 모인 상태에서 백엔드 완료 기다림)
                const [apiData] = await Promise.all([apiCallPromise, simulationPromise]);
                
                setCurrentReportHtml(apiData.result_html || '');
                setCurrentReportText(apiData.result || '');
                setAgentReports(apiData.agent_reports || {});
                setLastTokenUsage(apiData.token_usage);
                setFinalReport(`[수동 분석 완료]\n- 실제 AI 리포트가 생성되었습니다. 탭에서 리포트를 확인하세요.`);
                
            } catch (error) {
                console.error('API Error:', error);
                setFinalReport(`[오류 발생]\n백엔드 오케스트레이터 호출에 실패했습니다.\n상세: ${String(error)}`);
            } finally {
                // 종료 시 모든 에이전트 자리로 복귀시키고 프로젝트 할당 초기화
                if (simulationTimeoutId) window.clearTimeout(simulationTimeoutId);
                if (meetingTimeoutId) window.clearTimeout(meetingTimeoutId);
                
                activeTeam.forEach((agent) => {
                    updateAgentStatus(agent.id, 'idle');
                    clearAgentProjects(agent.id);
                });
                setIsAnalyzing(false);
            }
        }
    };

    const handleStartAutoOrchestration = async () => {
        const leader = agents.find(a => a.role === 'leader');
        if (!leader || !leader.isActive) {
            alert('팀장이 출근하지 않았습니다! 팀장을 출근시킨 후 다시 시도해주세요.');
            return;
        }

        setIsAnalyzing(true);
        setFinalReport('');
        setAgentReports({});
        setSelectedReportAgentId('merged');
        setAutoPlan(null);

        setLeaderStatus({
            step: 'planning',
            message: '👔 팀장이 최적의 업무 배정 계획을 수립하고 있습니다...'
        });

        const activeTeam = agents.filter(a => a.isActive && a.role !== 'leader');
        
        const pollStatus = async () => {
            try {
                const res = await fetch('http://127.0.0.1:8000/api/v1/orchestrate/auto/status');
                const statusData = await res.json();
                
                setLeaderStatus({
                    step: statusData.step,
                    message: statusData.message,
                    assignments: statusData.assignments
                });

                const step = statusData.step;
                const assignments = statusData.assignments || [];
                
                if (step === 'planning') {
                    // 다 lounge 대기
                } else if (step === 'analyzing') {
                    assignments.forEach((asg: any) => {
                        const matched = agents.find(a => a.name === asg.agent_name);
                        if (matched) {
                            updateAgentStatus(matched.id, 'working', `${asg.projects.join(', ')} 분석 중 ⌨️`);
                        }
                    });
                    updateAgentStatus('agent_leader', 'working', '팀원들 작업 모니터링 중 👔');
                } else if (step === 'reviewing') {
                    assignments.forEach((asg: any) => {
                        const matched = agents.find(a => a.name === asg.agent_name);
                        if (matched) {
                            updateAgentStatus(matched.id, 'debating', '회의실에서 팀장과 의견 검토 중 💬');
                        }
                    });
                    updateAgentStatus('agent_leader', 'debating', '회의실에서 팀원 리포트 최종 검수 중 👔');
                }
            } catch (err) {
                console.error('Failed to poll status:', err);
            }
        };

        pollStatus();
        const pollTimer = window.setInterval(pollStatus, 2000);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/orchestrate/auto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jira_key: jiraKey.trim(),
                    log_text: logInput,
                    log_images: attachedImages,
                    available_agents: activeTeam.map(a => ({
                        id: a.id,
                        name: a.name,
                        role: a.role,
                        engine: a.engine
                    })),
                    available_projects: projects.map(p => p.id),
                    leader_engine: leader.engine,
                    run_development: runDevelopment,
                    create_branch: createBranch,
                    use_self_reflection: true,
                    use_verify_loop: true
                })
            });

            window.clearInterval(pollTimer);

            const data = await response.json();
            if (response.ok && data.status === 'success') {
                setFinalReport(data.result);
                if (data.result_html) {
                    setReportViewTab('visual');
                } else {
                    setReportViewTab('markdown');
                }
                
                if (data.agent_reports) {
                    setAgentReports(data.agent_reports);
                }

                if (data.token_usage) {
                    setLastTokenUsage(data.token_usage);
                }

                setLeaderStatus({
                    step: 'completed',
                    message: '✨ 최종 통합 리포트 작성이 완료되었습니다!'
                });

                const finalAssignments = data.plan?.assignments || [];
                const totalTokensUsed = data.token_usage?.total_tokens || data.result.length;
                if (finalAssignments.length > 0) {
                    const shareLoad = Math.floor(totalTokensUsed / finalAssignments.length);
                    finalAssignments.forEach((assignment: any) => {
                        const matchedAgent = agents.find(ag => ag.name === assignment.agent_name);
                        if (matchedAgent) {
                            increaseAgentLoad(matchedAgent.id, shareLoad);
                        }
                    });
                    increaseAgentLoad('agent_leader', totalTokensUsed);
                }

            } else {
                setFinalReport(`[오류 발생]\n백엔드 처리 중 오류가 발생했습니다.\n상세: ${data.detail || '알 수 없는 오류'}`);
                setLeaderStatus({
                    step: 'error',
                    message: '⚠️ 오류 발생'
                });
            }
        } catch (error) {
            window.clearInterval(pollTimer);
            console.error('API Error:', error);
            setFinalReport(`[오류 발생]\n백엔드 오케스트레이터 호출에 실패했습니다.\n상세: ${String(error)}`);
            setLeaderStatus({
                step: 'error',
                message: '⚠️ 오류 발생'
            });
        } finally {
            setIsAnalyzing(false);
            agents.forEach(a => {
                updateAgentStatus(a.id, 'idle');
                clearAgentProjects(a.id);
            });
        }
    };

    const handleStartSingleAgentOrchestration = async (agentId: string) => {
        const agent = agents.find(a => a.id === agentId);
        if (!agent) return;
        
        const req = individualInputs[agentId] || { jiraKey: '', logInput: '' };
        
        if (agent.status !== 'idle' || isAnalyzing) return;
        updateAgentStatus(agent.id, 'working');
        
        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/orchestrate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jira_key: req.jiraKey,
                    log_text: req.logInput,
                    log_images: attachedImages,
                    working_agents: [{ 
                        id: agent.id, 
                        name: agent.name, 
                        engine: agent.engine, 
                        role: agent.role, 
                        system_prompt: "" 
                    }],
                    projects: agent.assignedProjects
                })
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                setAgentReports(prev => ({...prev, [agent.id]: data.agent_reports[agent.id]}));
                setSelectedReportAgentId(agent.id);
                setReportViewTab('visual');
            }
        } catch (err) {
            console.error(err);
        } finally {
            updateAgentStatus(agent.id, 'idle');
        }
    };

    const renderDesk = (x: number, y: number, isLeaderDesk: boolean = false) => {
        const deskAgent = getDeskAgent(x, y);
        const isWorking = isDeskWorking(deskAgent);
        
        return (
            <div className="absolute" style={{ left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)', zIndex: 10 }}>
                {/* Desk shadow */}
                <div className="absolute w-14 h-8 bg-black/10 rounded-full blur-[2px] bottom-[-5px]" />
                <div className="w-14 h-10 flex flex-col items-center relative">
                    {/* Desk top */}
                    <div className={`w-14 h-7 ${isLeaderDesk ? 'bg-[#c39b6b] border-[#9b7348]' : 'bg-[#debf9f] border-[#c19b77]'} border-t-2 border-l-2 rounded-sm shadow-md flex justify-center items-end pb-1.5 relative z-10`}>
                        {/* Laptop/Monitor */}
                        <div className={`w-8 h-4.5 rounded-sm border-t border-l flex items-center justify-center relative ${isWorking ? 'bg-[#0f172a] border-[#020617] shadow-[0_-2px_10px_rgba(16,185,129,0.4)]' : 'bg-[#1e293b] border-[#0f172a]'}`}>
                            {isWorking && <div className="absolute inset-0 bg-emerald-500/10 animate-pulse rounded-sm" />}
                            {isWorking && <><div className="w-4 h-[1px] bg-emerald-400 opacity-90 rounded-full ml-0.5"/><div className="w-2 h-[1px] bg-cyan-400 opacity-90 rounded-full ml-0.5"/></>}
                            {/* Monitor Stand */}
                            <div className="absolute -bottom-1.5 w-2 h-1.5 bg-[#475569]" />
                        </div>
                    </div>
                    {/* Chair */}
                    <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex flex-col items-center z-0">
                        <div className="w-5 h-5 bg-[#334155] rounded-full border-2 border-[#1e293b]" />
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="flex min-h-screen bg-[#060b13] text-slate-100 font-sans">
            <style>{`
                .office-main-bg {
                    background-color: #9ba8b8;
                    background-image: 
                        linear-gradient(to right, rgba(0,0,0,0.04) 1px, transparent 1px),
                        linear-gradient(to bottom, rgba(0,0,0,0.04) 1px, transparent 1px);
                    background-size: 30px 30px;
                }
                .office-meeting-bg {
                    background-color: #f4f7fa;
                    background-image: 
                        linear-gradient(to right, #e2e8f0 1px, transparent 1px),
                        linear-gradient(to bottom, #e2e8f0 1px, transparent 1px);
                    background-size: 20px 20px;
                }
            `}</style>
            
            
            {/* 1. Left Column: Settings & Controls */}
            <div className="w-[380px] border-r border-slate-800/60 bg-[#0c121d] p-5 flex flex-col h-screen sticky top-0 gap-5 overflow-y-auto custom-scrollbar flex-shrink-0 z-20">
                
                {/* Mode Toggle */}
                <div className="flex p-1 bg-[#18212f] rounded-lg border border-slate-800">
                    <button 
                        onClick={() => setAgentPanelTab('manual')}
                        className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all ${agentPanelTab === 'manual' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/50 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        수동 (Manual)
                    </button>
                    <button 
                        onClick={() => setAgentPanelTab('auto')}
                        className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all flex items-center justify-center gap-1 ${agentPanelTab === 'auto' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <Bot className="w-3.5 h-3.5" /> 오토 모드
                    </button>
                </div>

                {/* Auto Mode Status Banner */}
                {agentPanelTab === 'auto' && (
                    <div className="bg-[#121926] p-3 rounded-lg border border-emerald-500/30">
                        <div className="flex items-center gap-2 mb-2">
                            <Bot className="w-4 h-4 text-emerald-400" />
                            <h3 className="text-[11px] font-bold text-emerald-400">오케스트레이터 가동 중</h3>
                        </div>
                        <div className="text-[10px] text-slate-300 bg-[#090d16] p-2 rounded border border-slate-800">
                            상태: <span className="font-bold text-emerald-300">{leaderStatus?.message || '대기 중'}</span>
                        </div>
                        {leaderStatus?.step !== 'idle' && leaderStatus?.step !== 'completed' && (
                            <div className="mt-2 w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                                <div className="bg-emerald-500 h-full animate-pulse w-full"></div>
                            </div>
                        )}
                    </div>
                )}



                {/* Project List Rendering (Match Original Screenshot + Add/Delete Feature) */}
                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-3">
                    <div className="flex justify-between items-center mb-1">
                        <h2 className="text-[12px] font-extrabold text-slate-300">프로젝트 목록</h2>
                        <button onClick={() => setIsAddingProject(!isAddingProject)} className="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-1 transition-colors">
                            {isAddingProject ? <X className="w-3 h-3" /> : <PlusCircle className="w-3 h-3" />} {isAddingProject ? '취소' : '추가'}
                        </button>
                    </div>

                    {isAddingProject && (
                        <div className="flex gap-2 bg-[#121926] p-2 rounded-lg border border-emerald-500/30 flex-col">
                            <select 
                                value={newProjectName} 
                                onChange={(e) => setNewProjectName(e.target.value)} 
                                className="w-full bg-[#090d16] text-xs px-2 py-1.5 rounded border border-slate-700 text-slate-100 outline-none focus:border-emerald-500/50"
                            >
                                <option value="">IdeaProjects 하위 폴더 선택...</option>
                                {localDirectories.map(dir => (
                                    <option key={dir} value={dir}>{dir}</option>
                                ))}
                            </select>
                            <div className="flex gap-2 w-full">
                                <input 
                                    type="text" 
                                    value={newProjectName} 
                                    onChange={(e) => setNewProjectName(e.target.value)} 
                                    placeholder="또는 수동 입력..." 
                                    className="flex-1 bg-[#090d16] text-xs px-2 py-1.5 rounded border border-slate-700 text-slate-100 outline-none focus:border-emerald-500/50" 
                                    onKeyDown={(e) => e.key === 'Enter' && handleAddProject()}
                                />
                                <button onClick={handleAddProject} className="bg-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded text-[10px] font-bold hover:bg-emerald-500/30 whitespace-nowrap">확인</button>
                            </div>
                        </div>
                    )}

                    {projects.map(proj => (
                        <div key={proj.id} className="bg-[#121926] border border-slate-800/80 rounded-xl p-3.5 shadow-sm group">
                            <div className="flex justify-between items-start mb-2.5">
                                <div className="text-[11px] font-extrabold text-slate-200">
                                    {proj.name}
                                </div>
                                <button onClick={() => deleteProject(proj.id)} className="text-slate-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-all">
                                    <Trash2 className="w-3 h-3" />
                                </button>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {agents.filter(a => a.role !== 'leader').map((agent, idx) => {
                                    const isAssigned = agent.assignedProjects.includes(proj.id);
                                    const roleStr = agent.role === 'backend' ? 'BE' : 'FE';
                                    const colorTheme = isAssigned ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-slate-900 border-slate-700 text-slate-500 hover:border-slate-600';
                                    
                                    return (
                                        <button 
                                            key={agent.id} 
                                            onClick={() => assignProjectToAgent(agent.id, proj.id)}
                                            className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold cursor-pointer transition-all border ${colorTheme}`}
                                        >
                                            {renderPixelFace(agent.id, agents.findIndex(a => a.id === agent.id), 12)}
                                            {roleStr}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Request Form */}
                <div className="flex flex-col gap-3 mt-4 border-t border-slate-800/60 pt-4">
                    <div className="flex gap-2 border-b border-slate-800 pb-1">
                        <button onClick={() => setRequestMode('unified')} className={`px-4 py-1.5 text-xs font-bold rounded-t-md transition-all ${requestMode === 'unified' ? 'bg-emerald-500/10 text-emerald-400 border-b-2 border-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}>통합 요청</button>
                        <button onClick={() => setRequestMode('individual')} className={`px-4 py-1.5 text-xs font-bold rounded-t-md transition-all ${requestMode === 'individual' ? 'bg-emerald-500/10 text-emerald-400 border-b-2 border-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}>에이전트별 개별 요청</button>
                    </div>

                    {requestMode === 'unified' ? (
                        <>
                            <div className="space-y-1">
                                <label className="block text-slate-400 text-[10px] font-bold">Jira Issue Key (선택)</label>
                                <input type="text" value={jiraKey} onChange={(e) => setJiraKey(e.target.value)} className="w-full bg-[#090d16] border border-slate-800/80 rounded px-3 py-2 text-xs text-slate-100 font-mono" />
                            </div>

                            <textarea 
                                placeholder="분석할 로그 덤프 혹은 지시사항... (클립보드 이미지 붙여넣기 가능)" 
                                value={logInput} 
                                onChange={(e) => setLogInput(e.target.value)} 
                                onPaste={handlePaste}
                                className="w-full h-28 bg-[#090d16] border border-slate-800/80 rounded px-3 py-2 text-xs text-slate-100 resize-none custom-scrollbar" 
                            />

                            {/* 첨부 이미지 미리보기 */}
                            {attachedImages.length > 0 && (
                                <div className="flex gap-2 overflow-x-auto py-2 custom-scrollbar">
                                    {attachedImages.map((img, idx) => (
                                        <div key={idx} className="relative flex-shrink-0 group">
                                            <img src={img} alt={`attached-${idx}`} className="h-16 rounded border border-slate-700" />
                                            <button 
                                                onClick={() => removeImage(idx)}
                                                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity shadow-md"
                                            >
                                                <X className="w-3 h-3" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Options Box */}
                            <div className="border border-slate-800/80 rounded-lg p-3 bg-[#121926] mt-1">
                                <div className="text-[10px] font-extrabold text-slate-400 mb-2 flex items-center gap-1">
                                    <Edit2 className="w-3 h-3" /> 작업 옵션 설정
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <label className="flex items-center gap-2 cursor-pointer hover:text-slate-350 select-none">
                                        <input type="checkbox" checked={createBranch} onChange={(e) => setCreateBranch(e.target.checked)} className="accent-emerald-500 w-3.5 h-3.5" />
                                        <div>
                                            <div className="text-[11px] font-bold text-slate-200">브랜치 생성</div>
                                            <div className="text-[9px] text-slate-500">지라 연동하여 신규 브랜치 생성</div>
                                        </div>
                                    </label>
                                    <label className="flex items-center gap-2 cursor-pointer hover:text-slate-350 select-none">
                                        <input type="checkbox" checked={runDevelopment} onChange={(e) => {
                                            setRunDevelopment(e.target.checked);
                                            if (!e.target.checked) setRunTesting(false);
                                        }} className="accent-emerald-500 w-3.5 h-3.5" />
                                        <div>
                                            <div className="text-[11px] font-bold text-slate-200">개발 진행</div>
                                            <div className="text-[9px] text-slate-500">분석 결과를 바탕으로 개발 수행</div>
                                        </div>
                                    </label>
                                </div>
                                <div className="grid grid-cols-2 gap-3 mt-3">
                                    <label className="flex items-center gap-2 cursor-pointer hover:text-slate-350 select-none">
                                        <input type="checkbox" checked={requireLeaderFeedback} onChange={(e) => setRequireLeaderFeedback(e.target.checked)} className="accent-indigo-500 w-3.5 h-3.5" />
                                        <div>
                                            <div className="text-[11px] font-bold text-slate-200">팀장 피드백</div>
                                            <div className="text-[9px] text-slate-500">리더 에이전트 교차 검증</div>
                                        </div>
                                    </label>
                                    <label className={`flex items-center gap-2 select-none ${runDevelopment ? 'cursor-pointer hover:text-slate-350' : 'cursor-not-allowed opacity-50'}`}>
                                        <input type="checkbox" disabled={!runDevelopment} checked={runTesting} onChange={(e) => setRunTesting(e.target.checked)} className="accent-indigo-500 w-3.5 h-3.5" />
                                        <div>
                                            <div className="text-[11px] font-bold text-slate-200">테스트 진행</div>
                                            <div className="text-[9px] text-slate-500">테스트 코드 작성 및 검증</div>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <div className="flex gap-2 mt-2">
                                <button 
                                    onClick={agentPanelTab === 'auto' ? handleStartAutoOrchestration : handleStartOrchestration} 
                                    disabled={(agentPanelTab === 'auto' && leaderStatus?.step !== 'idle') || isAnalyzing}
                                    className={`flex-1 font-black py-3 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm shadow-lg ${
                                        (agentPanelTab === 'auto' && leaderStatus?.step !== 'idle') || isAnalyzing 
                                        ? 'bg-slate-700 text-slate-400 cursor-not-allowed' 
                                        : 'bg-emerald-500 hover:bg-emerald-400 text-[#060b13]'
                                    }`}
                                >
                                    <Play className="w-4 h-4 fill-current" /> 
                                    {agentPanelTab === 'auto' && leaderStatus?.step !== 'idle' 
                                        ? leaderStatus.message 
                                        : (isAnalyzing ? '기동 중...' : '▶ 에이전트 기동')
                                    }
                                </button>
                                <button className="bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg p-3 border border-slate-700 transition-colors shadow-lg">
                                    <RefreshCw className="w-4 h-4" />
                                </button>
                            </div>
                        </>
                    ) : (
                        <div className="flex flex-col gap-3 mt-1 h-[400px] overflow-y-auto custom-scrollbar pr-2">
                            {agents.filter(a => a.isActive && a.role !== 'leader').map(agent => {
                                const req = individualRequests[agent.id] || { jiraKey: '', logInput: '' };
                                return (
                                    <div key={agent.id} className="border border-slate-700/60 rounded-xl bg-[#131b2b] p-3 shadow-md flex flex-col gap-2">
                                        <div className="flex justify-between items-center border-b border-slate-800 pb-2">
                                            <div className="font-extrabold text-xs flex items-center gap-2 text-slate-200">
                                                <Bot className="w-3.5 h-3.5 text-emerald-400" />
                                                {agent.name}
                                            </div>
                                            <div className="text-[9px] text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-bold">
                                                {agent.engine}
                                            </div>
                                        </div>
                                        <input 
                                            type="text" 
                                            placeholder="Jira Issue Key"
                                            value={req.jiraKey} 
                                            onChange={(e) => setIndividualRequests(prev => ({...prev, [agent.id]: { ...req, jiraKey: e.target.value }}))} 
                                            className="w-full bg-[#090d16] border border-slate-800/80 rounded px-2 py-1.5 text-[10px] text-slate-100 font-mono" 
                                        />
                                        <textarea 
                                            placeholder="개별 지시사항 및 에러 로그... (클립보드 이미지 붙여넣기 가능)" 
                                            value={req.logInput} 
                                            onChange={(e) => setIndividualRequests(prev => ({...prev, [agent.id]: { ...req, logInput: e.target.value }}))} 
                                            onPaste={handlePaste}
                                            className="w-full h-16 bg-[#090d16] border border-slate-800/80 rounded px-2 py-1.5 text-[10px] text-slate-100 resize-none custom-scrollbar" 
                                        />
                                        
                                        {/* 개별 폼 아래에도 공통 첨부 이미지 미리보기 노출 */}
                                        {attachedImages.length > 0 && (
                                            <div className="flex gap-2 overflow-x-auto py-1 custom-scrollbar">
                                                {attachedImages.map((img, idx) => (
                                                    <div key={idx} className="relative flex-shrink-0 group">
                                                        <img src={img} alt={`attached-${idx}`} className="h-10 rounded border border-slate-700" />
                                                        <button 
                                                            onClick={() => removeImage(idx)}
                                                            className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity shadow-md"
                                                        >
                                                            <X className="w-2.5 h-2.5" />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <button 
                                            onClick={() => handleStartSingleAgentOrchestration(agent.id)}
                                            disabled={isAnalyzing || agent.status !== 'idle'}
                                            className={`w-full py-1.5 mt-1 rounded text-xs font-bold transition-all shadow-sm flex justify-center items-center gap-1 ${
                                                isAnalyzing || agent.status !== 'idle' 
                                                ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                                                : 'bg-indigo-500/20 text-indigo-400 hover:bg-indigo-500/30 border border-indigo-500/30'
                                            }`}
                                        >
                                            <Play className="w-3 h-3" /> {agent.status !== 'idle' ? '기동 중...' : '이 에이전트만 단독 실행'}
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* 2. Center Column: Office Grid & Report Viewer */}
            <div className="flex-1 flex flex-col p-5 gap-5 select-none bg-[#090d16]">
                
                {/* 3-Room Layout Office Grid */}
                <div ref={officeRef} className="flex-none min-h-[500px] relative rounded-xl overflow-hidden border-4 border-[#5a6a7c] shadow-2xl flex">
                    
                    {/* Main Workspace (65%) */}
                    <div className="w-[65%] h-full office-main-bg relative z-0 border-r-4 border-[#78889a]">
                        {renderPottedTree(4, 10)}
                        {renderPottedTree(92, 10)}
                        {renderPottedTree(4, 60)}
                        {renderPottedTree(92, 60)}

                        {/* Row 1 */}
                        {renderDesk(12, 15)} {renderDesk(36, 15)} {renderDesk(60, 15)} {renderDesk(84, 15)}
                        {/* Row 2 */}
                        {renderDesk(12, 40)} {renderDesk(36, 40)} {renderDesk(60, 40)} {renderDesk(84, 40)}
                        {/* Row 3 */}
                        {renderDesk(12, 65)} {renderDesk(36, 65)} {renderDesk(60, 65)} {renderDesk(84, 65)}
                        
                        {/* Leader Desk (Pushed down) */}
                        {renderDesk(48, 80, true)}
                    </div>
                    
                    {/* Right Area (35%) */}
                    <div className="w-[35%] h-full flex flex-col z-0">
                        {/* Meeting Room (65%) */}
                        <div className="h-[65%] office-meeting-bg relative border-b-4 border-[#78889a] flex items-center justify-center">
                            {/* Whiteboard */}
                            <div className="absolute top-2 w-[70%] h-[12%] bg-white border-2 border-[#cbd5e1] rounded shadow-sm flex flex-col items-center justify-center">
                                <div className="flex gap-1 mb-1">
                                    <div className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                                </div>
                                <div className="w-[80%] h-1 bg-slate-200 rounded-full" />
                                <div className="w-[50%] h-1 bg-slate-200 rounded-full mt-1" />
                            </div>
                            
                            {/* Oval Table */}
                            <div className="w-[60%] h-[20%] bg-white rounded-full border-2 border-[#cbd5e1] shadow-lg absolute bottom-[30%] z-10 flex items-center justify-center">
                                <div className="w-[85%] h-[60%] border border-[#e2e8f0] rounded-full" />
                            </div>
                            
                            {/* Chairs (dots) */}
                            <div className="absolute w-[60%] h-[20%] bottom-[30%] flex flex-wrap justify-between items-center z-0 px-2 pointer-events-none">
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -top-1 left-[20%]" />
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -top-1 left-[50%] -translate-x-1/2" />
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -top-1 right-[20%]" />
                                
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -bottom-1 left-[20%]" />
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -bottom-1 left-[50%] -translate-x-1/2" />
                                <div className="w-3 h-3 bg-slate-600 rounded-full absolute -bottom-1 right-[20%]" />
                            </div>
                        </div>
                        
                        {/* Lounge (35%) */}
                        <div className="h-[35%] bg-white relative">
                            {/* LOUNGE badge */}
                            <div className="absolute top-3 left-3 border-2 border-emerald-400 rounded-full px-2 py-0.5 text-[8px] font-bold text-emerald-500 bg-white shadow-sm flex items-center gap-1 z-10">
                                ☕ LOUNGE
                            </div>
                            <div className="absolute top-3 right-3 border border-orange-300 rounded-full px-2 py-0.5 text-[8px] font-bold text-orange-500 bg-white shadow-sm flex items-center gap-1 z-10">
                                COFFEE <div className="w-3 h-1 bg-orange-400 rounded-full ml-1" />
                            </div>
                            
                            {/* Coffee machine */}
                            <div className="absolute top-[35%] left-6 w-8 h-12 bg-slate-800 rounded flex flex-col items-center p-1 z-10 shadow-md border-b-4 border-[#78350f]">
                                <div className="w-5 h-5 bg-slate-900 rounded-sm mb-1 flex items-center justify-center border border-slate-700">
                                    <div className="w-2 h-2 bg-emerald-400 rounded-full" />
                                </div>
                                <div className="w-1.5 h-1.5 bg-slate-400 rounded-b-sm" />
                                <div className="w-full flex-1 flex items-end justify-center pb-0.5">
                                    <div className="text-[10px] leading-none mb-0.5">☕</div>
                                </div>
                            </div>
                            
                            {/* Lounge Tables (White Round) */}
                            <div className="absolute right-[20%] top-[30%] flex flex-col items-center justify-center z-10">
                                <div className="w-4 h-4 bg-slate-400 rounded-full mb-1 shadow-sm" />
                                <div className="w-10 h-10 bg-white rounded-full shadow-lg border-2 border-[#e2e8f0]" />
                                <div className="w-4 h-4 bg-slate-400 rounded-full mt-1 shadow-sm" />
                            </div>
                            
                            <div className="absolute left-[25%] bottom-[20%] flex items-center justify-center z-10">
                                <div className="w-4 h-4 bg-slate-400 rounded-full mr-1 shadow-sm" />
                                <div className="w-10 h-10 bg-white rounded-full shadow-lg border-2 border-[#e2e8f0]" />
                                <div className="w-4 h-4 bg-slate-400 rounded-full ml-1 shadow-sm" />
                            </div>
                        </div>
                    </div>

                    {/* Render Agents over everything */}
                    {agents.filter(a => a.isActive).map((agent, index) => {
                        const pos = getAgentOfficePosition(agent, index, agentPanelTab === 'auto');
                        const preset = getCharacterPreset(agent.id, index);
                        const direction = getAgentDirection(agent, index, agentPanelTab === 'auto', leaderStatus?.step, presenterId);
                        
                        return (
                            <div 
                                key={`agent-${agent.id}`} 
                                className={`absolute z-30 transition-all ${draggingAgentId === agent.id ? 'duration-0 scale-110 cursor-grabbing' : 'duration-1000 cursor-grab hover:scale-105'} ease-in-out flex flex-col items-center`} 
                                style={{ 
                                    left: `${pos.x}%`, 
                                    top: pos.isManual ? `${pos.y}%` : `calc(${pos.y}% + 24px)`, 
                                    transform: 'translate(-50%, -50%)' 
                                }}
                                onMouseDown={(e) => handleMouseDown(e, agent.id)}
                                onDoubleClick={() => updateAgentPosition(agent.id, undefined)} // 더블클릭 시 수동 위치 해제
                            >
                                {/* Speech Bubble */}
                                {agent.status === 'debating' && (
                                    <div className="absolute -top-10 bg-[#1e293b] text-white text-[9px] font-extrabold px-3 py-1.5 rounded-full border-2 border-slate-700 shadow-lg whitespace-nowrap z-50">
                                        {agent.id === presenterId 
                                            ? ["문제 원인을 발견했습니다!", "이 부분 로직이 의심됩니다", "로그를 보면 여기서 실패하네요", "DB 병목이 원인인 듯 합니다", "정확한 코드 라인을 찾았습니다"][(agent.id.charCodeAt(agent.id.length - 1) + meetingTick) % 5]
                                            : ["오, 일리 있네요!", "그 부분 자세히 보죠", "동의합니다!", "조금 다른 생각입니다만..", "빠르게 수정해봅시다", "로그 확인해볼까요?"][(agent.id.charCodeAt(agent.id.length - 1) + meetingTick) % 6]
                                        }
                                        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-[#1e293b] border-r-2 border-b-2 border-slate-700 transform rotate-45" />
                                    </div>
                                )}
                                <div className="bg-[#18181b] text-white text-[9px] font-extrabold px-1.5 py-0.5 rounded border border-slate-700 shadow-sm leading-none whitespace-nowrap mb-1">{agent.name}</div>
                                {agent.role === 'leader' && (
                                    <div className="bg-orange-500/20 text-orange-400 text-[8px] font-bold px-1.5 py-0.5 rounded border border-orange-500/30 mb-1 leading-none shadow-sm whitespace-nowrap flex items-center justify-center">
                                        [{agent.engine}]
                                    </div>
                                )}
                                {agent.role === 'leader' ? renderLeaderSprite(direction) : renderPixelSprite(direction, preset, false)}
                                <div className="w-8 h-1 bg-black/30 rounded-full filter blur-[1px] mt-0.5" />
                            </div>
                        );
                    })}
                </div>

                {/* Report Viewer */}
                <div className="flex-none min-h-[600px] flex flex-col bg-[#0c121d] border border-slate-800/80 rounded-xl p-5 shadow-xl overflow-hidden">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-3 mb-3">
                        <h2 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
                            <FileText className="w-4 h-4 text-emerald-400" /> 📄 에이전트 오케스트레이션 보고서 뷰어
                        </h2>
                        {lastTokenUsage && (
                            <span className="text-[9px] text-slate-500 font-mono">
                                토큰 사용량: {lastTokenUsage.total_tokens.toLocaleString()} (P: {lastTokenUsage.prompt_tokens.toLocaleString()} / C: {lastTokenUsage.completion_tokens.toLocaleString()})
                            </span>
                        )}
                    </div>
                    
                    <div className="flex gap-2 mb-3">
                        <button onClick={() => setReportViewTab('visual')} className={`px-4 py-1.5 text-xs font-bold rounded border transition-all flex items-center gap-2 ${reportViewTab === 'visual' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40' : 'bg-slate-900 border-slate-800 text-slate-400'}`}>
                            <div className={`w-2 h-2 rounded-full ${reportViewTab === 'visual' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                            비주얼 리포트 (Flowchart)
                        </button>
                        <button onClick={() => setReportViewTab('markdown')} className={`px-4 py-1.5 text-xs font-bold rounded border transition-all flex items-center gap-2 ${reportViewTab === 'markdown' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40' : 'bg-slate-900 border-slate-800 text-slate-400'}`}>
                            <div className={`w-2 h-2 rounded-full ${reportViewTab === 'markdown' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                            마크다운 텍스트
                        </button>
                    </div>

                    <div className="flex gap-4 mb-4 text-xs font-bold border-b border-slate-800 pb-2 overflow-x-auto custom-scrollbar">
                        <button onClick={() => setSelectedReportAgentId('merged')} className={`flex items-center gap-1.5 transition-colors whitespace-nowrap ${selectedReportAgentId === 'merged' ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-300'}`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${selectedReportAgentId === 'merged' ? 'bg-emerald-400' : 'bg-transparent'}`} /> 통합 리포트
                        </button>
                        {Object.keys(agentReports).map(agentId => {
                            const agentInfo = agents.find(a => a.id === agentId);
                            const displayName = agentInfo ? agentInfo.name : agentId;
                            return (
                                <button key={agentId} onClick={() => setSelectedReportAgentId(agentId)} className={`flex items-center gap-1.5 transition-colors whitespace-nowrap ${selectedReportAgentId === agentId ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-300'}`}>
                                    <div className={`w-1.5 h-1.5 rounded-full ${selectedReportAgentId === agentId ? 'bg-emerald-400' : 'bg-slate-700'}`} /> {displayName}
                                </button>
                            );
                        })}
                    </div>

                    <div className="flex-1 bg-[#090d16] border border-slate-800/50 rounded-lg p-4 overflow-hidden">
                        {isAnalyzing ? (
                            <div className="text-slate-400 text-sm flex flex-col items-center justify-center h-full gap-5">
                                <div className="w-12 h-12 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin" />
                                <div className="animate-pulse text-emerald-300 font-extrabold whitespace-pre-wrap text-center leading-relaxed">
                                    {finalReport || 'AI 에이전트가 코드를 샅샅이 분석하고 있습니다...'}
                                </div>
                                <div className="flex flex-col items-center mt-2 space-y-1.5 w-full">
                                    {loadingLogs.map((log, i) => (
                                        <div key={i} className="text-[11px] text-slate-500 font-mono opacity-80">
                                            &gt; {log}
                                        </div>
                                    ))}
                                    <div className="text-[11px] text-emerald-500/70 font-mono animate-pulse">
                                        &gt; _
                                    </div>
                                </div>
                            </div>
                        ) : selectedReportAgentId === 'merged' ? (
                            reportViewTab === 'visual' && currentReportHtml ? (
                                <iframe srcDoc={currentReportHtml} className="w-full h-full border-none bg-transparent" sandbox="allow-scripts" />
                            ) : (
                                <div className="font-mono text-sm leading-relaxed overflow-y-auto h-full text-slate-100 whitespace-pre-wrap custom-scrollbar">
                                    {currentReportText || finalReport || '결과가 없습니다.'}
                                </div>
                            )
                        ) : (
                            reportViewTab === 'visual' && agentReports[selectedReportAgentId]?.result_html ? (
                                <iframe srcDoc={agentReports[selectedReportAgentId].result_html} className="w-full h-full border-none bg-transparent" sandbox="allow-scripts" />
                            ) : (
                                <div className="font-mono text-sm leading-relaxed overflow-y-auto h-full text-slate-100 whitespace-pre-wrap custom-scrollbar">
                                    {agentReports[selectedReportAgentId]?.result || '해당 에이전트의 개별 분석 결과가 없습니다.'}
                                </div>
                            )
                        )}
                    </div>
                </div>
            </div>

            {/* 3. Right Column: Rosters & Chat */}
            <div className="w-[360px] border-l border-slate-800/60 bg-[#0c121d] p-5 flex flex-col h-screen sticky top-0 overflow-y-auto custom-scrollbar flex-shrink-0">
                <div className="flex justify-between items-center mb-4 px-1">
                    <div className="text-[10px] font-bold text-slate-400">
                        카드를 클릭하면 에이전트가 오피스로 즉시 출근합니다.
                    </div>
                    <button onClick={handleCreateNewAgent} className="text-[10px] text-emerald-400 font-bold hover:text-emerald-300 flex items-center gap-1 transition-colors bg-emerald-500/10 px-2 py-1 rounded">
                        <UserPlus className="w-3 h-3" /> 영입
                    </button>
                </div>
                
                <div className="space-y-4">
                    {[...agents].sort((a, b) => (a.role === 'leader' ? -1 : (b.role === 'leader' ? 1 : 0))).map((agent, idx) => {
                        const isLeader = agent.role === 'leader';
                        const themeColor = isLeader ? 'orange' : 'emerald';
                        const cardBorder = agent.isActive ? `border-${themeColor}-500/50` : 'border-slate-800';
                        const cardBg = agent.isActive ? (isLeader ? 'bg-[#1a1105]' : 'bg-[#0f172a]/60') : 'bg-[#090d16]';
                        
                        return (
                            <div key={agent.id} onClick={() => toggleAgentActive(agent.id)} className={`border ${cardBorder} rounded-xl p-4 ${cardBg} cursor-pointer transition-all hover:border-${themeColor}-500/30`}>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex gap-3">
                                        <div className={`w-10 h-10 rounded-lg border flex items-center justify-center bg-slate-900 ${agent.isActive ? `border-${themeColor}-500/30` : 'border-slate-700'}`}>
                                            {renderPixelFace(agent.id, idx, 32)}
                                        </div>
                                        <div>
                                            <div className={`font-extrabold text-sm ${isLeader ? 'text-orange-400' : 'text-slate-200'}`}>
                                                {isLeader && <span className="mr-1">👑</span>}
                                                {agent.name}
                                            </div>
                                            <div className="text-[9px] text-slate-500 mt-0.5">
                                                엔진: {agent.engine} ({agent.role})
                                            </div>
                                            <div className={`mt-1.5 inline-flex text-[9px] px-1.5 py-0.5 rounded font-bold ${agent.isActive ? `bg-${themeColor}-500/10 text-${themeColor}-400 border border-${themeColor}-500/20` : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
                                                상태: {agent.status === 'idle' ? '대기 중' : '작업 중'}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end gap-2">
                                        <div className="flex gap-1.5 items-center">
                                            {agent.isActive && (agent.stress || 0) > 0 && (
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); reduceAgentStress(agent.id, 20); }} 
                                                    className="text-[10px] bg-orange-500/20 text-orange-400 hover:bg-orange-500/40 border border-orange-500/30 rounded px-1.5 py-0.5 transition-colors"
                                                    title="커피 마시고 스트레스 -20%"
                                                >
                                                    ☕
                                                </button>
                                            )}
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); setEditingAgent(agent); }} 
                                                className="text-slate-500 hover:text-emerald-400 transition-colors p-1"
                                                title="설정 편집"
                                            >
                                                <Edit2 className="w-3 h-3" />
                                            </button>
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); deleteAgent(agent.id); }} 
                                                className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                                                title="에이전트 삭제"
                                            >
                                                <Trash2 className="w-3 h-3" />
                                            </button>
                                        </div>
                                        <button className={`border rounded px-3 py-1 text-xs font-bold transition-colors ${agent.isActive ? `border-${themeColor}-500 text-${themeColor}-400 bg-${themeColor}-500/10` : 'border-slate-700 text-slate-500'}`}>
                                            {agent.isActive ? '출근 중' : '출근 전'}
                                        </button>
                                    </div>
                                </div>
                                
                                <div>
                                    <div className="flex justify-between items-center text-[10px] mb-1.5">
                                        <div className="flex items-center gap-1 font-bold text-slate-400">
                                            <span className="text-[12px]">🔥</span> 스트레스 지수:
                                        </div>
                                        <span className={`font-bold ${(agent.stress || 0) > 50 ? 'text-yellow-500' : 'text-emerald-400'}`}>
                                            {(agent.stress || 0)}% {(agent.stress || 0) > 50 ? '⚡ 누적' : '🟢 쾌적'}
                                        </span>
                                    </div>
                                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                        <div className={`h-full transition-all duration-1000 ${(agent.stress || 0) > 50 ? 'bg-orange-500' : 'bg-emerald-500'}`} style={{ width: `${(agent.stress || 0)}%` }} />
                                    </div>
                                    <div className="flex justify-between items-center text-[9px] text-slate-500 font-mono mt-2">
                                        <div className="flex items-center gap-1">
                                            <div className={`w-1.5 h-1.5 rounded-sm ${agent.isActive ? `bg-${themeColor}-400` : 'bg-slate-700'}`} />
                                            📊 일일 분석 처리량:
                                        </div>
                                        <span className="font-bold text-slate-300">{(agent.totalTokens || 0).toLocaleString()} 토큰</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Agent Edit Modal */}
            {editingAgent && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center backdrop-blur-sm">
                    <div className="bg-[#0c121d] border border-slate-700 rounded-xl w-[320px] shadow-2xl p-5" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center mb-4 border-b border-slate-800 pb-3">
                            <h2 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
                                <Users className="w-4 h-4 text-emerald-400" /> 에이전트 설정
                            </h2>
                            <button onClick={() => setEditingAgent(null)} className="text-slate-500 hover:text-slate-300">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 mb-1">이름</label>
                                <input 
                                    type="text" 
                                    value={editingAgent.name} 
                                    onChange={(e) => setEditingAgent({...editingAgent, name: e.target.value})}
                                    className="w-full bg-[#090d16] border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 outline-none focus:border-emerald-500/50"
                                />
                            </div>
                            
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 mb-1">역할 (Role)</label>
                                <div className="flex gap-2">
                                    {(['backend', 'frontend', 'leader'] as const).map(role => (
                                        <button 
                                            key={role}
                                            onClick={() => setEditingAgent({...editingAgent, role})}
                                            className={`flex-1 py-1.5 text-xs font-bold rounded border transition-colors ${editingAgent.role === role ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-slate-900 border-slate-700 text-slate-500'}`}
                                        >
                                            {role === 'backend' ? 'BE' : role === 'frontend' ? 'FE' : 'Leader'}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-[10px] font-bold text-slate-400 mb-1">엔진 (Engine)</label>
                                <select 
                                    value={editingAgent.engine}
                                    onChange={(e) => setEditingAgent({...editingAgent, engine: e.target.value as any})}
                                    className="w-full bg-[#090d16] border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 outline-none focus:border-emerald-500/50"
                                >
                                    <option value="Gemini-Flash">Gemini-Flash</option>
                                    <option value="Gemini-Pro">Gemini-Pro</option>
                                    <option value="Claude-CLI">Claude-CLI (로컬)</option>
                                    <option value="Claude" disabled>Claude 3.5 Sonnet (API 키 필요)</option>
                                    <option value="GPT-4" disabled>GPT-4o (API 키 필요)</option>
                                </select>
                            </div>
                            
                            <div className="pt-4 flex gap-2">
                                <button onClick={() => setEditingAgent(null)} className="flex-1 py-2 text-xs font-bold text-slate-400 bg-slate-800 rounded hover:bg-slate-700 transition-colors">취소</button>
                                <button onClick={handleSaveAgent} className="flex-1 py-2 text-xs font-bold text-[#060b13] bg-emerald-500 rounded hover:bg-emerald-400 flex items-center justify-center gap-1 transition-colors"><Save className="w-3 h-3"/> 저장</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}

export default function App() {
    return (
        <AgentsProvider>
            <Dashboard />
        </AgentsProvider>
    );
}