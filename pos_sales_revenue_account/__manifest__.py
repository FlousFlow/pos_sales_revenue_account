{
    'name': 'POS Sales Revenue Account',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'sequence': 10,
    'summary': 'Assign each Point of Sale its own optional Sales Revenue Account.',
    'description': """
POS Sales Revenue Account
=========================

Let every Point of Sale configuration define its own *Sales Revenue Account*.

When a Point of Sale has a Sales Revenue Account set, all product sales revenue
lines generated when closing that POS session are posted to this account
instead of the product / product-category income account. POS refunds are
reversed against the same account.

When the field is left empty, standard Odoo behavior is preserved: the income
account is taken from the product, then from the product category, exactly as
in vanilla Odoo.

Key features
============

* **Per-POS revenue account** — each ``pos.config`` can optionally select its
  own income account (e.g. ``411001 POS Sales Cairo``, ``411002 POS Sales
  Giza``).
* **Company default** — an optional default account can be set from the main
  Settings page (Point of Sale settings); any Point of Sale without its own
  account uses it.
* **Per-POS from Settings** — manage each Point of Sale's account directly
  from the Settings page (same pattern as Odoo's Default Journals).
* **Income accounts only** — the selector is restricted to valid Income /
  Revenue accounts (``account.internal_group = 'income'``, i.e. the Income and
  Other Income account types) of the same company as the Point of Sale.
* **Refunds** — POS refunds reverse the revenue against the same
  POS-specific account (full, partial and negative-line refunds).
* **Fallback preserved** — with the field empty, product / product-category
  income accounts are used, exactly as in standard Odoo.
* **Surgical override** — only the *product sales revenue* move lines of the
  POS closing entry are affected. Tax accounts, receivable/payment accounts,
  stock valuation accounts, COGS, cash, bank, rounding and session balance
  logic are untouched.
* **No frontend change** — a backend-only accounting configuration.
* **Multi-company safe** — a Point of Sale can only use an income account of
  its own company; selecting another company's account is blocked.

Compatibility
=============

Verified against Odoo 19 (Community Edition).
""",
    'author': 'Flous Flow',
    'website': 'https://flousflow.com',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'account'],
    'data': [
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'images': [
        'static/description/thumbnail.png',
        'static/description/cover.png',
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
}
