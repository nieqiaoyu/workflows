# Agent Context - Requirement After

来源：`docs/iterations/S1/v1/change.md`

## 订单展示

订单列表和订单详情页需要展示创建人信息。

### 字段说明

| 字段 | 展示名称 | 说明 |
| --- | --- | --- |
| `orderId` | 订单编号 | 订单唯一标识 |
| `orderStatus` | 订单状态 | 展示当前订单状态 |
| `createName` | 创建人 | 展示创建人姓名 |
| `createTime` | 创建时间 | 展示订单创建时间 |

### 展示要求

- 订单列表展示 `createName`。
- 订单详情页展示 `createName`。
- 前端使用接口返回的 `createName` 字段展示创建人姓名。
- 后端需要确认订单列表接口和订单详情接口返回 `createName`。
