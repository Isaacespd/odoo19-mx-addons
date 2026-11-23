{
    'name': 'Odoo Approval Engine Core',
    'version': '19.0.2.0.0',
    'category': 'Framework',
    'summary': 'Motor centralizado de aprobaciones de múltiples pasos (Abstract Mixin).',
    'author': 'Isaac Espinosa',
    'website': 'https://isaacespd.github.io',
    'depends': ['base', 'mail'],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/approval_rule_views.xml',
        'views/approval_request_views.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
