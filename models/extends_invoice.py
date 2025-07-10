# -*- coding: utf-8 -*-

from operator import inv
from openerp import models, fields, api, _
import json
import base64
import qrcode
from io import BytesIO
from PIL import Image
from datetime import datetime
# from .pyi25 import PyI25
from openerp.exceptions import UserError
from cStringIO import StringIO as StringIO
import logging
import sys
import traceback
_logger = logging.getLogger(__name__)

try:
    from pysimplesoap.client import SoapFault
except ImportError:
    _logger.debug('Can not `from pyafipws.soap import SoapFault`.')

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
		self.qr = img_str


	@api.multi
	def do_pyafipws_request_cae(self):
		_logger.info("*************************************")
		_logger.info("do_pyafipws_request_cae")
		_logger.info("*************************************")
		# "Request to AFIP the invoices' Authorization Electronic Code (CAE)"
		for inv in self:
			# Ignore invoices with cae (do not check date)
			if inv.afip_auth_code:
				continue

			if inv.journal_id.point_of_sale_type != 'electronic':
				continue
			afip_ws = inv.journal_id.afip_ws
			# Ignore invoice if not ws on point of sale
			if not afip_ws:
				raise UserError(_(
					'If you use electronic journals (invoice id %s) you need '
					'configure AFIP WS on the journal') % (inv.id))

			# get the electronic invoice type, point of sale and afip_ws:
			commercial_partner = inv.commercial_partner_id
			country = commercial_partner.country_id
			journal = inv.journal_id
			pos_number = journal.point_of_sale_number
			doc_afip_code = inv.document_type_id.code

			# authenticate against AFIP:
			ws = inv.company_id.get_connection(afip_ws).connect()

			if afip_ws == 'wsfex':
				if not country:
					raise UserError(_(
						'For WS "%s" country is required on partner' % (
							afip_ws)))
				elif not country.code:
					raise UserError(_(
						'For WS "%s" country code is mandatory'
						'Country: %s' % (
							afip_ws, country.name)))
				elif not country.afip_code:
					raise UserError(_(
						'For WS "%s" country afip code is mandatory'
						'Country: %s' % (
							afip_ws, country.name)))

			ws_next_invoice_number = int(
				inv.journal_document_type_id.get_pyafipws_last_invoice(
				)['result']) + 1
			# verify that the invoice is the next one to be registered in AFIP
			if inv.invoice_number != ws_next_invoice_number:
				raise UserError(_(
					'Error!'
					'Invoice id: %i'
					'Next invoice number should be %i and not %i' % (
						inv.id,
						ws_next_invoice_number,
						inv.invoice_number)))

			partner_id_code = commercial_partner.main_id_category_id.afip_code
			tipo_doc = partner_id_code or '99'
			nro_doc = partner_id_code and int(
				commercial_partner.main_id_number) or "0"
			cbt_desde = cbt_hasta = cbte_nro = inv.invoice_number
			concepto = tipo_expo = int(inv.afip_concept)

			fecha_cbte = inv.date_invoice
			if afip_ws != 'wsmtxca':
				fecha_cbte = fecha_cbte.replace("-", "")

			# due and billing dates only for concept "services"
			if int(concepto) != 1:
				fecha_venc_pago = inv.date_due or inv.date_invoice
				fecha_serv_desde = inv.afip_service_start
				fecha_serv_hasta = inv.afip_service_end
				if afip_ws != 'wsmtxca':
					fecha_venc_pago = fecha_venc_pago.replace("-", "")
					fecha_serv_desde = fecha_serv_desde.replace("-", "")
					fecha_serv_hasta = fecha_serv_hasta.replace("-", "")
			else:
				fecha_venc_pago = fecha_serv_desde = fecha_serv_hasta = None

			# # invoice amount totals:
			imp_total = str("%.2f" % inv.amount_total)
			# ImpTotConc es el iva no gravado
			imp_tot_conc = str("%.2f" % inv.vat_untaxed_base_amount)
			# tal vez haya una mejor forma, la idea es que para facturas c
			# no se pasa iva. Probamos hacer que vat_taxable_amount
			# incorpore a los imp cod 0, pero en ese caso termina reportando
			# iva y no lo queremos
			if inv.document_type_id.document_letter_id.name == 'C':
				imp_neto = str("%.2f" % inv.amount_untaxed)
			else:
				imp_neto = str("%.2f" % inv.vat_taxable_amount)
			imp_iva = str("%.2f" % inv.vat_amount)
			# se usaba para wsca..
			# imp_subtotal = str("%.2f" % inv.amount_untaxed)
			imp_trib = str("%.2f" % inv.other_taxes_amount)
			imp_op_ex = str("%.2f" % inv.vat_exempt_base_amount)
			moneda_id = inv.currency_id.afip_code
			moneda_ctz = inv.currency_rate
			# Agregar la condición frente al IVA del receptor
			receptor_condicion_iva = commercial_partner.afip_responsability_type_id.code

			# create the invoice internally in the helper
			if afip_ws == 'wsfe':
				ws.CrearFactura(
					concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
					cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
					imp_iva,
					imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
					fecha_serv_desde, fecha_serv_hasta,
					moneda_id, moneda_ctz, 
					condicion_iva_receptor_id=receptor_condicion_iva
				)
			# elif afip_ws == 'wsmtxca':
			#     obs_generales = inv.comment
			#     ws.CrearFactura(
			#         concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
			#         cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
			#         imp_subtotal,   # difference with wsfe
			#         imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
			#         fecha_serv_desde, fecha_serv_hasta,
			#         moneda_id, moneda_ctz,
			#         obs_generales   # difference with wsfe
			#     )
			elif afip_ws == 'wsfex':
				# # foreign trade data: export permit, country code, etc.:
				if inv.afip_incoterm_id:
					incoterms = inv.afip_incoterm_id.afip_code
					incoterms_ds = inv.afip_incoterm_id.name
					# máximo de 20 caracteres admite
					incoterms_ds = incoterms_ds and incoterms_ds[:20]
				else:
					incoterms = incoterms_ds = None
				# por lo que verificamos, se pide permiso existente solo
				# si es tipo expo 1 y es factura (codigo 19), para todo el
				# resto pasamos cadena vacia
				if int(doc_afip_code) == 19 and tipo_expo == 1:
					# TODO investigar si hay que pasar si ("S")
					permiso_existente = "N"
				else:
					permiso_existente = ""
				obs_generales = inv.comment

				if inv.payment_term_id:
					forma_pago = inv.payment_term_id.name
					obs_comerciales = inv.payment_term_id.name
				else:
					forma_pago = obs_comerciales = None

				idioma_cbte = 1     # invoice language: spanish / español

				# TODO tal vez podemos unificar este criterio con el del
				# citi que pide el cuit al partner
				# customer data (foreign trade):
				nombre_cliente = commercial_partner.name
				# If argentinian and cuit, then use cuit
				if country.code == 'AR' and tipo_doc == 80 and nro_doc:
					id_impositivo = nro_doc
					cuit_pais_cliente = None
				# If not argentinian and vat, use vat
				elif country.code != 'AR' and nro_doc:
					id_impositivo = nro_doc
					cuit_pais_cliente = None
				# else use cuit pais cliente
				else:
					id_impositivo = None
					if commercial_partner.is_company:
						cuit_pais_cliente = country.cuit_juridica
					else:
						cuit_pais_cliente = country.cuit_fisica
					if not cuit_pais_cliente:
						raise UserError(_(
							'No vat defined for the partner and also no CUIT '
							'set on country'))

				domicilio_cliente = " - ".join([
					commercial_partner.name or '',
					commercial_partner.street or '',
					commercial_partner.street2 or '',
					commercial_partner.zip or '',
					commercial_partner.city or '',
				])
				pais_dst_cmp = commercial_partner.country_id.afip_code
				ws.CrearFactura(
					doc_afip_code, pos_number, cbte_nro, fecha_cbte,
					imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
					nombre_cliente, cuit_pais_cliente, domicilio_cliente,
					id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
					obs_generales, forma_pago, incoterms,
					idioma_cbte, incoterms_ds
				)
			elif afip_ws == 'wsbfe':
				zona = 1  # Nacional (la unica devuelta por afip)
				# los responsables no inscriptos no se usan mas
				impto_liq_rni = 0.0
				imp_iibb = sum(inv.tax_line_ids.filtered(lambda r: (
					r.tax_id.tax_group_id.type == 'perception' and
					r.tax_id.tax_group_id.application == 'provincial_taxes')
				).mapped('amount'))
				imp_perc_mun = sum(inv.tax_line_ids.filtered(lambda r: (
					r.tax_id.tax_group_id.type == 'perception' and
					r.tax_id.tax_group_id.application == 'municipal_taxes')
				).mapped('amount'))
				imp_internos = sum(inv.tax_line_ids.filtered(
					lambda r: r.tax_id.tax_group_id.application == 'others'
				).mapped('amount'))
				imp_perc = sum(inv.tax_line_ids.filtered(lambda r: (
					r.tax_id.tax_group_id.type == 'perception' and
					# r.tax_id.tax_group_id.tax != 'vat' and
					r.tax_id.tax_group_id.application == 'national_taxes')
				).mapped('amount'))

				ws.CrearFactura(
					tipo_doc, nro_doc, zona, doc_afip_code, pos_number,
					cbte_nro, fecha_cbte, imp_total, imp_neto, imp_iva,
					imp_tot_conc, impto_liq_rni, imp_op_ex, imp_perc, imp_iibb,
					imp_perc_mun, imp_internos, moneda_id, moneda_ctz
				)

			# TODO ver si en realidad tenemos que usar un vat pero no lo
			# subimos
			if afip_ws not in ['wsfex', 'wsbfe']:
				for vat in inv.vat_taxable_ids:
					_logger.info(
						'Adding VAT %s' % vat.tax_id.tax_group_id.name)
					ws.AgregarIva(
						vat.tax_id.tax_group_id.afip_code,
						"%.2f" % vat.base,
						# "%.2f" % abs(vat.base_amount),
						"%.2f" % vat.amount,
					)

				for tax in inv.not_vat_tax_ids:
					_logger.info(
						'Adding TAX %s' % tax.tax_id.tax_group_id.name)
					ws.AgregarTributo(
						tax.tax_id.tax_group_id.application_code,
						tax.tax_id.tax_group_id.name,
						"%.2f" % tax.base,
						# "%.2f" % abs(tax.base_amount),
						# TODO pasar la alicuota
						# como no tenemos la alicuota pasamos cero, en v9
						# podremos pasar la alicuota
						0,
						"%.2f" % tax.amount,
					)

			CbteAsoc = inv.get_related_invoices_data()
			# bono no tiene implementado AgregarCmpAsoc
			if CbteAsoc and afip_ws != 'wsbfe':
				ws.AgregarCmpAsoc(
					CbteAsoc.document_type_id.code,
					CbteAsoc.point_of_sale_number,
					CbteAsoc.invoice_number,
				)

			# analize line items - invoice detail
			# wsfe do not require detail
			if afip_ws != 'wsfe':
				for line in inv.invoice_line_ids:
					codigo = line.product_id.default_code
					# unidad de referencia del producto si se comercializa
					# en una unidad distinta a la de consumo
					if not line.uom_id.afip_code:
						raise UserError(_(
							'Not afip code con producto UOM %s' % (
								line.uom_id.name)))
					# cod_mtx = line.uom_id.afip_code
					ds = line.name
					qty = line.quantity
					umed = line.uom_id.afip_code
					precio = line.price_unit
					importe = line.price_subtotal
					# calculamos bonificacion haciendo teorico menos importe
					bonif = line.discount and (precio * qty - importe) or None
					if afip_ws in ['wsmtxca', 'wsbfe']:
						if not line.product_id.uom_id.afip_code:
							raise UserError(_(
								'Not afip code con producto UOM %s' % (
									line.product_id.uom_id.name)))
						# u_mtx = (
						#     line.product_id.uom_id.afip_code or
						#     line.uom_id.afip_code)
						iva_id = line.vat_tax_id.tax_group_id.afip_code
						vat_taxes_amounts = line.vat_tax_id.compute_all(
							line.price_unit, inv.currency_id, line.quantity,
							product=line.product_id,
							partner=inv.partner_id)
						imp_iva = sum(
							[x['amount'] for x in vat_taxes_amounts['taxes']])
						if afip_ws == 'wsmtxca':
							raise UserError(
								_('WS wsmtxca Not implemented yet'))
							# ws.AgregarItem(
							#     u_mtx, cod_mtx, codigo, ds, qty, umed,
							#     precio, bonif, iva_id, imp_iva,
							#     importe + imp_iva)
						elif afip_ws == 'wsbfe':
							sec = ""  # Código de la Secretaría (TODO usar)
							ws.AgregarItem(
								codigo, sec, ds, qty, umed, precio, bonif,
								iva_id, importe + imp_iva)
					elif afip_ws == 'wsfex':
						ws.AgregarItem(
							codigo, ds, qty, umed, precio, importe,
							bonif)

			# Request the authorization! (call the AFIP webservice method)
			vto = None
			msg = False
			try:
				if afip_ws == 'wsfe':
					ws.CAESolicitar()
					vto = ws.Vencimiento
				elif afip_ws == 'wsmtxca':
					ws.AutorizarComprobante()
					vto = ws.Vencimiento
				elif afip_ws == 'wsfex':
					ws.Authorize(inv.id)
					vto = ws.FchVencCAE
				elif afip_ws == 'wsbfe':
					ws.Authorize(inv.id)
					vto = ws.Vencimiento
			except SoapFault as fault:
				msg = 'Falla SOAP %s: %s' % (
					fault.faultcode, fault.faultstring)
			except Exception as e:
				msg = e
			except Exception:
				if ws.Excepcion:
					# get the exception already parsed by the helper
					msg = ws.Excepcion
				else:
					# avoid encoding problem when raising error
					msg = traceback.format_exception_only(
						sys.exc_type,
						sys.exc_value)[0]
			if msg:
				raise UserError(_('AFIP Validation Error. %s' % msg))

			msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
			if not ws.CAE or ws.Resultado != 'A':
				raise UserError(_('AFIP Validation Error. %s' % msg))
			# TODO ver que algunso campos no tienen sentido porque solo se
			# escribe aca si no hay errores
			_logger.info('CAE solicitado con exito. CAE: %s. Resultado %s' % (
				ws.CAE, ws.Resultado))
			_logger.info("Condicion frente al IVA del receptor: %s" % (
				receptor_condicion_iva))
			inv.write({
				'afip_auth_mode': 'CAE',
				'afip_auth_code': ws.CAE,
				'afip_auth_code_due': vto,
				'afip_result': ws.Resultado,
				'afip_message': msg,
				'afip_xml_request': ws.XmlRequest,
				'afip_xml_response': ws.XmlResponse,
			})
			# si obtuvimos el cae hacemos el commit porque estoya no se puede
			# volver atras
			# otra alternativa seria escribir con otro cursor el cae y que
			# la factura no quede validada total si tiene cae no se vuelve a
			# solicitar. Lo mismo podriamos usar para grabar los mensajes de
			# afip de respuesta
			inv._cr.commit()