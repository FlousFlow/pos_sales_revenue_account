# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_default_sales_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default Sales Revenue Account',
        related='company_id.pos_default_sales_revenue_account_id',
        readonly=False,
        check_company=True,
        domain="[('internal_group', '=', 'income')]",
    )

    pos_sales_revenue_account_id = fields.Many2one(
        'account.account',
        string='Sales Revenue Account',
        related='pos_config_id.sales_revenue_account_id',
        readonly=False,
        check_company=True,
        domain="[('internal_group', '=', 'income')]",
    )
