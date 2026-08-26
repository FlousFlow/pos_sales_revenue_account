# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosSalesRevenueAccount(TestPoSCommon):
    """POS Sales Revenue Account (Odoo 18) — per-POS revenue account tests."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _unique_account_code(self):
        """Return an account code that does not collide with the chart of accounts."""
        n = 900000
        while self.env['account.account'].search_count([
                ('code', '=', str(n)),
                ('company_ids', 'in', [self.env.company.id]),
        ], limit=1):
            n += 1
        return str(n)

    def _create_account(self, name, account_type, **kwargs):
        return self.env['account.account'].create({
            'code': self._unique_account_code(),
            'name': name,
            'account_type': account_type,
            **kwargs,
        })

    def _create_income_account(self, code, name):
        # `code` is kept for readability; if it already exists in the chart of
        # accounts we fall back to a guaranteed-unique code.
        if self.env['account.account'].search_count([
                ('code', '=', code),
                ('company_ids', 'in', [self.env.company.id]),
        ], limit=1):
            code = self._unique_account_code()
        return self.env['account.account'].create({
            'code': code,
            'name': name,
            'account_type': 'income',
        })

    def _create_pos_config(self, name):
        """Create a standalone POS config with its own cash payment method
        (a cash journal cannot be shared between two POS configurations)."""
        seq = self.env['pos.payment.method'].search_count([])
        cash_journal = self.env['account.journal'].create({
            'name': 'Cash %s' % name,
            'type': 'cash',
            'code': 'PRA%03d' % seq,
            'company_id': self.env.company.id,
            'loss_account_id': self.company_data['default_account_expense'].id,
            'profit_account_id': self.company_data['default_account_revenue'].id,
        })
        cash_pm = self.env['pos.payment.method'].create({
            'name': 'Cash %s' % name,
            'journal_id': cash_journal.id,
            'receivable_account_id': self.pos_receivable_cash.id,
            'company_id': self.env.company.id,
        })
        return self.env['pos.config'].create({
            'name': name,
            'invoice_journal_id': self.invoice_journal.id,
            'available_pricelist_ids': self.currency_pricelist.ids,
            'pricelist_id': self.currency_pricelist.id,
            'payment_method_ids': [cash_pm.id],
        })

    def _prepare_session(self, config):
        config.open_ui()
        session = config.current_session_id
        session.set_opening_control(0, None)
        self.config = config
        self.pos_session = session
        self.currency = session.currency_id
        self.pricelist = config.pricelist_id
        return session

    def _close_session(self, session):
        cash_pm = session.payment_method_ids.filtered('is_cash_count')[:1]
        total_cash = sum(session.order_ids.payment_ids.filtered(
            lambda p: p.payment_method_id == cash_pm).mapped('amount'))
        session.post_closing_cash_details(total_cash)
        session.close_session_from_ui()
        self.assertEqual(session.state, 'closed')
        return session

    def _run_pos_sale(self, config, lines):
        session = self._prepare_session(config)
        order_data = self.create_ui_order_data(lines)
        self.env['pos.order'].sync_from_ui([order_data])
        return self._close_session(session)

    def _revenue_lines(self, session):
        return session.move_id.line_ids.filtered(
            lambda line: line.display_type == 'product')

    def _revenue_balance(self, session):
        return round(sum(line.balance for line in self._revenue_lines(session)), 2)

    # ------------------------------------------------------------------
    # Test 1 — a configured POS revenue account overrides the product
    #           income account
    # ------------------------------------------------------------------
    def test_custom_revenue_account_overrides_product_account(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        product = self.create_product(
            'Product Cairo', self.categ_basic, 100.0,
            sale_account=self.sales_account)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        self.assertTrue(all(line.account_id == custom for line in revenue_lines))
        # 100.0 revenue credit posted to the custom account
        self.assertAlmostEqual(self._revenue_balance(session), -100.0, places=2)
        # the move is balanced and posted
        self.assertEqual(session.move_id.state, 'posted')
        self.assertAlmostEqual(sum(session.move_id.line_ids.mapped('balance')), 0.0, places=2)

    # ------------------------------------------------------------------
    # Test 2 — empty POS revenue account preserves standard behavior
    # ------------------------------------------------------------------
    def test_empty_revenue_account_uses_product_income_account(self):
        product = self.create_product(
            'Product Standard', self.categ_basic, 100.0,
            sale_account=self.sales_account)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        self.assertTrue(all(line.account_id == self.sales_account for line in revenue_lines))

    # ------------------------------------------------------------------
    # Test 3 — two POS configurations use their own independent accounts
    # ------------------------------------------------------------------
    def test_two_pos_configs_use_own_accounts(self):
        custom_cairo = self._create_income_account('411001', 'POS Sales Cairo')
        custom_giza = self._create_income_account('411002', 'POS Sales Giza')
        self.basic_config.write({'sales_revenue_account_id': custom_cairo.id})
        giza = self._create_pos_config('POS Giza')
        giza.write({'sales_revenue_account_id': custom_giza.id})
        product = self.create_product(
            'Product Shared', self.categ_basic, 100.0,
            sale_account=self.sales_account)

        session_cairo = self._run_pos_sale(self.basic_config, [(product, 1)])
        session_giza = self._run_pos_sale(giza, [(product, 1)])

        self.assertTrue(all(
            line.account_id == custom_cairo for line in self._revenue_lines(session_cairo)))
        self.assertTrue(all(
            line.account_id == custom_giza for line in self._revenue_lines(session_giza)))

    # ------------------------------------------------------------------
    # Test 4 — refunds reverse revenue against the same custom account
    # ------------------------------------------------------------------
    def test_refund_reverses_on_custom_revenue_account(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        product = self.create_product(
            'Product Refund', self.categ_basic, 100.0,
            sale_account=self.sales_account)

        session = self._prepare_session(self.basic_config)
        # sale
        order_data = self.create_ui_order_data([(product, 1)])
        order = self.env['pos.order'].browse(
            self.env['pos.order'].sync_from_ui([order_data])['pos.order'][0]['id'])
        # refund
        refund = self.env['pos.order'].browse(order.refund()['res_id'])
        cash_pm = session.payment_method_ids.filtered('is_cash_count')[:1]
        self.env['pos.make.payment'].with_context(
            active_id=refund.id, active_ids=refund.ids).create({
                'amount': refund.amount_total,
                'payment_method_id': cash_pm.id,
            }).check()
        self._close_session(session)

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        # both the sale credit and the refund debit use the custom account
        self.assertTrue(all(line.account_id == custom for line in revenue_lines))
        # the sale and its refund net to zero on the custom account
        self.assertAlmostEqual(self._revenue_balance(session), 0.0, places=2)

    # ------------------------------------------------------------------
    # Test 5 — taxes keep standard accounts
    # ------------------------------------------------------------------
    def test_vat_account_unchanged(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        tax = self.taxes['tax7']  # 7% excluded
        product = self.create_product(
            'Product Taxed', self.categ_basic, 100.0,
            sale_account=self.sales_account, tax_ids=tax.ids)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(all(line.account_id == custom for line in revenue_lines))
        tax_lines = session.move_id.line_ids.filtered(
            lambda line: line.display_type == 'tax')
        self.assertTrue(tax_lines)
        self.assertTrue(all(line.account_id == self.tax_received_account for line in tax_lines))
        self.assertAlmostEqual(self._revenue_balance(session), -100.0, places=2)
        # output VAT is a liability -> credited (-7.0), standard tax account
        self.assertAlmostEqual(
            round(sum(line.balance for line in tax_lines), 2), -7.0, places=2)

    # ------------------------------------------------------------------
    # Test 6 — non-POS customer invoices keep the product income account
    # ------------------------------------------------------------------
    def test_non_pos_invoice_keeps_product_income_account(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        product_income = self._create_income_account('400010', 'Product Income')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        product = self.create_product(
            'Product Invoice', self.categ_basic, 100.0, sale_account=product_income)

        # POS sale -> custom account
        session = self._run_pos_sale(self.basic_config, [(product, 1)])
        self.assertTrue(all(
            line.account_id == custom for line in self._revenue_lines(session)))

        # Non-POS customer invoice -> product income account (module must not
        # affect the invoice flow)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        self.assertEqual(invoice.invoice_line_ids.account_id, product_income)

    # ------------------------------------------------------------------
    # Test 7 — product category income account fallback
    # ------------------------------------------------------------------
    def test_product_category_income_account_fallback(self):
        # product WITHOUT an explicit income account -> category income account
        product = self.create_product('Product Categ', self.categ_basic, 100.0)

        # empty POS revenue account -> category income account
        session = self._run_pos_sale(self.basic_config, [(product, 1)])
        self.assertTrue(all(
            line.account_id == self.sale_account for line in self._revenue_lines(session)))

        # POS revenue account set -> custom account
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        session2 = self._run_pos_sale(self.basic_config, [(product, 1)])
        self.assertTrue(all(
            line.account_id == custom for line in self._revenue_lines(session2)))

    # ------------------------------------------------------------------
    # Test 8 — a POS cannot use an income account of another company
    # ------------------------------------------------------------------
    def test_cannot_select_other_company_account(self):
        company_b = self.env['res.company'].create({'name': 'Company B'})
        account_b = self.env['account.account'].create({
            'code': self._unique_account_code(),
            'name': 'B Revenue',
            'account_type': 'income',
            'company_ids': [company_b.id],
        })
        # check_company=True enforces the company consistency on write
        with self.assertRaises(UserError):
            self.basic_config.write({'sales_revenue_account_id': account_b.id})
        # and the field is still empty (the write was rejected)
        self.assertFalse(self.basic_config.sales_revenue_account_id)

    # ------------------------------------------------------------------
    # Test 9 — only income accounts satisfy the field domain
    # ------------------------------------------------------------------
    def test_only_income_accounts_allowed_by_domain(self):
        income_acct = self._create_income_account('411001', 'POS Sales Cairo')
        expense_acct = self._create_account('Expense', 'expense')
        receivable_acct = self._create_account(
            'Receivable', 'asset_receivable', reconcile=True)
        bank_acct = self._create_account('Bank', 'asset_cash')

        # the field domain restricts the selector to Income / Revenue accounts
        allowed = self.env['account.account'].search([('internal_group', '=', 'income')])
        self.assertIn(income_acct, allowed)
        self.assertNotIn(expense_acct, allowed)
        self.assertNotIn(receivable_acct, allowed)
        self.assertNotIn(bank_acct, allowed)

    # ------------------------------------------------------------------
    # Test 10 — discounts keep standard pricing on the custom account
    # ------------------------------------------------------------------
    def test_discount_keeps_standard_pricing(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        # A tax is required here: Odoo's `create_ui_order_data` test helper
        # ignores the discount in its no-tax branch, which would create an
        # unbalanced closing move. With a tax, the helper computes the
        # discounted base correctly (and this also covers discount + VAT).
        tax = self.taxes['tax7']
        product = self.create_product(
            'Product Disc', self.categ_basic, 100.0,
            sale_account=self.sales_account, tax_ids=tax.ids)
        session = self._run_pos_sale(self.basic_config, [(product, 1, 10.0)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(all(line.account_id == custom for line in revenue_lines))
        # 100.0 - 10% = 90.0 net revenue credit on the custom account
        self.assertAlmostEqual(self._revenue_balance(session), -90.0, places=2)
        # the closing move remains balanced
        self.assertAlmostEqual(
            sum(session.move_id.line_ids.mapped('balance')), 0.0, places=2)

    # ------------------------------------------------------------------
    # Test 11 — multiple products with different income accounts all post
    #            to the custom POS revenue account
    # ------------------------------------------------------------------
    def test_multiple_products_all_on_custom_account(self):
        custom = self._create_income_account('411001', 'POS Sales Cairo')
        self.basic_config.write({'sales_revenue_account_id': custom.id})
        product_a = self.create_product(
            'Product A', self.categ_basic, 100.0,
            sale_account=self._create_income_account('400001', 'Income A'))
        product_b = self.create_product(
            'Product B', self.categ_basic, 200.0,
            sale_account=self._create_income_account('400002', 'Income B'))
        session = self._run_pos_sale(self.basic_config, [(product_a, 1), (product_b, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        self.assertTrue(all(line.account_id == custom for line in revenue_lines))
        self.assertAlmostEqual(self._revenue_balance(session), -300.0, places=2)

    # ------------------------------------------------------------------
    # Test 12 — company default (main Settings page) used when the POS has
    #            no specific account
    # ------------------------------------------------------------------
    def test_company_default_sales_revenue_account_used(self):
        default_acct = self._create_income_account('411099', 'Company POS Default')
        self.env.company.write({
            'pos_default_sales_revenue_account_id': default_acct.id,
        })
        product = self.create_product(
            'Product Default', self.categ_basic, 100.0,
            sale_account=self.sales_account)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        # the POS has no specific account -> company default is used
        self.assertTrue(all(line.account_id == default_acct for line in revenue_lines))
        self.assertAlmostEqual(self._revenue_balance(session), -100.0, places=2)

    # ------------------------------------------------------------------
    # Test 13 — the POS-specific account overrides the company default
    # ------------------------------------------------------------------
    def test_pos_specific_overrides_company_default(self):
        default_acct = self._create_income_account('411099', 'Company POS Default')
        specific_acct = self._create_income_account('411001', 'POS Sales Cairo')
        self.env.company.write({
            'pos_default_sales_revenue_account_id': default_acct.id,
        })
        self.basic_config.write({'sales_revenue_account_id': specific_acct.id})
        product = self.create_product(
            'Product Override', self.categ_basic, 100.0,
            sale_account=self.sales_account)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])

        revenue_lines = self._revenue_lines(session)
        self.assertTrue(revenue_lines)
        # the POS-specific account wins over the company default
        self.assertTrue(all(line.account_id == specific_acct for line in revenue_lines))
        self.assertAlmostEqual(self._revenue_balance(session), -100.0, places=2)

    # ------------------------------------------------------------------
    # Test 14 — the main Settings page field sets the selected POS's account
    # ------------------------------------------------------------------
    def test_settings_page_sets_pos_account(self):
        acct = self._create_income_account('411001', 'POS Sales Cairo')
        settings = self.env['res.config.settings'].create({
            'pos_config_id': self.basic_config.id,
        })
        settings.write({'pos_sales_revenue_account_id': acct.id})
        # the settings field is related to the selected pos.config
        self.assertEqual(self.basic_config.sales_revenue_account_id, acct)
        # and it is really used for the closing entry
        product = self.create_product(
            'Product From Settings', self.categ_basic, 100.0,
            sale_account=self.sales_account)
        session = self._run_pos_sale(self.basic_config, [(product, 1)])
        self.assertTrue(all(
            line.account_id == acct for line in self._revenue_lines(session)))
