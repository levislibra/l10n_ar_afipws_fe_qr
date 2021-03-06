# -*- coding: utf-8 -*-
{
    'name': "QR en factura electronica Afip",

    'summary': """
        Agregamos QR a la factura electronica AFIP de ingenieria Adhoc.""",

    'description': """
        Agregamos QR a la factura electronica AFIP de ingenieria Adhoc.
    """,

    'author': "Librasoft",
    'website': "https://libra-soft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Localization/Argentina',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'l10n_ar_afipws_fe'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/extends_invoice.xml',
				'views/invoice_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}