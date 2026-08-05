# payment-demo 项目导航（ZHIDAO）

> 本文件由 code-comment-expert 生成，是项目的"地图"。阅读顺序：先看本文，再按「推荐阅读路径」浏览代码。
> 生成时间：2026-08-05 ｜ 扫描范围：tests/fixtures/sample-java ｜ 源码文件数：3（另跳过 1 个测试文件）

## 1. 技术栈识别

| 维度 | 识别结果 |
|---|---|
| 主导语言 | Java |
| 构建/包管理 | Maven（pom.xml） |
| 核心框架 | Spring（@Service / @RestController / @Transactional） |
| 关键依赖 | Spring Web、Spring TX、JUnit 5 |
| 运行入口 | PaymentController（/api/pay/*） |

## 2. 目录树（简化）

```
sample-java
└── src
    ├── main/java/com/demo/payment/   # 支付域：Controller + Service + Mapper
    │   ├── PaymentController.java    # REST 入口
    │   ├── PaymentService.java       # 支付编排核心
    │   └── PaymentMapper.java        # 数据访问（示例存根）
    └── test/java/...                  # 测试（本 Skill 跳过，不加注释）
```

## 3. 模块职责

| 模块/目录 | 职责 | 关键类 | 备注 |
|---|---|---|---|
| payment/ | 支付流程编排与幂等控制 | PaymentService | 核心业务 |
| （同包） | REST 接口层 | PaymentController | 薄入口，无逻辑 |
| （同包） | 数据访问层 | PaymentMapper | 示例存根 |

## 4. 依赖流向

```
HTTP 请求 → PaymentController → PaymentService → PaymentMapper（DB）
                                    └─→ PaypalGateway / OrderService（外部依赖，未在本仓库）
```

- **被依赖最多**（底层基石）：PaymentMapper —— 数据访问，改动影响面大
- **依赖最多**（编排中枢）：PaymentService —— 阅读入口优先

## 5. 推荐阅读路径

**快速上手（3 个文件读透主流程）**：
1. `PaymentController.java` —— 看请求如何进入系统
2. `PaymentService.java` —— 看支付编排逻辑（幂等闸门 + 锁单 + 网关扣款）
3. `PaymentMapper.java` —— 看数据访问

**精读顺序**：Mapper（认识数据模型）→ Service（业务编排）→ Controller（入口组装）。

**跳读指引**：`PaymentServiceTest` 帮助理解预期行为（测试目录由 Skill 自动跳过，不添加注释）。

---

## 附：后续维护

- 模块职责变更时更新本文件（可用 `detect_changes.py` 辅助定位受影响模块）。
