"""打卡服务单元测试

覆盖：签到、签出、重复打卡拦截、未签到先签出、离职员工打卡、记录查询。
"""
import unittest

from services import checkin_service
from services.errors import ServiceError
from tests.base import DatabaseTestCase


class CheckinServiceTest(DatabaseTestCase):
    """打卡业务服务测试"""

    def test_checkin_success(self):
        """正常签到返回打卡记录"""
        employee = self.create_employee()
        record = checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        self.assertEqual(record.employee_id, employee['id'])
        self.assertEqual(record.check_type, 'in')
        self.assertTrue(record.check_time)

    def test_checkin_with_location_and_remark(self):
        """签到可以带上地点和备注"""
        employee = self.create_employee()
        record = checkin_service.create_checkin({
            'employee_id': employee['id'],
            'location': '总部一楼',
            'remark': '准时到岗',
        }, 'in')
        self.assertEqual(record.location, '总部一楼')
        self.assertEqual(record.remark, '准时到岗')

    def test_checkin_duplicate_blocked(self):
        """同一天重复签到被拦截"""
        employee = self.create_employee()
        checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        self.assertIn('当天已经签到', ctx.exception.message)

    def test_checkout_before_checkin_blocked(self):
        """没签到直接签出被拦截"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin({'employee_id': employee['id']}, 'out')
        self.assertIn('还没有签到', ctx.exception.message)

    def test_checkout_after_checkin_success(self):
        """签到之后可以签出"""
        employee = self.create_employee()
        checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        record = checkin_service.create_checkin({'employee_id': employee['id']}, 'out')
        self.assertEqual(record.check_type, 'out')

    def test_checkin_quit_employee_blocked(self):
        """离职员工不能打卡"""
        employee = self.create_employee(status='quit')
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        self.assertIn('已离职', ctx.exception.message)

    def test_checkin_employee_not_found(self):
        """给不存在的员工打卡返回 404"""
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin({'employee_id': 999}, 'in')
        self.assertEqual(ctx.exception.code, 404)

    def test_checkin_invalid_employee_id(self):
        """员工编号非法时返回 400"""
        for bad_id in (0, -5, 'abc'):
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ServiceError) as ctx:
                    checkin_service.create_checkin({'employee_id': bad_id}, 'in')
                self.assertEqual(ctx.exception.code, 400)

    def test_checkin_invalid_type(self):
        """打卡类型非法时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin({'employee_id': employee['id']}, 'break')
        self.assertIn('打卡类型不合法', ctx.exception.message)

    def test_checkin_missing_body(self):
        """请求体不是对象时返回 400"""
        with self.assertRaises(ServiceError) as ctx:
            checkin_service.create_checkin('not a dict', 'in')
        self.assertIn('必须是 JSON 对象', ctx.exception.message)

    def test_checkin_custom_time(self):
        """可以指定打卡时间，用于测试和演示"""
        employee = self.create_employee()
        record = checkin_service.create_checkin({
            'employee_id': employee['id'],
            'check_time': '2026-11-09 08:52:00',
        }, 'in')
        self.assertTrue(record.check_time.startswith('2026-11-09'))

    def test_query_checkins_returns_first_in_and_last_out(self):
        """查询记录返回首次签到和最后签出"""
        employee = self.create_employee()
        self.create_checkin(employee['id'], 'in', '2026-11-09 08:52:00')
        self.create_checkin(employee['id'], 'out', '2026-11-09 18:30:00')

        result = checkin_service.list_checkins(employee['id'], '2026-11-09')
        self.assertEqual(result['first_in'], '2026-11-09 08:52:00')
        self.assertEqual(result['last_out'], '2026-11-09 18:30:00')
        self.assertEqual(len(result['records']), 2)

    def test_query_checkins_empty(self):
        """没有打卡记录时返回空结构而不是报错"""
        employee = self.create_employee()
        result = checkin_service.list_checkins(employee['id'], '2026-11-09')
        self.assertIsNone(result['first_in'])
        self.assertIsNone(result['last_out'])
        self.assertEqual(result['records'], [])


if __name__ == '__main__':
    unittest.main()
