# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    sales_revenue_account_id = fields.Many2one(
        'account.account',
        string='Sales Revenue Account',
        check_company=True,
        domain="[('internal_group', '=', 'income')]",
        help=_("Revenue account used for product sales from this Point of Sale. "
               "Leave empty to use product/category income accounts."),
    )
