import { create } from 'zustand';
import { ExpertType, ExpertStatus, ToolCall, ExpertStep } from '../components/ExpertCard';

// ============================================
// Types
// ============================================

/**
 * Agent思考面板的动画阶段（Apple/WWDC 风格动画序列）
 * collapsed:   收起状态，三张扑克牌散开
 * idle:        分析未开始前的稳定状态
 * stacking:    叠卡阶段，三张牌向中心聚拢成叠
 * flipped:     翻面完成，叠卡整齐显露彩虹背面
 * morphing:    收缩变形，叠卡流畅收缩变形成小球
 * orbMoving:   球曲线滑动到右上角 + 逐张发牌（macOS拉伸感）
 * cardsLanded: 三张落地左侧整体垂直居中，球固定右上角
 * streaming:   协调者球呼吸 + 思维流输出
 */
export type AgentAnimationPhase =
  | 'collapsed'
  | 'idle'
  | 'stacking'
  | 'flipped'
  | 'morphing'
  | 'orbMoving'
  | 'cardsLanded'
  | 'streaming';

export interface ExpertAgentState {
  status: ExpertStatus;
  thinkingContent: string;
  toolCalls: ToolCall[];
  finding: string;
  subtitle: string; // 动态副标题
  steps: ExpertStep[];
}

export interface OrchestratorState {
  subtitle: string; // 协调者动态副标题
  content: string;  // 综合流式内容
  steps: ExpertStep[];
  subtitles: string[];
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

  // 步骤相关
  addExpertStep: (type: ExpertType, title: string, stepIndex: number) => void;
  appendExpertStepContent: (type: ExpertType, stepIndex: number, chunk: string) => void;
  finalizeExpertStep: (type: ExpertType, stepIndex: number, durationMs?: number) => void;

  // 更新协调者副标题
  updateOrchestratorSubtitle: (subtitle: string) => void;

  // 追加协调者内容
  appendOrchestratorContent: (chunk: string) => void;

  // 协调者步骤
  addOrchestratorStep: (title: string, stepIndex: number) => void;
  appendOrchestratorStepContent: (stepIndex: number, chunk: string) => void;
  finalizeOrchestratorStep: (stepIndex: number, durationMs?: number) => void;
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
    steps: [],
  },
  strategy: {
    status: 'idle',
    thinkingContent: '',
    toolCalls: [],
    finding: '',
    subtitle: '',
    steps: [],
  },
  engine: {
    status: 'idle',
    thinkingContent: '',
    toolCalls: [],
    finding: '',
    subtitle: '',
    steps: [],
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
    steps: [],
    subtitles: [],
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
      orchestrator: { subtitle: '', content: '', steps: [], subtitles: [] },
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

  addExpertStep: (type, title, stepIndex) =>
    set((state) => {
      const existing = state.experts[type].steps.find((step) => step.index === stepIndex);
      if (existing) {
        return state;
      }

      return {
        experts: {
          ...state.experts,
          [type]: {
            ...state.experts[type],
            subtitle: title,
            steps: [
              ...state.experts[type].steps,
              {
                index: stepIndex,
                title,
                content: '',
                status: 'thinking' as const,
              },
            ].sort((a, b) => a.index - b.index),
          },
        },
      };
    }),

  appendExpertStepContent: (type, stepIndex, chunk) =>
    set((state) => ({
      experts: {
        ...state.experts,
        [type]: {
          ...state.experts[type],
          steps: state.experts[type].steps.map((step) =>
            step.index === stepIndex
              ? { ...step, content: step.content + chunk }
              : step
          ),
        },
      },
    })),

  finalizeExpertStep: (type, stepIndex, durationMs) =>
    set((state) => ({
      experts: {
        ...state.experts,
        [type]: {
          ...state.experts[type],
          steps: state.experts[type].steps.map((step) =>
            step.index === stepIndex
              ? { ...step, status: 'completed', durationMs }
              : step
          ),
        },
      },
    })),

  updateOrchestratorSubtitle: (subtitle) =>
    set((state) => ({
      orchestrator: {
        ...state.orchestrator,
        subtitle,
        subtitles: subtitle && !state.orchestrator.subtitles.includes(subtitle)
          ? [...state.orchestrator.subtitles, subtitle]
          : state.orchestrator.subtitles,
      },
    })),

  appendOrchestratorContent: (chunk) =>
    set((state) => ({
      orchestrator: {
        ...state.orchestrator,
        content: state.orchestrator.content + chunk,
      },
    })),

  addOrchestratorStep: (title, stepIndex) =>
    set((state) => {
      const existing = state.orchestrator.steps.find((step) => step.index === stepIndex);
      if (existing) {
        return state;
      }

      return {
        orchestrator: {
          ...state.orchestrator,
          subtitle: title,
          steps: [
            ...state.orchestrator.steps,
            {
              index: stepIndex,
              title,
              content: '',
              status: 'thinking' as const,
            },
          ].sort((a, b) => a.index - b.index),
        },
      };
    }),

  appendOrchestratorStepContent: (stepIndex, chunk) =>
    set((state) => ({
      orchestrator: {
        ...state.orchestrator,
        steps: state.orchestrator.steps.map((step) =>
          step.index === stepIndex
            ? { ...step, content: step.content + chunk }
            : step
        ),
      },
    })),

  finalizeOrchestratorStep: (stepIndex, durationMs) =>
    set((state) => ({
      orchestrator: {
        ...state.orchestrator,
        steps: state.orchestrator.steps.map((step) =>
          step.index === stepIndex
            ? { ...step, status: 'completed', durationMs }
            : step
        ),
      },
    })),
}));
