# -*- coding: utf-8 -*-

from openerp import models, fields, api
import json
import base64
import qrcode
from io import BytesIO
from PIL import Image

class ExtendsAccountInvoice(models.Model):
	_inherit = "account.invoice"

	json_qr = fields.Char("JSON QR AFIP", compute='_compute_json_qr')
	texto_modificado_qr = fields.Char('Texto Modificado QR', compute='_compute_json_qr')
	qr = fields.Binary("QR", compute='_compute_qr')

	@api.one
	def _compute_json_qr(self):
		if self.type in ['out_invoice','out_refund'] and self.state in ['open','paid'] and self.afip_auth_code != False:
			dict_invoice = {
				"ver": 1,
				"fecha": str(self.date_invoice),
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
			res = str(dict_invoice).replace("\n", "")
			res = res.replace(" ", "")
			print("RES:: ", res)
		else:
			dict_invoice = 'ERROR'
			res = 'N/A'
		self.json_qr = res
		if type(dict_invoice) == dict:
			print("res 2: ",res)
			enc = res.encode()
			b64 = base64.encodestring(enc)
			print("b64:: ", b64)
			b64 = b64.replace(' ', '')
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?p=' + str(b64)
		else:
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?ERROR'


	@api.one
	def _compute_qr(self):
		# Link for website
		# input_data = "https://towardsdatascience.com/face-detection-in-10-lines-for-beginners-1787aa1d9127"
		#Creating an instance of qrcode
		qr = qrcode.QRCode(
			version=10,
			box_size=2,
			border=1)
		qr.add_data(self.texto_modificado_qr)
		qr.make()
		img = qr.make_image()
		maxsize = (115, 115)
		img.thumbnail(maxsize, Image.ANTIALIAS)
		buffered = BytesIO()
		img.save(buffered, format="JPEG")
		img_str = base64.b64encode(buffered.getvalue())
		self.qr = img_str