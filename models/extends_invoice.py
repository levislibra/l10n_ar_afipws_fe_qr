# -*- coding: utf-8 -*-

from openerp import models, fields, api
import json
import base64

class ExtendsAccountInvoice(models.Model):
	_inherit = "account.invoice"

	json_qr = fields.Char("JSON QR AFIP", compute='_compute_json_qr')
	texto_modificado_qr = fields.Char('Texto Modificado QR', compute='_compute_json_qr')

	@api.one
	def _compute_json_qr(self):
		# print("number: ", self.number)
		print("invoice_number: ", self.invoice_number)
		# print("number.split: ", self.number.split('-'))
		if self.type in ['out_invoice','out_refund'] and self.state in ['open','paid'] and self.afip_auth_code != False:
			# try:
			# tipoCmp = 0
			# if len(self.journal_document_type_id) > 0:
			# 	tipoCmp = int(self.journal_document_type_id.document_type_id.code)
			# nroCmp = 0
			# number = self.number.split('-')
			# if len(number) >= 2:
			# 	nroCmp = int(number[2])
			
			dict_invoice = {
				"ver": 1,
				"fecha": str(self.date_invoice),
				"cuit": int(self.company_id.main_id_number),
				"ptoVta": self.journal_id.point_of_sale_number,
				"tipoCmp": int(self.journal_document_type_id.document_type_id.code),
				"nroCmp": self.invoice_number,
				"importe": self.amount_total,
				"moneda": self.currency_id.afip_code,
				"ctz": self.currency_id.rate,
				"tipoDocRec": int(self.partner_id.main_id_category_id.afip_code),
				"nroDocRec": int(self.partner_id.main_id_number),
				"tipoCodAut": 'E',
				"codAut": self.afip_auth_code,
			}
			print("DICT_INVOICE:: ", dict_invoice)
			# except:
				# dict_invoice = 'ERROR'
				# pass
			res = str(dict_invoice).replace("\n", "")
		else:
			dict_invoice = 'ERROR'
			res = 'N/A'
		self.json_qr = res
		if type(dict_invoice) == dict:
			enc = res.encode()
			b64 = base64.encodestring(enc)
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?p=' + str(b64)
		else:
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?ERROR'
		print("texto_modificado_qr:: ", self.texto_modificado_qr)