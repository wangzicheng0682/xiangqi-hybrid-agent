# Tasks

## 严重错误修复

- [ ] Task 1: 修复E-02 双车错标签命名错误
  - [ ] SubTask 1.1: 在 `tactical_tags.py` 中将 `TAG_CHECKMATE_DOUBLE_CANNON` 重命名为 `TAG_CHECKMATE_DOUBLE_ROOK`
  - [ ] SubTask 1.2: 更新标签的 `name` 属性为 `checkmate_double_rook`
  - [ ] SubTask 1.3: 在 `tactical_detector.py` 中更新 `get_tag_by_name("checkmate_double_cannon")` 为 `get_tag_by_name("checkmate_double_rook")`
  - [ ] SubTask 1.4: 更新文档 `03.4_TACTICAL_DETECTOR_ALGORITHM.md` 中的标签名

- [ ] Task 2: 修复E-03 马后炮炮架检测逻辑
  - [ ] SubTask 2.1: 修改 `_detect_horse_back_cannon` 中的 `has_screen` 逻辑
  - [ ] SubTask 2.2: 将 `any(board[p[0]][p[1]] for p in line)` 改为 `len([p for p in line if board[p[0]][p[1]]]) == 1`
  - [ ] SubTask 2.3: 更新文档中的算法说明

- [ ] Task 3: 修复E-04 牵制检测规则区分
  - [ ] SubTask 3.1: 在 `_detect_pin_skewer` 中区分车牵制和炮牵制
  - [ ] SubTask 3.2: 车牵制：连线上只有1个己方棋子且无其他任何棋子
  - [ ] SubTask 3.3: 炮牵制：炮与将之间恰好有1个己方棋子
  - [ ] SubTask 3.4: 更新文档中的算法说明

- [ ] Task 4: 修复E-01 文档标签总数
  - [ ] SubTask 4.1: 更新文档 `03.4_TACTICAL_DETECTOR_ALGORITHM.md` 第11行，将"15个"改为"16个"

## 中等缺陷修复

- [ ] Task 5: 修复E-06 闪将检测归因精确性
  - [ ] SubTask 5.1: 在 `_detect_discovered_attack` 中添加精确归因逻辑
  - [ ] SubTask 5.2: 验证后方棋子的攻击范围是否包含敌方将/帅位置
  - [ ] SubTask 5.3: 更新文档中的算法说明

- [ ] Task 6: 修复E-07 炮串打穿透停止
  - [ ] SubTask 6.1: 在 `_find_cannon_double_targets` 中添加 `break` 语句
  - [ ] SubTask 6.2: 炮架后遇到任何棋子（敌方或己方）都应停止扫描
  - [ ] SubTask 6.3: 更新文档中的算法说明

- [ ] Task 7: 修复E-08 铁门栓将死验证
  - [ ] SubTask 7.1: 在 `_detect_iron_gate` 中添加将死验证
  - [ ] SubTask 7.2: 验证敌方被将军且无合法走法
  - [ ] SubTask 7.3: 更新文档中的算法说明

## 轻微问题修复

- [ ] Task 8: 修复E-09 抽将目标过滤
  - [ ] SubTask 8.1: 在 `_detect_double_attack_with_check` 中排除将/帅本身
  - [ ] SubTask 8.2: 更新文档中的算法说明

- [ ] Task 9: 修复E-10 注释步骤一致性
  - [ ] SubTask 9.1: 更新文档中攻无根的检测思路描述，补充第4步

## 标签定义修正

- [ ] Task 10: 修正炮有架标签定义
  - [ ] SubTask 10.1: 将 `cannon_has_platform` 的描述从"己方棋子"改为"任意棋子"

## 验证

- [ ] Task 11: 运行测试验证修复
  - [ ] SubTask 11.1: 运行现有单元测试
  - [ ] SubTask 11.2: 确保所有测试通过

# Task Dependencies

- Task 1 必须在 Task 2 之前完成（避免命名混淆）
- Task 2、Task 3、Task 5、Task 6、Task 7、Task 8 可以并行执行
- Task 4、Task 9、Task 10 可以并行执行
- Task 11 必须在所有修复任务完成后执行
