from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestApprovalEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.finance_group = cls.env['res.groups'].create({'name': 'Finanzas (test)'})
        approval_user = 'base.group_user,base_approval_engine.group_approval_user'
        cls.requester = new_test_user(cls.env, login='requester', groups=approval_user)
        cls.boss = new_test_user(cls.env, login='boss', groups=approval_user)
        cls.finance = new_test_user(cls.env, login='finance', groups=approval_user)
        cls.finance.group_ids |= cls.finance_group
        cls.outsider = new_test_user(cls.env, login='outsider', groups=approval_user)
        cls.manager = new_test_user(
            cls.env, login='approval_manager',
            groups='base.group_user,base_approval_engine.group_approval_manager')

        cls.rule = cls.env['approval.rule'].create({
            'name': 'Montos mayores a 10,000',
            'model_id': cls.env['ir.model']._get_id('approval.test.document'),
            'domain': "[('amount', '>', 10000)]",
            'step_ids': [
                (0, 0, {'sequence': 1, 'name': 'Jefe directo', 'user_id': cls.boss.id}),
                (0, 0, {'sequence': 2, 'name': 'Finanzas', 'group_id': cls.finance_group.id}),
            ],
        })
        Document = cls.env['approval.test.document'].with_user(cls.requester)
        cls.small = Document.create({'name': 'Gasto chico', 'amount': 500})
        cls.big = Document.create({'name': 'Gasto grande', 'amount': 50000})

    def _request(self):
        return self.big.approval_request_id

    def test_no_rule_matches_flow_continues(self):
        self.small.action_confirm()
        self.assertEqual(self.small.state, 'done')
        self.assertEqual(self.small.approval_state, 'none')
        self.assertFalse(self.small.approval_request_id)

    def test_rule_match_creates_pending_request(self):
        self.big.action_confirm()
        self.assertEqual(self.big.state, 'draft')
        self.assertEqual(self.big.approval_state, 'pending')
        request = self._request()
        self.assertEqual(request.state, 'pending')
        self.assertEqual(request.current_step_id.name, 'Jefe directo')
        self.assertTrue(request.name.startswith('APR/'))

    def test_inactive_rule_is_ignored(self):
        self.rule.active = False
        self.big.action_confirm()
        self.assertEqual(self.big.state, 'done')

    def test_multi_step_approval_completes_document(self):
        self.big.action_confirm()
        request = self._request()
        request.with_user(self.boss).action_approve()
        self.assertEqual(request.state, 'pending')
        self.assertEqual(request.current_step_id.name, 'Finanzas')
        request.with_user(self.finance).action_approve(comment='Presupuesto disponible')
        self.assertEqual(request.state, 'approved')
        self.assertEqual(self.big.approval_state, 'approved')
        self.assertEqual(self.big.state, 'done')
        self.assertEqual(request.log_ids.mapped('user_id'), self.finance | self.boss)
        self.assertEqual(set(request.log_ids.mapped('state')), {'approved'})

    def test_wrong_user_cannot_approve_step(self):
        self.big.action_confirm()
        request = self._request()
        for user in (self.outsider, self.requester, self.finance):
            with self.assertRaises(AccessError):
                request.with_user(user).action_approve()
        self.assertFalse(request.with_user(self.outsider).can_review)
        self.assertTrue(request.with_user(self.boss).can_review)

    def test_group_step_requires_group(self):
        self.big.action_confirm()
        request = self._request()
        request.with_user(self.boss).action_approve()
        with self.assertRaises(AccessError):
            request.with_user(self.boss).action_approve()
        request.with_user(self.finance).action_approve()
        self.assertEqual(request.state, 'approved')

    def test_manager_can_review_any_step(self):
        self.big.action_confirm()
        request = self._request()
        request.with_user(self.manager).action_approve()
        request.with_user(self.manager).action_approve()
        self.assertEqual(request.state, 'approved')

    def test_reject_refuses_document(self):
        self.big.action_confirm()
        request = self._request()
        request.with_user(self.boss).action_reject(comment='Fuera de presupuesto')
        self.assertEqual(request.state, 'rejected')
        self.assertEqual(self.big.state, 'refused')
        self.assertEqual(self.big.approval_state, 'none')
        self.assertEqual(request.log_ids.comment, 'Fuera de presupuesto')

    def test_closed_request_cannot_be_reviewed_again(self):
        self.big.action_confirm()
        request = self._request()
        request.with_user(self.boss).action_reject()
        with self.assertRaises(UserError):
            request.with_user(self.manager).action_approve()

    def test_users_cannot_write_request_state_directly(self):
        self.big.action_confirm()
        with self.assertRaises(AccessError):
            self._request().with_user(self.boss).write({'state': 'approved'})

    def test_confirm_twice_does_not_duplicate_request(self):
        self.big.action_confirm()
        request = self._request()
        self.big.action_confirm()
        self.assertEqual(self._request(), request)
        self.assertEqual(self.env['approval.request'].search_count([
            ('res_model', '=', 'approval.test.document'), ('res_id', '=', self.big.id)]), 1)

    def test_rule_without_steps_any_approval_user_can_approve(self):
        self.rule.step_ids.unlink()
        self.big.action_confirm()
        self._request().with_user(self.outsider).action_approve()
        self.assertEqual(self.big.state, 'done')
