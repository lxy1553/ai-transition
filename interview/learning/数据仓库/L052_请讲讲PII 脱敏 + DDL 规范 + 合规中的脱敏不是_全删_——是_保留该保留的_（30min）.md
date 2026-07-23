---
id: L052
source: learning
category: 数据仓库
title: 请讲讲PII 脱敏 + DDL 规范 + 合规中的脱敏不是"全删"——是"保留该保留的"（30min）
generated: 2026-07-23T15:41:19.865105
---

# 请讲讲PII 脱敏 + DDL 规范 + 合规中的脱敏不是"全删"——是"保留该保留的"（30min）

> 来源: 学习复习计划 | 分类: 数据仓库

### 1.1 DataMasker 的四种策略

打开 `src/data/warehouse/dwd_layer.py` 第 48-78 行：


```python
class DataMasker:
    # 策略1: 掩码(Mask) — 保留部分结构，可做统计分析
    @staticmethod
    def mask_name(name):        # 黄敏 → 黄*
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_id_card(id_card):  # 934184...8691 → 934184********8691
        return id_card[:6] + "********" + id_card[-4:]

    @staticmethod
    def mask_phone(phone):      # 13872128795 → 138****8795
        return phone[:3] + "****" + phone[-4:]

    # 策略2: 哈希(Hash) — 不可逆但可去重
    @staticmethod
    def hash_user_id(user_id):  # user_000042 → a1b2c3d4e5f6...
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

```

**策略选择矩阵**：

| 策略 | 可逆性 | 可分析性 | 适用场景 |
|------|--------|---------|---------|
| Mask(掩码) | 部分可逆 | 高（保留结构） | 姓名、身份证、手机 |
| Hash(哈希) | 不可逆 | 仅可去重 | user_id、设备 ID |
| Generalize(泛化) | 不可逆 | 中（高维→低维） | IP→网段、年龄→年龄段 |
| Encrypt(加密) | 可逆（凭密钥） | 高 | 银行卡号（需结算时解密） |

### 1.2 为什么保留部分信息？


```
身份证: 934184********8691
  前6位 934184 = 地区码 → 可衍生"户籍省份"特征
  中间8位 = 出生日期 → 可衍生""年龄"特征
  后4位 = 校验码 → 可去重

全部哈希 → 丢失了地区和年龄两个有用特征
保留前6后4 → 既保护了隐私，又保留了分析价值

```

---