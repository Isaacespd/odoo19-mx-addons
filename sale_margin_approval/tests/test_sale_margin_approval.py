from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleMarginApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestSaleMarginApproval, cls).setUpClass()
        
        # 1. Configurar margen en la compañia (e.g. 20%)
        cls.company = cls.env.company
        cls.company.min_margin_percentage = 20.0
        
        # 2. Crear usuarios
        sales_group = cls.env.ref('sales_team.group_sale_salesman')
        sales_all_group = cls.env.ref('sales_team.group_sale_salesman_all_leads')
        internal_group = cls.env.ref('base.group_user')
        approver_group = cls.env.ref('sale_margin_approval.group_sale_margin_approver')
        
        cls.user_salesman = cls.env['res.users'].create({
            'name': 'Vendedor Regular',
            'login': 'salesman@test.com',
            'group_ids': [(4, sales_group.id), (4, internal_group.id)]
        })
        
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Gerente Aprobador',
            'login': 'manager@test.com',
            'group_ids': [(4, sales_all_group.id), (4, internal_group.id), (4, approver_group.id)]
        })

        # 3. Crear productos
        cls.product_high_margin = cls.env['product.product'].create({
            'name': 'Producto Alto Margen',
            'list_price': 100.0,
            'standard_price': 50.0, # Margen de 50%
            'type': 'consu'
        })
        
        cls.product_low_margin = cls.env['product.product'].create({
            'name': 'Producto Bajo Margen',
            'list_price': 100.0,
            'standard_price': 90.0, # Margen de 10%
            'type': 'consu'
        })
        
        # Partner
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Test'})

    def test_01_high_margin_auto_confirm(self):
        """Ventas con margen superior al mínimo se confirman automáticamente."""
        order = self.env['sale.order'].with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_high_margin.id,
                    'product_uom_qty': 1.0,
                })
            ]
        })
        order.action_confirm()
        self.assertEqual(order.state, 'sale', "La cotización debió confirmarse ya que el margen es 50% (> 20%).")

    def test_02_low_margin_requires_approval(self):
        """Ventas con margen inferior al mínimo quedan en esperando aprobación."""
        order = self.env['sale.order'].with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_low_margin.id,
                    'product_uom_qty': 1.0,
                })
            ]
        })
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval', "La cotización debió detenerse ya que el margen es 10% (< 20%).")
        
        # Validar que un vendedor regular no puede aprobar ni rechazar
        with self.assertRaises(AccessError):
            order.action_approve_margin()
            
        with self.assertRaises(AccessError):
            order.action_reject_margin()
            
        # El gerente la aprueba
        order.with_user(self.user_manager).action_approve_margin()
        self.assertEqual(order.state, 'sale', "El gerente debió poder aprobar la cotización.")

    def test_03_reject_margin(self):
        """Un gerente puede rechazar la cotización y regresarla a borrador."""
        order = self.env['sale.order'].with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_low_margin.id,
                    'product_uom_qty': 1.0,
                })
            ]
        })
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval')
        
        order.with_user(self.user_manager).action_reject_margin()
        self.assertEqual(order.state, 'draft', "La cotización debió regresar a borrador tras ser rechazada.")

    def _create_order(self, product, price_unit=None):
        line = {'product_id': product.id, 'product_uom_qty': 1.0}
        if price_unit is not None:
            line['price_unit'] = price_unit
        return self.env['sale.order'].with_user(self.user_salesman).create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, line)],
        })

    def test_04_zero_minimum_disables_check(self):
        self.company.min_margin_percentage = 0.0
        order = self._create_order(self.product_low_margin)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_05_mixed_batch_only_low_margin_waits(self):
        high = self._create_order(self.product_high_margin)
        low = self._create_order(self.product_low_margin)
        (high | low).action_confirm()
        self.assertEqual(high.state, 'sale')
        self.assertEqual(low.state, 'waiting_approval')

    def test_06_margin_exactly_at_minimum_is_confirmed(self):
        # Costo 90 sobre precio 112.50 = 20% exacto, igual al mínimo.
        order = self._create_order(self.product_low_margin, price_unit=112.5)
        self.assertAlmostEqual(order.margin_percent_display, 20.0, places=2)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_07_rejected_order_can_be_fixed_and_confirmed(self):
        order = self._create_order(self.product_low_margin)
        order.action_confirm()
        order.with_user(self.user_manager).action_reject_margin()
        order.order_line.price_unit = 150.0
        order.action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_08_message_reports_margin(self):
        order = self._create_order(self.product_low_margin)
        order.action_confirm()
        self.assertIn('10.00%', order.message_ids[0].body)
