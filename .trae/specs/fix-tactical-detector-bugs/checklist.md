# Checklist

## 严重错误修复验证

- [ ] E-02: 双车错标签名已从 `checkmate_double_cannon` 改为 `checkmate_double_rook`
- [ ] E-02: `tactical_tags.py` 中 `TAG_CHECKMATE_DOUBLE_ROOK` 定义正确
- [ ] E-02: `tactical_detector.py` 中 `get_tag_by_name("checkmate_double_rook")` 调用正确
- [ ] E-03: 马后炮炮架检测使用 `len(...) == 1` 而非 `any(...)`
- [ ] E-04: 牵制检测区分车牵制和炮牵制的不同规则
- [ ] E-04: 车牵制：连线上只有1个己方棋子且无其他任何棋子
- [ ] E-04: 炮牵制：炮与将之间恰好有1个己方棋子作为炮架
- [ ] E-01: 文档标签总数已从15改为16

## 中等缺陷修复验证

- [ ] E-06: 闪将检测精确绑定造成将军的后方棋子
- [ ] E-06: 验证后方棋子攻击范围是否包含敌方将/帅位置
- [ ] E-07: 炮串打在炮架后遇到任何棋子都停止扫描
- [ ] E-08: 铁门栓检测验证敌方被将军且无合法走法

## 轻微问题修复验证

- [ ] E-09: 抽将目标列表排除敌方将/帅本身
- [ ] E-10: 攻无根检测思路描述与代码注释步骤一致

## 标签定义修正验证

- [ ] `cannon_has_platform` 描述已从"己方棋子"改为"任意棋子"

## 文档更新验证

- [ ] `03.4_TACTICAL_DETECTOR_ALGORITHM.md` 中所有相关算法说明已更新
- [ ] 文档中的标签名 `checkmate_double_cannon` 已全部改为 `checkmate_double_rook`

## 测试验证

- [ ] 所有现有单元测试通过
- [ ] 无新增 lint 错误
- [ ] 无新增类型检查错误
