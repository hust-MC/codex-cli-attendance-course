"""请假业务单元测试

覆盖：提交、类型校验、日期校验、与已审批记录冲突、审批状态机。
"""
import unittest

from services import leave_service
from services.errors import ServiceError
from tests.base import DatabaseTestCase


class LeaveServiceTest(DatabaseTestCase):
    """请假业务服务测试"""

    def test_create_leave_success(self):
        """正常提交请假，自动计算天数"""
        employee = self.create_employee()
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-16',
            'end_date': '2026-11-17',
            'reason': '家庭旅行',
        })
        self.assertEqual(leave.leave_type, '年假')
        self.assertEqual(leave.days, 2)
        self.assertEqual(leave.status, 'pending')
        self.assertIsNone(leave.approver)

    def test_create_leave_single_day(self):
        """同一天请假的时长是 1 天"""
        employee = self.create_employee()
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '病假',
            'start_date': '2026-11-16',
            'end_date': '2026-11-16',
        })
        self.assertEqual(leave.days, 1)

    def test_create_leave_invalid_type(self):
        """请假类型非法时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '婚假',
                'start_date': '2026-11-16',
                'end_date': '2026-11-17',
            })
        self.assertIn('请假类型只能是', ctx.exception.message)

    def test_create_leave_start_after_end(self):
        """开始日期晚于结束日期时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '年假',
                'start_date': '2026-11-18',
                'end_date': '2026-11-16',
            })
        self.assertIn('开始日期不能晚于结束日期', ctx.exception.message)

    def test_create_leave_invalid_date_format(self):
        """日期格式错误时返回 400"""
        employee = self.create_employee()
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '年假',
                'start_date': '2026/11/16',
                'end_date': '2026-11-17',
            })
        self.assertIn('格式必须是 YYYY-MM-DD', ctx.exception.message)

    def test_create_leave_conflict_with_approved(self):
        """与已审批请假的时间段冲突时返回 400"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-16', end_date='2026-11-18')
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '事假',
                'start_date': '2026-11-17',
                'end_date': '2026-11-19',
            })
        self.assertIn('与已审批的请假冲突', ctx.exception.message)

    def test_leave_conflict_boundary_adjacent_days(self):
        """与已审批请假首尾相接时算冲突

        请假天数含首尾两天。已审批 11-18 到 11-20，新申请 11-20 到 11-22，
        11-20 这天被两段请假都算上了，属于真冲突，必须拦截。
        """
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-18', end_date='2026-11-20')
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '事假',
                'start_date': '2026-11-20',
                'end_date': '2026-11-22',
            })
        self.assertIn('与已审批的请假冲突', ctx.exception.message)

    def test_leave_conflict_day_after_approved_ok(self):
        """已审批请假结束后的第二天开始申请，不构成冲突

        已审批 11-18 到 11-20，新申请 11-21 到 11-22，两段完全不相交。
        """
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-18', end_date='2026-11-20')

        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-21',
            'end_date': '2026-11-22',
        })
        self.assertEqual(leave.start_date, '2026-11-21')
        self.assertEqual(leave.days, 2)

    def test_leave_conflict_day_before_approved_ok(self):
        """已审批请假开始前的区间申请，不构成冲突"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-18', end_date='2026-11-20')
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-16',
            'end_date': '2026-11-17',
        })
        self.assertEqual(leave.start_date, '2026-11-16')

    def test_leave_conflict_fully_overlapped(self):
        """区间完全落在已审批请假之内时必须拦截"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-18', end_date='2026-11-20')
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '事假',
                'start_date': '2026-11-19',
                'end_date': '2026-11-21',
            })
        self.assertIn('与已审批的请假冲突', ctx.exception.message)

    def test_leave_conflict_containing_approved(self):
        """新区间完全覆盖已审批请假时必须拦截"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-19', end_date='2026-11-20')
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '事假',
                'start_date': '2026-11-18',
                'end_date': '2026-11-22',
            })
        self.assertIn('与已审批的请假冲突', ctx.exception.message)

    def test_leave_conflict_before_approved(self):
        """新区间完全在已审批请假之前时不构成冲突"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-18', end_date='2026-11-20')
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-16',
            'end_date': '2026-11-17',
        })
        self.assertEqual(leave.start_date, '2026-11-16')

    def test_create_leave_no_conflict_with_pending(self):
        """待审批的请假不构成冲突"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='pending',
                          start_date='2026-11-16', end_date='2026-11-18')
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-17',
            'end_date': '2026-11-19',
        })
        self.assertEqual(leave.status, 'pending')

    def test_create_leave_quit_employee_blocked(self):
        """离职员工不能提交请假"""
        employee = self.create_employee(status='quit')
        with self.assertRaises(ServiceError) as ctx:
            leave_service.create_leave({
                'employee_id': employee['id'],
                'leave_type': '年假',
                'start_date': '2026-11-16',
                'end_date': '2026-11-17',
            })
        self.assertIn('已离职', ctx.exception.message)

    def test_approve_leave_success(self):
        """审批通过请假"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        leave = leave_service.approve_leave(1, {'approver': '王经理', 'comment': '同意'})
        self.assertEqual(leave.status, 'approved')
        self.assertEqual(leave.approver, '王经理')
        self.assertEqual(leave.approve_comment, '同意')

    def test_approve_leave_twice_blocked(self):
        """已处理的请假不能重复审批"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        leave_service.approve_leave(1, {'approver': '王经理'})
        with self.assertRaises(ServiceError) as ctx:
            leave_service.approve_leave(1, {'approver': '王经理'})
        self.assertIn('不能重复处理', ctx.exception.message)

    def test_approve_leave_conflict_with_approved_blocked(self):
        """审批时与已审批请假冲突必须被拒绝

        回归用例：修复前，两条时间重叠的请假可以先后都被审批通过，
        导致数据库里出现两条已审批的重叠请假。
        """
        employee = self.create_employee()
        leave_a = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-18',
            'end_date': '2026-11-20',
        })
        leave_b = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-19',
            'end_date': '2026-11-21',
        })

        leave_service.approve_leave(leave_a.id, {'approver': '王经理'})

        with self.assertRaises(ServiceError) as ctx:
            leave_service.approve_leave(leave_b.id, {'approver': '王经理'})
        self.assertIn('冲突', ctx.exception.message)

    def test_approve_leave_conflict_free_ok(self):
        """审批时与已审批请假不冲突时可以正常通过"""
        employee = self.create_employee()
        leave_a = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-18',
            'end_date': '2026-11-20',
        })
        leave_b = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '事假',
            'start_date': '2026-11-22',
            'end_date': '2026-11-23',
        })

        leave_service.approve_leave(leave_a.id, {'approver': '王经理'})
        approved = leave_service.approve_leave(leave_b.id, {'approver': '王经理'})
        self.assertEqual(approved.status, 'approved')

    def test_reject_leave_success(self):
        """驳回请假"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        leave = leave_service.reject_leave(1, {'approver': '王经理', 'comment': '材料不全'})
        self.assertEqual(leave.status, 'rejected')
        self.assertEqual(leave.approve_comment, '材料不全')

    def test_reject_after_approve_blocked(self):
        """已通过的请假不能再被驳回"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        leave_service.approve_leave(1, {'approver': '王经理'})
        with self.assertRaises(ServiceError) as ctx:
            leave_service.reject_leave(1, {'approver': '王经理'})
        self.assertIn('已经通过', ctx.exception.message)

    def test_approve_leave_without_approver(self):
        """审批人必填"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        with self.assertRaises(ServiceError) as ctx:
            leave_service.approve_leave(1, {'comment': '同意'})
        self.assertIn('审批人不能为空', ctx.exception.message)

    def test_get_leave_not_found(self):
        """查询不存在的请假返回 404"""
        with self.assertRaises(ServiceError) as ctx:
            leave_service.get_leave(999)
        self.assertEqual(ctx.exception.code, 404)

    def test_list_leaves_filter_by_status(self):
        """按状态筛选请假"""
        employee = self.create_employee()
        self.create_leave(employee['id'], status='pending')
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-20', end_date='2026-11-21')

        result = leave_service.list_leaves(status='approved')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['status'], 'approved')

    def test_list_leaves_invalid_status(self):
        """非法状态筛选返回 400"""
        with self.assertRaises(ServiceError) as ctx:
            leave_service.list_leaves(status='unknown')
        self.assertIn('审批状态只能是', ctx.exception.message)


if __name__ == '__main__':
    unittest.main()
