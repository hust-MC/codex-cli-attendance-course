"""第五章：Bug 复现用的探索测试

这个文件不是回归测试，而是用来「找 Bug」的探索脚本。
每个用例先写成失败的样子，跑出真实报错，再决定怎么修。

跑法：
    python3 -m unittest tests.test_bug_exploration -v
"""
import unittest

from services import checkin_service, leave_service
from services.errors import ServiceError
from tests.base import DatabaseTestCase


class BugExplorationTest(DatabaseTestCase):
    """探索用例：先假设有 Bug，看真实行为"""

    def test_probe_overlapping_leaves_both_approved(self):
        """探测：两条时间重叠的请假，能不能先后都被审批通过

        场景：
        1. 员工提交请假 A：11-18 到 11-20
        2. 员工提交请假 B：11-19 到 11-21
           （此时 A 还是 pending，不构成冲突，允许提交）
        3. 主管审批通过 A
        4. 主管再审批通过 B
           （此时 A 已是 approved，B 与 A 重叠，应该被拒绝）

        预期：第 4 步应该报冲突错误。
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

        # 第一条审批通过
        leave_service.approve_leave(leave_a.id, {'approver': '王经理'})

        # 第二条此时与已审批的第一条重叠，应该被拒绝
        with self.assertRaises(ServiceError) as ctx:
            leave_service.approve_leave(leave_b.id, {'approver': '王经理'})
        self.assertIn('冲突', ctx.exception.message)

    def test_probe_checkin_leave_interaction(self):
        """探测：已审批的全天请假当天还能不能打卡

        业务上应该允许：请假的人照样可以打卡，系统只是不给他生成异常。
        """
        employee = self.create_employee()
        self.create_leave(employee['id'], status='approved',
                          start_date='2026-11-09', end_date='2026-11-09')
        record = checkin_service.create_checkin({'employee_id': employee['id']}, 'in')
        self.assertEqual(record.check_type, 'in')

    def test_probe_approver_missing(self):
        """探测：审批时传空审批人会怎样"""
        employee = self.create_employee()
        self.create_leave(employee['id'])
        with self.assertRaises(ServiceError):
            leave_service.approve_leave(1, {'approver': ''})

    def test_probe_reject_then_resubmit_same_range(self):
        """探测：请假被驳回后，能不能再提交同一时间段

        预期：可以，驳回的记录不构成冲突。
        """
        employee = self.create_employee()
        leave = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-18',
            'end_date': '2026-11-20',
        })
        leave_service.reject_leave(leave.id, {'approver': '王经理', 'comment': '材料不全'})

        again = leave_service.create_leave({
            'employee_id': employee['id'],
            'leave_type': '年假',
            'start_date': '2026-11-18',
            'end_date': '2026-11-20',
        })
        self.assertEqual(again.status, 'pending')


if __name__ == '__main__':
    unittest.main()
