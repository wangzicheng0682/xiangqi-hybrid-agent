# Checklist

## 标签定义验证

- [x] TagCategory.SEMANTIC 语义层分类已添加
- [x] 5个标准杀法标签已定义（checkmate_horse_corner, checkmate_bare_king, checkmate_double_cannon_battery, checkmate_sea_bottom_moon, checkmate_side_tiger）
- [x] 10个语义层标签已定义（phase_opening, phase_middlegame, phase_endgame, king_safety_critical, has_initiative, is_forcing_move, horse_leg_blocked, kings_face_to_face, cannon_battery, favorable_exchange）
- [x] 所有新标签已添加到 ALL_TACTICAL_TAGS 列表

## 标准杀法检测验证

- [x] 卧槽马检测：确认将死 + 马在宫外攻击将/帅
- [x] 白脸将检测：确认将死 + 双将同列无阻挡
- [x] 重炮杀检测：确认将死 + 炮A以炮B为炮架攻击将/帅
- [x] 海底捞月检测：确认将死 + 车在敌方底线攻击将/帅
- [x] 侧面虎检测：确认将死 + 车与将/帅同行横向攻击

## 语义层检测验证

- [x] 局面阶段检测：≥28开局、15-27中局、≤14残局
- [x] 将帅危急检测：安全分计算正确（防守子+2/个，逃跑格+1/格，威胁-2/个，被将军-4）
- [x] 主动权检测：强制手段统计正确
- [x] 强制手段检测（动态）：将军/吃无根子/将死判断正确
- [x] 马脚被别检测：四个马脚方向检查正确
- [x] 双将对面检测：同列无阻挡判断正确
- [x] 重炮阵型检测：同行/同列且无阻隔判断正确
- [x] 有利兑换检测：子力价值表正确，吃大子/吃无根子判断正确

## 辅助函数验证

- [x] _cannon_attacks_via_platform：三点共线 + 炮架在中间 + 恰好1个棋子
- [x] _count_king_defenders：统计保护将/帅的同色棋子数
- [x] _get_blocked_horse_legs：四个马脚方向阻塞信息
- [x] _count_forcing_potential：强制手段加权计数

## 检测器集成验证

- [x] detect_static 追加调用标准杀法检测
- [x] detect_static 追加调用语义层静态检测
- [x] detect_dynamic 追加调用强制手段检测

## Evidence Map 验证

- [x] 所有新增标签的 evidence_source 为 "RULES"
- [x] 标签→semantic_state 映射正确

## 测试验证

- [x] 所有现有单元测试通过
- [x] 无新增 lint 错误
- [x] 无新增类型检查错误
