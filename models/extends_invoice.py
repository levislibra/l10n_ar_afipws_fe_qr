# -*- coding: utf-8 -*-

from openerp import models, fields, api
import json
import base64
import qrcode
from io import BytesIO
from PIL import Image
from collections import OrderedDict
from datetime import datetime

class ExtendsAccountInvoice(models.Model):
	_inherit = "account.invoice"

	json_qr = fields.Char("JSON QR AFIP", compute='_compute_json_qr')
	texto_modificado_qr = fields.Char('Texto Modificado QR', compute='_compute_json_qr')
	qr = fields.Binary("QR", compute='_compute_qr')

	@api.one
	def _compute_json_qr(self):
		print("_compute_json_qr")
		if True or (self.type in ['out_invoice','out_refund'] and self.state in ['open','paid'] and self.afip_auth_code != False):
			# dict_invoice = OrderedDict()
			# dict_invoice["ver"] = 1
			# dict_invoice["fecha"]= str(self.date_invoice)
			# dict_invoice["cuit"] = int(self.company_id.main_id_number)
			# dict_invoice["ptoVta"] = self.journal_id.point_of_sale_number
			# dict_invoice["tipoCmp"] = int(self.journal_document_type_id.document_type_id.code)
			# dict_invoice["nroCmp"] = self.invoice_number
			# dict_invoice["importe"] = self.amount_total
			# dict_invoice["moneda"] = str(self.currency_id.afip_code)
			# dict_invoice["ctz"] = self.currency_id.rate
			# dict_invoice["tipoDocRec"] = int(self.partner_id.main_id_category_id.afip_code)
			# dict_invoice["nroDocRec"] = int(self.partner_id.main_id_number)
			# dict_invoice["tipoCodAut"] = 'E'
			# dict_invoice["codAut"] = int(self.afip_auth_code)
			fecha = datetime.strptime(self.date_invoice, "%Y-%m-%d")
			fecha = fecha.year+'-'+fecha.month+'-'+fecha.day
			print("puta fecha: ", fecha)
			print("fecha.date: ", fecha.date)
			dict_invoice = """{
				"ver": 1,
				"fecha": "%s",
				"cuit": %s,
				"ptoVta": %s,
				"tipoCmp": %s,
				"nroCmp": %s,
				"importe": %s,
				"moneda": "%s",
				"ctz": %s,
				"tipoDocRec": %s,
				"nroDocRec": %s,
				"tipoCodAut": "E",
				"codAut": %s
			}"""%(str(fecha), str(self.company_id.main_id_number),self.journal_id.point_of_sale_number,str(self.journal_document_type_id.document_type_id.code), str(self.invoice_number), str(self.amount_total), str(self.currency_id.afip_code), str(self.currency_id.rate), str(self.partner_id.main_id_category_id.afip_code), str(self.partner_id.main_id_number),str(self.afip_auth_code))
			res = str(dict_invoice).replace("\n", "").replace("\t", "").replace(" ", "")
			print("RES:: ", res)
		else:
			dict_invoice = 'ERROR'
			res = 'N/A'
		self.json_qr = res
		if type(dict_invoice) == dict:
			print("res 2: ",res)
			b64 = res.encode('base64','strict')
			# enc = res.encode()
			# b64 = base64.encodestring(enc)
			print("b64:: ", b64)
			b64 = b64.replace('\n', '')
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?p=' + str(b64)
		else:
			self.texto_modificado_qr = 'https://www.afip.gob.ar/fe/qr/?ERROR'


	@api.one
	def _compute_qr(self):
		# Link for website
		# input_data = "https://towardsdatascience.com/face-detection-in-10-lines-for-beginners-1787aa1d9127"
		#Creating an instance of qrcode
		# qr = qrcode.QRCode(
		# 	version=1,
		# 	box_size=10,
		# 	border=1)
		# qr.add_data(self.texto_modificado_qr)
		# qr.make(self.texto_modificado_qr)
		# img = qr.make_image()

		img = qrcode.make(self.texto_modificado_qr)

		maxsize = (150, 150)
		img.thumbnail(maxsize, Image.ANTIALIAS)

		buffered = BytesIO()
		img.save(buffered, format="JPEG")
		img_str = base64.b64encode(buffered.getvalue())
		self.qr = img_str