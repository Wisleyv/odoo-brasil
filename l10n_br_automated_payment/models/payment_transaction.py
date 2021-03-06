# © 2019 Danimar Ribeiro
# Part of OdooNext. See LICENSE file for full copyright and licensing details.

import iugu
from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    transaction_url = fields.Char(string="Url de Pagamento", size=256) 
    origin_move_line_id = fields.Many2one('account.move.line')
    date_maturity = fields.Date(string="Data de Vencimento")

    def action_verify_transaction(self):
        if not self.acquirer_reference:
            raise UserError('Esta transação não foi enviada a nenhum gateway de pagamento')
        if self.acquirer_id.provider != 'iugu':
            return
        token = self.env.user.company_id.iugu_api_token
        iugu.config(token=token)
        iugu_invoice_api = iugu.Invoice()

        data = iugu_invoice_api.search(self.acquirer_reference)
        if "errors" in data:
            raise UserError(data['errors'])
        if data.get('status', '') == 'paid' and self.state not in ('done', 'authorized'):
            self._set_transaction_done()
            self._post_process_after_done()
            self.origin_move_line_id._create_bank_tax_move(data)
        else:
            self.iugu_status = data['status']

    def cancel_transaction_in_iugu(self):
        if not self.acquirer_reference:
            raise UserError('Esta parcela não foi enviada ao IUGU')
        token = self.env.user.company_id.iugu_api_token
        iugu.config(token=token)
        iugu_invoice_api = iugu.Invoice()
        iugu_invoice_api.cancel(self.acquirer_reference)

    def action_cancel_transaction(self):
        self._set_transaction_cancel()
        if self.acquirer_id.provider == 'iugu':
            self.cancel_transaction_in_iugu()