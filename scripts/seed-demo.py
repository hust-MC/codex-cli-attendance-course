#!/usr/bin/env python3
# ============================================================
# seed-demo.py — 生成固定演示数据
#
# 用法：
#   python3 scripts/seed-demo.py            # 重置并写入固定演示数据
#   python3 scripts/seed-demo.py --keep-db  # 只写数据，不清库
#
# 为什么要固定数据：
#   演示数据如果每次都不一样，录制时会出现「上次跑过了所以报重复工号」
#   「员工已离职不能打卡」这类漂移，观众会以为是 Bug。
#   这个脚本让每次录制开始前的状态完全一致。
#
# 演示日期写死，不使用今天，避免跨天后结果变化。
# ============================================================

import os
import sys
from pathlib import Path

# 允许以脚本方式直接运行，把项目根目录加入导入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db as db_module  # noqa: E402


# 固定演示日期，不随系统日期变化
DEMO_DATE = '2026-11-09'
DEMO_CHECKIN_TIME = f'{DEMO_DATE} 08:52:00'
DEMO_CHECKOUT_TIME = f'{DEMO_DATE} 18:30:00'


# 演示员工：覆盖在职、离职、无手机号三种情况
DEMO_EMPLOYEES = [
    {
        'name': '张三',
        'department': '研发部',
        'employee_no': 'E1001',
        'phone': '13800000001',
        'status': 'active',
    },
    {
        'name': '李四',
        'department': '研发部',
        'employee_no': 'E1002',
        'phone': '13800000002',
        'status': 'active',
    },
    {
        'name': '王五',
        'department': '市场部',
        'employee_no': 'E1003',
        'phone': None,
        'status': 'active',
    },
    {
        'name': '赵六',
        'department': '市场部',
        'employee_no': 'E1004',
        'phone': None,
        'status': 'active',
    },
    {
        'name': '孙七',
        'department': '人事部',
        'employee_no': 'E1005',
        'phone': None,
        'status': 'quit',
    },
]

# 打卡记录：覆盖正常打卡和缺下班卡两种情况
DEMO_CHECKINS = [
    {'employee_no': 'E1001', 'check_type': 'in', 'check_time': DEMO_CHECKIN_TIME},
    {'employee_no': 'E1001', 'check_type': 'out', 'check_time': DEMO_CHECKOUT_TIME},
    # 李四只打了上班卡，用来演示缺下班卡
    {'employee_no': 'E1002', 'check_type': 'in', 'check_time': DEMO_CHECKIN_TIME},
]

# 请假记录：覆盖待审批、已通过、已驳回三种状态
DEMO_LEAVES = [
    {
        'employee_no': 'E1001',
        'leave_type': '年假',
        'start_date': '2026-11-16',
        'end_date': '2026-11-17',
        'days': 2,
        'reason': '家庭旅行',
        'status': 'pending',
        'approver': None,
        'approve_comment': None,
    },
    {
        'employee_no': 'E1002',
        'leave_type': '事假',
        'start_date': '2026-11-12',
        'end_date': '2026-11-13',
        'days': 2,
        'reason': '陪同家人就医',
        'status': 'approved',
        'approver': '王经理',
        'approve_comment': '同意',
    },
    {
        'employee_no': 'E1003',
        'leave_type': '病假',
        'start_date': '2026-11-10',
        'end_date': '2026-11-10',
        'days': 1,
        'reason': '感冒发烧',
        'status': 'rejected',
        'approver': '王经理',
        'approve_comment': '提交时缺少医院证明',
    },
]

# 加班记录：覆盖待审批和已通过
DEMO_OVERTIMES = [
    {
        'employee_no': 'E1001',
        'work_date': '2026-11-14',
        'hours': 3.5,
        'reason': '版本上线',
        'status': 'pending',
        'approver': None,
        'approve_comment': None,
    },
    {
        'employee_no': 'E1004',
        'work_date': '2026-11-13',
        'hours': 2.0,
        'reason': '客户现场支持',
        'status': 'approved',
        'approver': '王经理',
        'approve_comment': '已确认',
    },
]


def clear_data(conn):
    """清空所有业务数据，保留表结构"""
    for table in ('checkins', 'overtimes', 'leaves', 'employees'):
        conn.execute(f'DELETE FROM {table}')
    # 重置自增主键，让每次演示的 ID 保持一致
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                 "('checkins', 'overtimes', 'leaves', 'employees')")


def seed_employees(conn):
    """写入演示员工，返回工号到 ID 的映射"""
    id_map = {}
    for item in DEMO_EMPLOYEES:
        cursor = conn.execute(
            '''
            INSERT INTO employees (name, department, employee_no, phone, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                item['name'],
                item['department'],
                item['employee_no'],
                item['phone'],
                item['status'],
                f'{DEMO_DATE} 08:00:00',
            ),
        )
        id_map[item['employee_no']] = cursor.lastrowid
    return id_map


def seed_checkins(conn, id_map):
    """写入演示打卡记录"""
    for item in DEMO_CHECKINS:
        conn.execute(
            '''
            INSERT INTO checkins (employee_id, check_type, check_time, location, remark)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                id_map[item['employee_no']],
                item['check_type'],
                item['check_time'],
                '总部一楼' if item['check_type'] == 'in' else None,
                '准时到岗' if item['check_type'] == 'in' else '完成当天工作',
            ),        )


def seed_leaves(conn, id_map):
    """写入演示请假记录"""
    for item in DEMO_LEAVES:
        conn.execute(
            '''
            INSERT INTO leaves (
                employee_id, leave_type, start_date, end_date, days, reason,
                status, approver, approve_comment, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                id_map[item['employee_no']],
                item['leave_type'],
                item['start_date'],
                item['end_date'],
                item['days'],
                item['reason'],
                item['status'],
                item['approver'],
                item['approve_comment'],
                f'{DEMO_DATE} 08:00:00',
                f'{DEMO_DATE} 08:00:00',
            ),
        )


def seed_overtimes(conn, id_map):
    """写入演示加班记录"""
    for item in DEMO_OVERTIMES:
        conn.execute(
            '''
            INSERT INTO overtimes (
                employee_id, work_date, hours, reason,
                status, approver, approve_comment, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                id_map[item['employee_no']],
                item['work_date'],
                item['hours'],
                item['reason'],
                item['status'],
                item['approver'],
                item['approve_comment'],
                f'{DEMO_DATE} 08:00:00',
                f'{DEMO_DATE} 08:00:00',
            ),
        )


def main():
    """初始化数据库并写入固定演示数据"""
    keep_db = '--keep-db' in sys.argv

    print('数据库文件：', db_module.DB_PATH)

    # 确保表结构是最新的
    db_module.init_db()

    conn = db_module.get_db()
    try:
        if not keep_db:
            print('清空原有业务数据 ...')
            clear_data(conn)

        print('写入演示员工 ...')
        id_map = seed_employees(conn)
        print('写入演示打卡 ...')
        seed_checkins(conn, id_map)
        print('写入演示请假 ...')
        seed_leaves(conn, id_map)
        print('写入演示加班 ...')
        seed_overtimes(conn, id_map)
        conn.commit()

        print()
        print('演示数据已就绪：')
        print(f'  员工 {len(DEMO_EMPLOYEES)} 人（含 1 名已离职）')
        print(f'  打卡 {len(DEMO_CHECKINS)} 条（含 1 条缺下班卡）')
        print(f'  请假 {len(DEMO_LEAVES)} 条（待审批 / 已通过 / 已驳回各一）')
        print(f'  加班 {len(DEMO_OVERTIMES)} 条')
        print()
        print(f'工号到 ID 映射：{id_map}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
