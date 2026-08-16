# P8-008 未来商业关闭态与合同

日期：2026-08-14  
工作项：P8-008 订阅首期/充值资格的关闭态与未来合同测试  
状态：`IN_PROGRESS`

## 本轮确认

- `contracts/openapi/v1.yaml` 与 `contracts/openapi/admin-v1.yaml` 当前都没有 subscription、wallet、topup 或 recharge 路径。
- `web/src/app/pricing/page.tsx` 明确写出当前不开放自动续费、代币余额、充值钱包或永久无限 AI。
- 定价页明确按钮点击不会被写成已付款；本轮没有新增订阅、充值、余额或代币事实写入路径。
- Web 公共定价页保留真实 Offer 与一次性付款边界，不把关闭态伪装成可购买能力。

## 定向验证与完整回归

```text
uv run --directory backend pytest ../tests/contract/test_future_commerce_contract.py ../tests/contract/test_openapi_contract.py -q
11 passed

npm --prefix web test -- --run src/test/public-pages.test.tsx
10 passed

uv run --project backend ruff check --config backend/pyproject.toml tests/contract/test_future_commerce_contract.py
All checks passed

git diff --check && git diff --cached --check
passed
```

完整 `make check`：

```text
Backend: 729 passed, 92 skipped
Ruff: All checks passed
mypy: Success: no issues found in 132 source files
Web: 68 files, 431 tests
Admin: 33 files, 121 tests
Web/Admin lint、typecheck、production build: passed
治理合同：11 passed
```

## 边界

P8-008 当前只冻结未来商业能力的关闭态，避免后续代码误把按钮、文案或路径当成已付款、订阅或钱包余额。它不代表订阅、充值资格、支付渠道、账务账本、退款、生产密钥、通知或用户验收已经完成；这些能力必须在批准独立产品合同后再实现。
