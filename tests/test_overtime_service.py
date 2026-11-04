"""加班业务单元测试

覆盖：提交、时长校验、同日重复、审批状态机。
"""
import unittest

from services import overtime_service
from services.errors import ServiceError
from tests.base import DatabaseTestCase


class OvertimeServiceTest(DatabaseTestCase):
    """加班业务服务测试"""

    def test_create_overtime_success(self):
        """正常提交加班申请"""
        employee = self.create_employee()
        overtime = overtime_service.create_overtime({
            'employee_id': employee['id'],
            'work_date': '2026-11-14',
            'hours': 3.5,
            'reason': '版本上线',
        })
        self.assertEqual(overtime.hours, 3.5)
        self.assertEqual(overtime.status, 'pending')
        self.assertEqual(overtime.work_date, '2026-11-14')

    def test_create_overtime_zero_hours(self):
        """时长为 0 时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.create_overtime({
                'employee_id': employee['id'],
                'work_date': '2026-11-14',
                'hours': 0,
            })
        self.assertIn('必须大于 0', ctx.exception.message)

    def test_create_overtime_exceed_limit(self):
        """时长超过 24 小时时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.create_overtime({
                'employee_id': employee['id'],
                'work_date': '2026-11-14',
                'hours': 25,
            })
        self.assertIn('不能超过 24 小时', ctx.exception.message)

    def test_create_overtime_invalid_hours_type(self):
        """时长不是数字时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.create_overtime({
                'employee_id': employee['id'],
                'work_date': '2026-11-14',
                'hours': '很多',
            })
        self.assertIn('必须是数字', ctx.exception.message)

    def test_create_overtime_same_day_duplicate(self):
        """同一员工同一天只能有一条加班申请"""
        employee = self.create_employee()
        self.create_overtime(employee['id'], work_date='2026-11-14')
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.create_overtime({
                'employee_id': employee['id'],
                'work_date': '2026-11-14',
                'hours': 2,
            })
        self.assertIn('当天已经提交过加班申请', ctx.exception.message)

    def test_create_overtime_different_day_ok(self):
        """不同日期可以重复提交"""
        employee = self.create_employee()
        self.create_overtime(employee['id'], work_date='2026-11-14')
        overtime = overtime_service.create_overtime({
            'employee_id': employee['id'],
            'work_date': '2026-11-15',
            'hours': 2,
        })
        self.assertEqual(overtime.work_date, '2026-11-15')

    def test_create_overtime_quit_employee_blocked(self):
        """离职员工不能提交加班"""
        employee = self.create_employee(status='quit')
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.create_overtime({
                'employee_id': employee['id'],
                'work_date': '2026-11-14',
                'hours': 2,
            })
        self.assertIn('已离职', ctx.exception.message)

    def test_approve_overtime_success(self):
        """审批通过加班"""
        employee = self.create_employee()
        self.create_overtime(employee['id'])
        overtime = overtime_service.approve_overtime(1, {'approver': '王经理'})
        self.assertEqual(overtime.status, 'approved')
        self.assertEqual(overtime.approver, '王经理')

    def test_approve_overtime_twice_blocked(self):
        """已审批的加班不能重复审批"""
        employee = self.create_employee()
        self.create_overtime(employee['id'])
        overtime_service.approve_overtime(1, {'approver': '王经理'})
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.approve_overtime(1, {'approver': '王经理'})
        self.assertIn('不能重复审批', ctx.exception.message)

    def test_reject_overtime_success(self):
        """驳回加班"""
        employee = self.create_employee()
        self.create_overtime(employee['id'])
        overtime = overtime_service.reject_overtime(1, {'approver': '王经理', 'comment': '本月额度已满'})
        self.assertEqual(overtime.status, 'rejected')
        self.assertEqual(overtime.approve_comment, '本月额度已满')

    def test_get_overtime_not_found(self):
        """查询不存在的加班返回 404"""
        with self.assertRaises(ServiceError) as ctx:
            overtime_service.get_overtime(999)
        self.assertEqual(ctx.exception.code, 404)

    def test_list_overtimes_filter_by_status(self):
        """按状态筛选加班"""
        employee = self.create_employee()
        self.create_overtime(employee['id'], status='pending')
        self.create_overtime(employee['id'], status='approved', work_date='2026-11-20')

        result = overtime_service.list_overtimes(status='approved')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['work_date'], '2026-11-20')


if __name__ == '__main__':
    unittest.main()
