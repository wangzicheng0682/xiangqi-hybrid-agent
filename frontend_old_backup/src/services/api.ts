import axios from 'axios';

// 统一使用 127.0.0.1，避免 localhost DNS 解析延迟
// 同时确保所有请求使用同一个 origin，避免浏览器连接数限制
const API_BASE = 'http://127.0.0.1:8003/api';

export interface AnalyzeResponse {
  fen: string;
  explanation: string;
  engine_result: {
    bestmove: string;
    score: number;
    depth: number;
    pv: string[];
  } | null;
  kg_result: {
    opening_name: string;
    win_rate: number;
    total_games: number;
    statistics: string;
  } | null;
  rag_results: Array<{
    book_name: string;
    content: string;
    relevance: number;
  }>;
  vision_result: {
    description: string;
    confidence: number;
  } | null;
  error: string;
}

export interface MoveResponse {
  board: string[][];
  fen: string;
  legal_moves: string[];
  captured: string;
  in_check: boolean;
  game_over: boolean;
}

export interface LegalMovesResponse {
  moves: string[];
  in_check: boolean;
}

export interface AIMoveResponse {
  move: string;
  from_row: number;
  from_col: number;
  to_row: number;
  to_col: number;
  board: string[][];
  fen: string;
  score: number;
  explanation: string;
}

export interface BestMovesResponse {
  red_best_move: string;
  red_best_from_row: number;
  red_best_from_col: number;
  red_best_to_row: number;
  red_best_to_col: number;
  red_score?: number;
  black_best_move: string;
  black_best_from_row: number;
  black_best_from_col: number;
  black_best_to_row: number;
  black_best_to_col: number;
  black_score?: number;
  current_turn: string;
}

export interface PGNGameInfo {
  game_index: number;
  event: string;
  red_player: string;
  black_player: string;
  result: string;
  date: string;
  moves: string[];
}

export interface PGNLoadResponse {
  games: PGNGameInfo[];
  total_games: number;
}

export interface PGNNavigateResponse {
  board: string[][];
  fen: string;
  current_index: number;
  total_moves: number;
  move_text: string;
}

export interface PositionAnalysisResponse {
  analysis_structured: {
    board_fen: string;
    turn: string;
    pieces: Array<{
      piece_id: string;
      side: string;
      piece_type: string;
      position: string;
      legal_moves: string[];
      attacks: string[];
      mobility: number;
      constraints: Array<{ type: string; by?: string; at?: string }>;
      geometric_tags: string[];
      positional_tags: string[];
      tactical_patterns: string[];
    }>;
    global_patterns: {
      red_in_check: boolean;
      black_in_check: boolean;
      duijiang: boolean;
      check_threats: string[];
    };
    pressure_map: Record<string, string[]>;
    retrieval_info: {
      phase: string;
      material_balance: number;
      active_side: string;
    };
    summary: string;
  };
  analysis_text: {
    analysis_text: string;
    retrieval_tags: string[];
    retrieval_hints: string[];
  };
}

export interface TacticalTag {
  name: string;
  category: string;
  description: string;
  confidence: number;
  bind_pieces: string[];
  metadata: Record<string, any>;
}

export interface TacticalTagsResponse {
  fen: string;
  tags: TacticalTag[];
  tags_by_category: Record<string, TacticalTag[]>;
}

export interface GameSearchResult {
  game_id: number;
  red: string;
  black: string;
  event: string;
  date: string;
  result: string;
}

export interface GameSearchResponse {
  games: GameSearchResult[];
  total: number;
}

export interface GameDetailResponse {
  game_id: number;
  red: string;
  black: string;
  event: string;
  date: string;
  result: string;
  moves: string[];
}

export const api = {
  // 用于管理 EventSource 连接，防止连接泄漏
  _activeEventSource: null as EventSource | null,

  getPositionAnalysis: async (fen: string): Promise<PositionAnalysisResponse> => {
    const response = await axios.post(`${API_BASE}/position-analysis`, { fen });
    return response.data;
  },

  analyzePosition: async (fen: string, board: string[][]): Promise<AnalyzeResponse> => {
    const response = await axios.post(`${API_BASE}/analyze`, {
      fen,
      board,
      use_vision: true
    });
    return response.data;
  },

  getLegalMoves: async (data: { board: string[][]; row: number; col: number }): Promise<LegalMovesResponse> => {
    const response = await axios.post(`${API_BASE}/legal-moves`, data);
    return response.data;
  },

  makeMove: async (data: {
    board: string[][];
    from_row: number;
    from_col: number;
    to_row: number;
    to_col: number;
    red_to_move: boolean;
  }): Promise<MoveResponse> => {
    const response = await axios.post(`${API_BASE}/move`, data);
    return response.data;
  },

  aiMove: async (data: {
    board: string[][];
    red_to_move: boolean;
    difficulty: number;
  }): Promise<AIMoveResponse> => {
    const response = await axios.post(`${API_BASE}/ai-move`, data);
    return response.data;
  },


  generateReview: async (data: {
    red_player: string;
    black_player: string;
    result: string;
    moves: string[];
  }): Promise<any> => {
    const response = await axios.post(`${API_BASE}/review`, data);
    return response.data;
  },

  getBestMoves: async (data: {
    board: string[][];
    red_to_move: boolean;
    difficulty: number;
  }): Promise<BestMovesResponse> => {
    const response = await axios.post(`${API_BASE}/best-moves`, data);
    return response.data;
  },

  pgnLoad: async (pgn_content: string): Promise<PGNLoadResponse> => {
    const response = await axios.post(`${API_BASE}/pgn-load`, { pgn_content });
    return response.data;
  },

  pgnNavigate: async (data: {
    moves: string[];
    current_index: number;
    direction: string;
  }): Promise<PGNNavigateResponse> => {
    const response = await axios.post(`${API_BASE}/pgn-navigate`, data);
    return response.data;
  },

  getTacticalTags: async (fen: string): Promise<TacticalTagsResponse> => {
    const response = await axios.post(`${API_BASE}/tactical-tags`, { fen });
    return response.data;
  },

  searchGames: async (params: { player?: string; event?: string; limit?: number }): Promise<GameSearchResponse> => {
    const response = await axios.post(`${API_BASE}/games/search`, params);
    return response.data;
  },

  getGameDetail: async (gameId: number): Promise<GameDetailResponse> => {
    const response = await axios.get(`${API_BASE}/games/${gameId}`);
    return response.data;
  },

  // 深度分析 - 使用 EventSource API (原生 SSE 支持)
  // 添加连接管理，防止连接泄漏
  analyzeDeep: async (
    data: { fen: string; move?: string; show_thinking?: boolean; question?: string },
    onThinking: (msg: { type: string; stage?: number; message?: string; tool?: string; finding?: string }) => void,
    onResult: (result: { explanation: string; confidence: string }) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    return new Promise((resolve) => {
      console.log('[API] 创建 EventSource', performance.now());

      // 关闭之前的连接，防止连接泄漏
      if (api._activeEventSource) {
        console.log('[API] 关闭之前的 EventSource 连接');
        api._activeEventSource.close();
        api._activeEventSource = null;
      }

      // 构建参数
      const params = new URLSearchParams({
        fen: data.fen,
        question: data.question || '请分析当前局面',
        show_thinking: String(data.show_thinking ?? true)
      });
      if (data.move) {
        params.append('move', data.move);
      }

      // 使用与 API_BASE 相同的 origin
      const fullUrl = `${API_BASE}/analyze/deep-stream?${params.toString()}`;
      console.log('[API] EventSource URL:', fullUrl.substring(0, 100) + '...');
      console.log('[API] API_BASE:', API_BASE);

      const eventSource = new EventSource(fullUrl);
      api._activeEventSource = eventSource;
      let firstMessage = true;
      let resolved = false;

      eventSource.onopen = () => {
        console.log('[API] EventSource 连接已建立', performance.now());
      };

      eventSource.onmessage = (event) => {
        if (firstMessage) {
          console.log('[API] 收到第一条消息', performance.now());
          firstMessage = false;
        }

        try {
          const json = JSON.parse(event.data);
          // 单Agent事件
          if (json.type === 'thinking' || json.type === 'thinking_chunk' ||
              json.type === 'tool_call' || json.type === 'tool_result') {
            onThinking(json);
          }
          // 多Agent事件 - 专家开始/完成
          else if (json.type === 'expert_start' || json.type === 'expert_result') {
            onThinking(json);
          }
          // 多Agent事件 - 专家思考过程（带专家名前缀）
          else if (json.type?.startsWith('expert_')) {
            onThinking(json);
          }
          // 合成器流式输出
          else if (json.type === 'synthesis_chunk') {
            onThinking({ type: 'thinking_chunk', message: json.message });
          }
          else if (json.type === 'result') {
            if (json.explanation) {
              onResult(json);
            }
            eventSource.close();
            api._activeEventSource = null;
            resolved = true;
            resolve();
          } else if (json.type === 'error') {
            onError(json.message);
            eventSource.close();
            api._activeEventSource = null;
            resolved = true;
            resolve();
          }
        } catch (e) {
          // 忽略解析错误
        }
      };

      eventSource.onerror = (error) => {
        console.error('[API] EventSource 错误', error);
        if (!resolved) {
          onError('连接错误');
          resolved = true;
          resolve();
        }
        eventSource.close();
        api._activeEventSource = null;
      };
    });
  }
};
