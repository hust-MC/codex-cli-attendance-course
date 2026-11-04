# 测试公共工具
# 提供隔离的临时数据库，让测试不污染正式的 checkin.db
import os
import tempfile
import unittest
from pathlib import Path

# 项目根目录，方便测试文件导入 app、db、services
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DatabaseTestCase(unittest.TestCase):
    """所有需要数据库的测试的基类

    每个测试类在同一个临时数据库上运行，测试之间用 setUp 清理业务数据。
    """

    @classmethod
    def setUpClass(cls):
        """为整个测试类准备一个临时数据库文件"""
        cls._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(cls._temp_dir.name) / 'test_checkin.db'
        # 必须在导入 db 模块之前设置环境变量，db 模块在导入时读取它
        os.environ['CHECKIN_DB_PATH'] = str(db_path)
        cls.db_path = db_path

        # 重新导入 db，确保它拿到新的数据库路径
        import db as db_module
        cls.db_module = db_module
        db_module.DB_PATH = db_path
        db_module.init_db()

    @classmethod
    def tearDownClass(cls):
        """清理临时数据库目录"""
        os.environ.pop('CHECKIN_DB_PATH', None)
        cls._temp_dir.cleanup()

    def setUp(self):
        """每个用例开始前清空业务数据，保证用例之间互不影响"""
        conn = self.db_module.get_db()
        try:
            for table in ('checkins', 'overtimes', 'leaves', 'employees'):
                conn.execute(f'DELETE FROM {table}')
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                         "('checkins', 'overtimes', 'leaves', 'employees')")
            conn.commit()
        finally:
            conn.close()

    def create_employee(self, name='张三', department='研发部',
                        employee_no='E1001', phone=None, status='active'):
        """快速创建一个测试员工，返回员工字典"""
        conn = self.db_module.get_db()
        try:
            cursor = conn.execute(
                '''
                INSERT INTO employees (name, department, employee_no, phone, status)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (name, department, employee_no, phone, status),
            )
            conn.commit()
            employee_id = cursor.lastrowid
        finally:
            conn.close()
        return {'id': employee_id, 'name': name, 'department': department,
                'employee_no': employee_no, 'phone': phone, 'status': status}

    def create_checkin(self, employee_id, check_type='in', check_time='2026-11-09 08:52:00'):
        """快速创建一条打卡记录"""
        conn = self.db_module.get_db()
        try:
            conn.execute(
                '''
                INSERT INTO checkins (employee_id, check_type, check_time, location, remark)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (employee_id, check_type, check_time, '总部一楼', '测试打卡'),
            )
            conn.commit()
        finally:
            conn.close()

    def create_leave(self, employee_id, leave_type='年假',
                     start_date='2026-11-16', end_date='2026-11-17',
                     days=2, status='pending'):
        """快速创建一条请假记录"""
        conn = self.db_module.get_db()
        try:
            conn.execute(
                '''
                INSERT INTO leaves (employee_id, leave_type, start_date, end_date,
                                    days, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (employee_id, leave_type, start_date, end_date, days, '测试请假', status),
            )
            conn.commit()
        finally:
            conn.close()

    def create_overtime(self, employee_id, work_date='2026-11-14',
                         hours=3.5, status='pending'):
        """快速创建一条加班记录"""
        conn = self.db_module.get_db()
        try:
            conn.execute(
                '''
                INSERT INTO overtimes (employee_id, work_date, hours, reason, status)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (employee_id, work_date, hours, '测试加班', status),
            )
            conn.commit()
        finally:
            conn.close()
