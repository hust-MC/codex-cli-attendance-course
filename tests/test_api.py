"""接口层测试

验证 HTTP 层的统一响应格式、错误码和状态码映射。
这些是前端和第三方调用方依赖的契约，改动必须同步改测试。
"""
import unittest

from app import create_app
from tests.base import DatabaseTestCase


class ApiResponseTest(DatabaseTestCase):
    """接口响应格式测试"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 用测试配置创建应用，避免加载正式数据库
        cls.app = create_app()
        cls.app.config['TESTING'] = True

    def setUp(self):
        super().setUp()
        self.client = self.app.test_client()

    def test_health_check(self):
        """健康检查返回统一成功格式"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['message'], '服务正常')
        self.assertIsNone(body['data'])

    def test_error_response_format(self):
        """错误响应同时设置 HTTP 状态码和响应体 code"""
        response = self.client.get('/api/employees/999')
        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertEqual(body['code'], 404)
        self.assertIn('message', body)
        self.assertIsNone(body['data'])

    def test_bad_request_response(self):
        """参数错误返回 400"""
        response = self.client.post('/api/employees', json={'name': '张三'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['code'], 400)

    def test_not_found_endpoint(self):
        """不存在的接口返回 404"""
        response = self.client.get('/api/not-exists')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['code'], 404)

    def test_method_not_allowed(self):
        """方法不支持返回 405"""
        response = self.client.put('/api/health')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()['code'], 405)

    def test_invalid_json_body(self):
        """请求体不是 JSON 对象时返回 400"""
        response = self.client.post(
            '/api/employees',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('JSON', response.get_json()['message'])

    def test_employee_list_shape(self):
        """列表接口返回 total 和 items，不返回裸数组"""
        self.create_employee()
        response = self.client.get('/api/employees')
        body = response.get_json()
        self.assertEqual(body['code'], 200)
        self.assertIn('total', body['data'])
        self.assertIn('items', body['data'])
        self.assertEqual(body['data']['total'], 1)

    def test_leave_list_shape(self):
        """请假列表同样返回统一结构"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        response = self.client.get('/api/leaves')
        body = response.get_json()
        self.assertIn('total', body['data'])
        self.assertIn('items', body['data'])

    def test_chinese_message_not_escaped(self):
        """中文提示不转义，方便前端直接展示"""
        response = self.client.post('/api/employees', json={'name': '张三'})
        message = response.get_json()['message']
        self.assertIn('部门', message)
        self.assertNotIn('\\u', message)

    def test_checkin_flow_through_api(self):
        """完整的签到签出流程"""
        employee = self.create_employee()
        response = self.client.post('/api/checkins/in', json={'employee_id': employee['id']})
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/api/checkins/out', json={'employee_id': employee['id']})
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/api/checkins?employee_id={employee['id']}")
        body = response.get_json()
        self.assertIsNotNone(body['data']['first_in'])
        self.assertIsNotNone(body['data']['last_out'])

    def test_leave_approval_flow_through_api(self):
        """完整的请假审批流程"""
        employee = self.create_employee()
        response = self.client.post('/api/leaves', json={
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-16',
            'end_date': '2026-11-17',
        })
        self.assertEqual(response.status_code, 200)
        leave_id = response.get_json()['data']['id']

        response = self.client.post(
            f'/api/leaves/{leave_id}/approve',
            json={'approver': '王经理'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data']['status'], 'approved')

        response = self.client.post(
            f'/api/leaves/{leave_id}/approve',
            json={'approver': '王经理'},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
