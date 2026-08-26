# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_sale_vals(self, key, sale_vals):
        """Override the POS product sales revenue account.

        Priority when the POS closing entry is generated:
        1. ``pos.config.sales_revenue_account_id`` (POS-specific account)
        2. ``res.company.pos_default_sales_revenue_account_id`` (company default
           configured from the main Settings page)
        3. standard Odoo product / product-category income account.

        Only ``account_id`` is replaced; every other value returned by the
        standard method (amounts, taxes, tags, quantity, analytic fields added
        by other modules, ...) is preserved, so the move stays balanced and
        tax/payment/stock logic is untouched.
        """
        vals = super()._get_sale_vals(key, sale_vals)
        revenue_account = (
            self.config_id.sales_revenue_account_id
            or self.company_id.pos_default_sales_revenue_account_id
        )
        if revenue_account:
            vals['account_id'] = revenue_account.id
        return vals
