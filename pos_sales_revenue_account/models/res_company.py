# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_default_sales_revenue_account_id = fields.Many2one(
        'account.account',
        string='Default Sales Revenue Account (PoS)',
        check_company=True,
        domain="[('internal_group', '=', 'income')]",
        help=_("Default revenue account used for product sales from Point of Sale "
               "configurations that do not define their own Sales Revenue Account. "
               "Leave empty to use product/category income accounts."),
    )

    @api.constrains('pos_default_sales_revenue_account_id')
    def _check_pos_default_sales_revenue_account_company(self):
        # res.company does not auto-run `_check_company`, so enforce the company
        # consistency explicitly (same semantics as account.account's
        # `_check_company_domain` = check_companies_domain_parent_of).
        for company in self:
            account = company.pos_default_sales_revenue_account_id
            if account and not account.filtered_domain(
                    [('company_ids', 'parent_of', company.id)]):
                raise ValidationError(_(
                    "The Default Sales Revenue Account (%(account)s) of the company "
                    "'%(company)s' must belong to that company.",
                    account=account.display_name,
                    company=company.display_name,
                ))
