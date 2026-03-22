# Tasks

## 标签定义扩展

- [x] Task 1: 在 tactical_tags.py 中新增标签定义
  - [x] SubTask 1.1: 新增 TagCategory.SEMANTIC 语义层分类
  - [x] SubTask 1.2: 定义5个标准杀法标签（卧槽马、白脸将、重炮杀、海底捞月、侧面虎）
  - [x] SubTask 1.3: 定义10个语义层标签（阶段、将帅危急、主动权、强制手段、马脚被别、双将对面、重炮阵型、有利兑换）
  - [x] SubTask 1.4: 将新标签添加到 ALL_TACTICAL_TAGS 列表

## 第五层：标准杀法检测实现

- [x] Task 2: 实现卧槽马检测 (_detect_horse_corner)
  - [x] SubTask 2.1: 确认将死状态（被将军 + 无合法走法）
  - [x] SubTask 2.2: 找到攻击敌方将/帅的己方马
  - [x] SubTask 2.3: 验证马不在敌方九宫格内（卧槽位）
  - [x] SubTask 2.4: 绑定己方马和敌方将/帅

- [x] Task 3: 实现白脸将检测 (_detect_bare_king)
  - [x] SubTask 3.1: 确认将死状态
  - [x] SubTask 3.2: 找双方将/帅位置
  - [x] SubTask 3.3: 检查同列且无阻挡
  - [x] SubTask 3.4: 绑定双方将/帅

- [x] Task 4: 实现重炮杀检测 (_detect_double_cannon_battery_checkmate)
  - [x] SubTask 4.1: 确认将死状态
  - [x] SubTask 4.2: 找所有己方炮
  - [x] SubTask 4.3: 检查炮A以炮B为炮架攻击将/帅的配置
  - [x] SubTask 4.4: 绑定两门炮和敌方将/帅

- [x] Task 5: 实现海底捞月检测 (_detect_sea_bottom_moon)
  - [x] SubTask 5.1: 确认将死状态
  - [x] SubTask 5.2: 确定敌方底线行号
  - [x] SubTask 5.3: 找底线上攻击将/帅的己方车
  - [x] SubTask 5.4: 绑定己方车和敌方将/帅

- [x] Task 6: 实现侧面虎检测 (_detect_side_tiger)
  - [x] SubTask 6.1: 确认将死状态
  - [x] SubTask 6.2: 找将/帅所在行
  - [x] SubTask 6.3: 找同行的己方车并验证横向攻击
  - [x] SubTask 6.4: 绑定己方车和敌方将/帅

## 第七层：语义层检测实现

- [x] Task 7: 实现局面阶段检测 (_detect_phase)
  - [x] SubTask 7.1: 统计棋盘上棋子总数（分色统计）
  - [x] SubTask 7.2: 按阈值判断阶段（≥28开局、15-27中局、≤14残局）
  - [x] SubTask 7.3: 附带详细棋子清单到 metadata

- [x] Task 8: 实现将帅危急检测 (_detect_king_safety)
  - [x] SubTask 8.1: 对双方各自检测
  - [x] SubTask 8.2: 统计保护将/帅的同色棋子数
  - [x] SubTask 8.3: 统计将/帅的合法逃跑格数
  - [x] SubTask 8.4: 统计威胁将/帅相邻位置的敌方棋子数
  - [x] SubTask 8.5: 计算安全分，低于阈值触发标签

- [x] Task 9: 实现主动权检测 (_detect_initiative)
  - [x] SubTask 9.1: 统计己方强制手段数（将军、捉无根子）
  - [x] SubTask 9.2: 统计敌方强制手段数
  - [x] SubTask 9.3: 对比判断主动权归属

- [x] Task 10: 实现强制手段检测 (_detect_forcing_move)（动态）
  - [x] SubTask 10.1: 执行走法获取新局面
  - [x] SubTask 10.2: 检查是否形成将军
  - [x] SubTask 10.3: 检查是否捕获对方无根子
  - [x] SubTask 10.4: 检查是否直接将死

- [x] Task 11: 实现马脚被别检测 (_detect_horse_leg_blocked)
  - [x] SubTask 11.1: 遍历棋盘上所有马
  - [x] SubTask 11.2: 检查四个马脚位置是否被占据
  - [x] SubTask 11.3: 记录被阻塞的马脚数量和阻塞棋子

- [x] Task 12: 实现双将对面检测 (_detect_kings_face_to_face)
  - [x] SubTask 12.1: 找双方将/帅位置
  - [x] SubTask 12.2: 检查是否同列
  - [x] SubTask 12.3: 检查两将之间是否有阻挡

- [x] Task 13: 实现重炮阵型检测 (_detect_cannon_battery)
  - [x] SubTask 13.1: 找双方各自的所有炮
  - [x] SubTask 13.2: 检查同色炮两两组合是否同行/同列
  - [x] SubTask 13.3: 检查两炮之间是否无棋子

- [x] Task 14: 实现有利兑换检测 (_detect_favorable_exchange)
  - [x] SubTask 14.1: 定义子力价值表 PIECE_VALUES
  - [x] SubTask 14.2: 遍历己方棋子的攻击范围
  - [x] SubTask 14.3: 判断是否有利（吃大子 or 吃无根子）

## 辅助函数实现

- [x] Task 15: 实现辅助函数
  - [x] SubTask 15.1: _cannon_attacks_via_platform（验证炮通过炮架攻击目标）
  - [x] SubTask 15.2: _count_king_defenders（统计保护将/帅的同色棋子数）
  - [x] SubTask 15.3: _get_blocked_horse_legs（获取马的被别马脚信息）
  - [x] SubTask 15.4: _count_forcing_potential（统计一方强制手段潜力）

## 检测器集成

- [x] Task 16: 更新主检测入口函数
  - [x] SubTask 16.1: 在 detect_static 中追加调用标准杀法检测
  - [x] SubTask 16.2: 在 detect_static 中追加调用语义层静态检测
  - [x] SubTask 16.3: 在 detect_dynamic 中追加调用强制手段检测

## 验证

- [x] Task 17: 运行测试验证实现
  - [x] SubTask 17.1: 运行现有单元测试
  - [x] SubTask 17.2: 确保所有测试通过

# Task Dependencies

- Task 1 必须最先完成（标签定义）
- Task 2-6 可以并行执行（标准杀法检测）
- Task 7-14 可以并行执行（语义层检测）
- Task 15 可以与 Task 2-14 并行执行
- Task 16 必须在 Task 2-15 完成后执行
- Task 17 必须在所有实现任务完成后执行
