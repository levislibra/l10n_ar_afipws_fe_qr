# -*- coding: utf-8 -*-

from openerp import models, fields, api
import json
import base64
import qrcode
from io import BytesIO
from PIL import Image
from datetime import datetime

class ExtendsAccountInvoice(models.Model):
	_inherit = "account.invoice"

	json_qr = fields.Char("JSON QR AFIP", compute='_compute_json_qr')
	texto_modificado_qr = fields.Char('Texto Modificado QR', compute='_compute_json_qr')
	qr = fields.Binary("QR", compute='_compute_qr')

	@api.one
	def _compute_json_qr(self):
		print("_compute_json_qr")
		if (self.type in ['out_invoice','out_refund'] and self.state in ['open','paid'] and self.afip_auth_code != False):
			dict_invoice = {
				"ver": 1,
				"fecha": self.date_invoice,
				"cuit": int(self.company_id.main_id_number),
				"ptoVta": self.journal_id.point_of_sale_number,
				"tipoCmp": int(self.journal_document_type_id.document_type_id.code),
				"nroCmp": self.invoice_number,
				"importe": self.amount_total,
				"moneda": str(self.currency_id.afip_code),
				"ctz": self.currency_id.rate,
				"tipoDocRec": int(self.partner_id.main_id_category_id.afip_code),
				"nroDocRec": int(self.partner_id.main_id_number),
				"tipoCodAut": 'E',
				"codAut": int(self.afip_auth_code),
			}
			# res = ','.join(['%s:%s' % (key,value) for (key, value) in dict_invoice.items()])
			res = str(dict_invoice).replace("\n", "")
			res = res.replace(" ", "")
		else:
			dict_invoice = 'ERROR'
			res = 'N/A'
		self.json_qr = res
		if type(dict_invoice) == dict:
			b64 = res.encode('base64','strict')
			# enc = res.encode()
			# b64 = base64.encodestring(enc)
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?p=' + str(b64)
		else:
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?ERROR'


	@api.one
	def _compute_qr(self):
		#Creating an instance of qrcode
		# VERSION 0
		img = qrcode.make(self.texto_modificado_qr)
		type(img)  # qrcode.image.pil.PilImage
		img.resize((128, 128), Image.NEAREST)
		buffered = BytesIO()
		img.save(buffered, format="PNG")
		img_str = base64.b64encode(buffered.getvalue())

		# VERSION 1
		# qr = qrcode.QRCode(
		# 	version=1,
		# 	box_size=10,
		# 	border=4)
		# qr.add_data(self.texto_modificado_qr)
		# qr.make(fit=True)
		# img = qr.make_image()
		# print("img:: ", img)
		# img = qrcode.make(self.texto_modificado_qr)

		# maxsize = (115, 115)
		# img.thumbnail(maxsize, Image.ANTIALIAS)

		# buffered = BytesIO()
		# img.save(buffered, format="JPEG")
		# img_str = base64.b64encode(buffered.getvalue())

		# VERSION 2
		# qr = qrcode.QRCode(
		# 	version=1,
		# 	error_correction=qrcode.constants.ERROR_CORRECT_H,
		# 	box_size=4,
		# 	border=4,
		# )

		# qr.add_data(self.texto_modificado_qr)
		# qr.make(fit=True)
		# img = qr.make_image()
		# print("img:: ", img)
		# img = img.resize((115, 115), Image.NEAREST)

		# buffered = BytesIO()
		# img.save(buffered, format="PNG")
		# print("img:: ", img)
		# img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
		self.qr = img_str
