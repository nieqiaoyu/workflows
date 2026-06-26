# Agent Context - Requirement Before

来源：`docs/iterations/S1/00_initial/requirement.md`

## 订单展示

订单列表和订单详情页需要展示创建人信息。

### 字段说明

| 字段 | 展示名称 | 说明 |
| --- | --- | --- |
| `orderId` | 订单编号 | 订单唯一标识 |
| `orderStatus` | 订单状态 | 展示当前订单状态 |
| `createId` | 创建人 | 展示创建人账号 ID |
| `createTime` | 创建时间 | 展示订单创建时间 |

### 展示要求

- 订单列表展示 `createId`。
- 订单详情页展示 `createId`。
- 前端直接使用接口返回的 `createId` 字段。
