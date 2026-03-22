import { create } from 'zustand';
import { ExpertType, ExpertStatus, ToolCall } from '../components/ExpertCard';

// ============================================
// Types
// ============================================

/**
 * Agent思考面板的动画阶段
 * collapsed:  收起状态，三张扑克牌散开
 * idle:       分析未开始前的稳定状态
 * merging:    叠卡阶段，三张牌向中心聚拢成叠
 * orb:        圆标阶段，叠卡变形为协调者呼吸圆标
 * dealing:    发牌阶段，圆标裂开，三张牌依次飞出
 * flipping:   翻牌阶段，三张牌依次翻面揭示内容
 * streaming:  思维流阶段，右侧显示Claude风格思考流
 */
export type AgentAnimationPhase =
  | 'collapsed'
  | 'idle'
  | 'merging'
  | 'orb'
  | 'dealing'
  | 'flipping'
  | 'streaming';

export interface ExpertAgentState {
  status: ExpertStatus;
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
  subtitle: string; // 动态副标题
}

export interface OrchestratorState {
  subtitle: string; // 协调者动态副标题
  content: string;  // 综合流式内容
}

export interface AgentStore {
  // 动画阶段
  phase: AgentAnimationPhase;
  setPhase: (phase: AgentAnimationPhase) => void;

  // 三位专家状态
  experts: Record<ExpertType, ExpertAgentState>;

  // 协调者状态
  orchestrator: OrchestratorState;

  // 面板激活状态（由父组件控制）
  isPanelActive: boolean;
  setPanelActive: (v: boolean) => void;

  // 分析状态
  isAnalyzing: boolean;
  setAnalyzing: (v: boolean) => void;

  // 重置全部状态
  resetAll: () => void;

  // 更新单专家状态（partial update）
  updateExpert: (
    type: ExpertType,
    update: Partial<ExpertAgentState>
  ) => void;

  // 追加专家思考内容（流式）
  appendExpertThinking: (type: ExpertType, chunk: string) => void;

  // 添加工具调用
  addExpertToolCall: (
    type: ExpertType,
    toolCall: ToolCall
  ) => void;

  // 更新协调者副标题
  updateOrchestratorSubtitle: (subtitle: string) => void;

  // 追加协调者内容
  appendOrchestratorContent: (chunk: string) => void;
}

// ============================================
// Initial States
// ============================================

const initialExpertState: Record<ExpertType, ExpertAgentState> = {
  tactics: {
    status: 'idle',
    thinkingContent: '',
    toolCalls: [],
    finding: '',
    subtitle: '',
  },
  strategy: {
    status: 'idle',
    thinkingContent: '',
    toolCalls: [],
    finding: '',
    subtitle: '',
  },
  engine: {
    status: 'idle',
    thinkingContent: '',
    toolCalls: [],
    finding: '',
    subtitle: '',
  },
};

// ============================================
// Store
// ============================================

export const useAgentStore = create<AgentStore>((set) => ({
  phase: 'collapsed',
  setPhase: (phase) => set({ phase }),

  experts: { ...initialExpertState },

  orchestrator: {
    subtitle: '',
    content: '',
  },

  isPanelActive: false,
  setPanelActive: (v) => set({ isPanelActive: v }),

  isAnalyzing: false,
  setAnalyzing: (v) => set({ isAnalyzing: v }),

  resetAll: () =>
    set({
      phase: 'collapsed',
      experts: {
        tactics: { ...initialExpertState.tactics },
        strategy: { ...initialExpertState.strategy },
        engine: { ...initialExpertState.engine },
      },
      orchestrator: { subtitle: '', content: '' },
      isAnalyzing: false,
    }),

  updateExpert: (type, update) =>
    set((state) => ({
      experts: {
        ...state.experts,
        [type]: { ...state.experts[type], ...update },
      },
    })),

  appendExpertThinking: (type, chunk) =>
    set((state) => ({
      experts: {
        ...state.experts,
        [type]: {
          ...state.experts[type],
          thinkingContent:
            state.experts[type].thinkingContent + chunk,
        },
      },
    })),

  addExpertToolCall: (type, toolCall) =>
    set((state) => ({
      experts: {
        ...state.experts,
        [type]: {
          ...state.experts[type],
          toolCalls: [
            ...state.experts[type].toolCalls,
            toolCall,
          ],
        },
      },
    })),

  updateOrchestratorSubtitle: (subtitle) =>
    set((state) => ({
      orchestrator: { ...state.orchestrator, subtitle },
    })),

  appendOrchestratorContent: (chunk) =>
    set((state) => ({
      orchestrator: {
        ...state.orchestrator,
        content: state.orchestrator.content + chunk,
      },
    })),
}));
