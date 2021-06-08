# -*- coding: utf-8 -*-
from openerp import http

# class L10nArAfipwsFeQr(http.Controller):
#     @http.route('/l10n_ar_afipws_fe_qr/l10n_ar_afipws_fe_qr/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_ar_afipws_fe_qr/l10n_ar_afipws_fe_qr/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_ar_afipws_fe_qr.listing', {
#             'root': '/l10n_ar_afipws_fe_qr/l10n_ar_afipws_fe_qr',
#             'objects': http.request.env['l10n_ar_afipws_fe_qr.l10n_ar_afipws_fe_qr'].search([]),
#         })

#     @http.route('/l10n_ar_afipws_fe_qr/l10n_ar_afipws_fe_qr/objects/<model("l10n_ar_afipws_fe_qr.l10n_ar_afipws_fe_qr"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_ar_afipws_fe_qr.object', {
#             'object': obj
#         })