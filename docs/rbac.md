# RBAC conventions (SystemECOM)

## Roles

- **WAREHOUSE_ADMIN**: Full access within tenant.
- **WAREHOUSE_SUPERVISOR**: Operational access (warehouse workflows) within tenant.
- **WAREHOUSE_WORKER**: Scan-first workflows (receive/putaway/pick/pack/dispatch/returns/discrepancies) within tenant.
- **DRIVER**: Placeholder v1 role (courier/driver); treated as warehouse staff for now.
- **CLIENT_USER**: Read/write within their own `client_id` only (inventory, outbound/inbound requests, documents, invoices).

## Enforcement rules (hard requirements)

- **Backend is the source of truth**: tenant/client scoping is enforced in queries, never “UI-only”.
- **Tenant isolation**: every protected query is scoped to `user.tenant_id`.
- **Client isolation**: if `user.client_id != null`, queries are additionally scoped to that `client_id`.
- **Write endpoints**: require explicit role dependencies (e.g. `require_admin_or_supervisor`, `require_warehouse_staff`).


