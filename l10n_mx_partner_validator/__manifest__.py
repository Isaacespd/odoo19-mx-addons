{
    'name': 'Validador de RFC y Listas Negras (EFOS)',
    'version': '19.0.1.1.1',
    'summary': 'Valida RFCs y detecta empresas EFOS (69-B SAT)',
    'category': 'Accounting/Localizations',
    'author': 'Isaac Espinosa',
    'website': 'https://isaacespd.github.io',
    'license': 'LGPL-3',
    'depends': ['contacts', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
    ],
}
