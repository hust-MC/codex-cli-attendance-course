"""员工服务单元测试

覆盖：新增、列表筛选、详情、修改、逻辑离职，以及各种错误场景。
"""
import unittest

from services import employee_service
from services.errors import ServiceError
from tests.base import DatabaseTestCase


class EmployeeServiceTest(DatabaseTestCase):
    """员工业务服务测试"""

    def test_create_employee_success(self):
        """正常新增员工返回完整信息"""
        employee = employee_service.create_employee({
            'name': '张三',
            'department': '研发部',
            'employee_no': 'E1001',
            'phone': '13800000001',
        })
        self.assertEqual(employee.name, '张三')
        self.assertEqual(employee.department, '研发部')
        self.assertEqual(employee.employee_no, 'E1001')
        self.assertEqual(employee.status, 'active')
        self.assertGreater(employee.id, 0)

    def test_create_employee_duplicate_no(self):
        """工号重复时抛出业务错误"""
        self.create_employee(employee_no='E1001')
        with self.assertRaises(ServiceError) as ctx:
            employee_service.create_employee({
                'name': '李四',
                'department': '市场部',
                'employee_no': 'E1001',
            })
        self.assertIn('工号已存在', ctx.exception.message)
        self.assertEqual(ctx.exception.code, 400)

    def test_create_employee_missing_required_field(self):
        """缺少必填字段时抛出业务错误"""
        with self.assertRaises(ServiceError) as ctx:
            employee_service.create_employee({
                'name': '张三',
                'employee_no': 'E1001',
            })
        self.assertIn('部门不能为空', ctx.exception.message)

    def test_create_employee_name_too_long(self):
        """姓名超长时抛出业务错误"""
        with self.assertRaises(ServiceError) as ctx:
            employee_service.create_employee({
                'name': '张' * 60,
                'department': '研发部',
                'employee_no': 'E1001',
            })
        self.assertIn('不能超过 50 个字符', ctx.exception.message)

    def test_get_employee_not_found(self):
        """查询不存在的员工返回 404"""
        with self.assertRaises(ServiceError) as ctx:
            employee_service.get_employee(999)
        self.assertEqual(ctx.exception.code, 404)
        self.assertIn('员工不存在', ctx.exception.message)

    def test_get_employee_invalid_id(self):
        """非法员工编号返回 400"""
        for bad_id in (0, -1, 'abc', None):
            with self.subTest(bad_id=bad_id):
                with self.assertRaises(ServiceError) as ctx:
                    employee_service.get_employee(bad_id)
                self.assertEqual(ctx.exception.code, 400)

    def test_list_employees_filter_by_department(self):
        """按部门筛选员工"""
        self.create_employee(name='张三', department='研发部', employee_no='E1001')
        self.create_employee(name='李四', department='市场部', employee_no='E1002')
        self.create_employee(name='王五', department='市场部', employee_no='E1003')

        result = employee_service.list_employees(department='市场部')
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['items']), 2)
        self.assertTrue(all(item['department'] == '市场部' for item in result['items']))

    def test_list_employees_filter_by_status(self):
        """按在职状态筛选员工"""
        self.create_employee(name='张三', employee_no='E1001', status='active')
        self.create_employee(name='孙七', employee_no='E1002', status='quit')

        result = employee_service.list_employees(status='quit')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['name'], '孙七')

    def test_list_employees_keyword_search(self):
        """按关键字模糊搜索姓名和工号"""
        self.create_employee(name='张三', employee_no='E1001')
        self.create_employee(name='李四', employee_no='E2002')

        result = employee_service.list_employees(keyword='E100')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['name'], '张三')

    def test_update_employee_partial(self):
        """只传要改的字段，其他字段保持不变"""
        original = self.create_employee(name='张三', department='研发部',
                                        employee_no='E1001', phone='13800000001')
        updated = employee_service.update_employee(original['id'], {'name': '张三丰'})
        self.assertEqual(updated.name, '张三丰')
        self.assertEqual(updated.department, '研发部')
        self.assertEqual(updated.employee_no, 'E1001')
        self.assertEqual(updated.phone, '13800000001')

    def test_update_employee_duplicate_no(self):
        """改成已存在的工号时抛出业务错误"""
        self.create_employee(name='张三', employee_no='E1001')
        other = self.create_employee(name='李四', employee_no='E1002')
        with self.assertRaises(ServiceError) as ctx:
            employee_service.update_employee(other['id'], {'employee_no': 'E1001'})
        self.assertIn('工号已存在', ctx.exception.message)

    def test_delete_employee_is_logical(self):
        """离职是逻辑删除，历史记录保留"""
        employee = self.create_employee()
        self.create_checkin(employee['id'])

        result = employee_service.delete_employee(employee['id'])
        self.assertEqual(result['status'], 'quit')

        # 员工记录还在，打卡记录也还在
        still_there = employee_service.get_employee(employee['id'])
        self.assertEqual(still_there.status, 'quit')

        conn = self.db_module.get_db()
        try:
            count = conn.execute(
                'SELECT COUNT(*) FROM checkins WHERE employee_id = ?',
                (employee['id'],),
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1, '逻辑离职不应该删除历史打卡记录')

    def test_delete_employee_twice(self):
        """重复离职抛出业务错误"""
        employee = self.create_employee()
        employee_service.delete_employee(employee['id'])
        with self.assertRaises(ServiceError) as ctx:
            employee_service.delete_employee(employee['id'])
        self.assertIn('已经离职', ctx.exception.message)


if __name__ == '__main__':
    unittest.main()
