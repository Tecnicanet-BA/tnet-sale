# -*- coding: utf-8 -*-

{
    'name': "Tecnicanet Sale Renting Price Update",
    'version': '15.0.0',
    'description': """Massive Update Rental Prices""",
    'summary': "Massive Update Rental Prices",
    'author': 'Luis Trajtenberg',
    'website': 'https://www.tecnicanet.com',
    'category': 'Sales/Sales',
    'sequence': 160,
    'depends': ['sale_renting'],
    'data': [
        "security/security.xml",
        "security/ir.model.access.csv",
        "wizard/sale_renting_price_update_views.xml",
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
