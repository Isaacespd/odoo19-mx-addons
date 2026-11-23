{
    'name': 'Control de Márgenes y Aprobación de Descuentos',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'Bloquea ventas que no alcanzan el margen mínimo y requiere aprobación.',
    'author': 'Isaac Espinosa',
    'website': 'https://isaacespd.github.io',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale_margin'],
    'data': [
        'security/sale_margin_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
}
