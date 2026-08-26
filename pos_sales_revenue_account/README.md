# POS Sales Revenue Account (Odoo 18)

Let every **Point of Sale configuration** define its own optional **Sales Revenue Account**.

When set, all product sales revenue lines generated when closing that POS
session are posted to this account **instead of** the product /
product-category income account. POS refunds are reversed against the same
account. When the field is left empty, **standard Odoo behavior is preserved**
exactly.

## Configuration

1. Invoicing → Configuration → Charts of Accounts → create your revenue
   accounts (e.g. `411001 POS Sales Cairo`, `411002 POS Sales Giza`).
2. **Optional company default**: Settings → Point of Sale → *Default Sales
   Revenue Account* — used for any POS configuration that does not define its
   own account.
3. Point of Sale → Configuration → Point of Sale → open a POS → **Accounting**
   section → *Sales Revenue Account* (each POS can override the company
   default).
4. Save. From now on, every sale made at that POS posts its revenue to the
   selected account (POS-specific account first, then the company default,
   then the standard product/category income account).

## Behavior

| POS configuration         | Revenue posted to                                              |
|---------------------------|----------------------------------------------------------------|
| `411001` set (POS Cairo)  | `411001`                                                       |
| `411002` set (POS Giza)   | `411002`                                                       |
| empty, company default set| company default (from the main Settings page)                  |
| empty, no default         | standard product / product-category income account             |

* Refunds (full, partial, negative lines) reverse revenue against the same
  POS-specific account.
* Taxes, receivable/payment accounts, stock valuation, COGS, cash, bank,
  rounding and session-balance logic are untouched.
* Only valid **Income / Revenue accounts** (Income and Other Income types) of
  the **same company** can be selected (`check_company` is enforced
  server-side).
* No frontend change; the account is read at session-closing time, so a change
  affects future closings only (historical `account.move` records are never
  modified).

## Technical notes

* Field: `pos.config.sales_revenue_account_id` (`account.account`, optional) +
  company default `res.company.pos_default_sales_revenue_account_id` (editable
  from the main Settings page through `res.config.settings`).
* The revenue-account override happens in `pos.session._get_sale_vals()` — a
  minimal override that calls `super()` and replaces only `account_id` of the
  product sales/refund revenue lines.
* Priority: POS-specific account → company default → product/category income
  account.
* No new models, no new security groups, no `ir.config_parameter`, no direct
  SQL, no core modifications.

## Tests

```bash
# On an Odoo 18 instance (test database)
odoo-bin -d test --test-enable -u pos_sales_revenue_account --stop-after-init
```

The suite covers: custom-account override, empty-account fallback, two
independent POS configurations, refund reversal, VAT account preservation,
non-POS invoice behavior, product-category fallback, cross-company blocking,
income-only domain, discounts and multiple products.

## Compatibility

Verified against Odoo 19 (Community Edition). Depends on `point_of_sale` and
`account`.
