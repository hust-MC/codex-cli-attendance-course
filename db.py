# 数据库模块
# 负责 SQLite 连接、建表、索引和初始化
import os
import sqlite3
from pathlib import Path


# 默认数据库位于项目根目录，测试时可通过环境变量切换
DEFAULT_DB_PATH = Path(__file__).parent / 'checkin.db'
DB_PATH = Path(os.environ.get('CHECKIN_DB_PATH', DEFAULT_DB_PATH))

# 请假类型是固定的四种，不允许前端自由输入
LEAVE_TYPES = ('事假', '病假', '年假', '调休')

# 请假和加班共用同一套审批状态机
APPLICATION_STATUSES = ('pending', 'approved', 'rejected')

# 员工在职状态，删除按钮执行的是逻辑离职
EMPLOYEE_STATUSES = ('active', 'quit')


def get_db():
    """获取数据库连接并启用外键约束"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def _ensure_column(conn, table, column, column_ddl):
    """给已存在的表补字段，保证旧数据库可以平滑升级到当前结构"""
    existing = {row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    if column in existing:
        return
    conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {column_ddl}')


def _create_employees(conn):
    """创建员工表，并为历史库补齐新增字段"""
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS employees (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            department  TEXT    NOT NULL,
            employee_no TEXT    NOT NULL UNIQUE,
            phone       TEXT,
            status      TEXT    NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active', 'quit')),
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        '''
    )
    _ensure_column(conn, 'employees', 'phone', 'TEXT')
    _ensure_column(conn, 'employees', 'status', "TEXT NOT NULL DEFAULT 'active'")


def _create_checkins(conn):
    """创建打卡表，唯一索引兜底同一天同类型重复打卡"""
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS checkins (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            check_type  TEXT    NOT NULL CHECK(check_type IN ('in', 'out')),
            check_time  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            location    TEXT,
            remark      TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
        '''
    )
    _ensure_column(conn, 'checkins', 'location', 'TEXT')
    _ensure_column(conn, 'checkins', 'remark', 'TEXT')
    conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_checkins_employee_time
        ON checkins(employee_id, check_time)
        '''
    )
    conn.execute(
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_checkins_employee_type_day
        ON checkins(employee_id, check_type, date(check_time))
        '''
    )


def _create_leaves(conn):
    """创建请假申请表，按员工和日期区间支持冲突查询"""
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS leaves (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id    INTEGER NOT NULL,
            leave_type     TEXT    NOT NULL CHECK(leave_type IN ('事假', '病假', '年假', '调休')),
            start_date     TEXT    NOT NULL,
            end_date       TEXT    NOT NULL,
            days           INTEGER NOT NULL,
            reason         TEXT,
            status         TEXT    NOT NULL DEFAULT 'pending'
                           CHECK(status IN ('pending', 'approved', 'rejected')),
            approver       TEXT,
            approve_comment TEXT,
            created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
        '''
    )
    conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_leaves_employee_range
        ON leaves(employee_id, start_date, end_date)
        '''
    )


def _create_overtimes(conn):
    """创建加班申请表，日期加员工维度唯一"""
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS overtimes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id     INTEGER NOT NULL,
            work_date       TEXT    NOT NULL,
            hours           REAL    NOT NULL CHECK(hours > 0 AND hours <= 24),
            reason          TEXT,
            status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending', 'approved', 'rejected')),
            approver        TEXT,
            approve_comment TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
        '''
    )
    conn.execute(
        '''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_overtimes_employee_date
        ON overtimes(employee_id, work_date)
        '''
    )


def init_db():
    """创建全部业务表和索引，重复执行保持幂等"""
    conn = get_db()
    try:
        _create_employees(conn)
        _create_checkins(conn)
        _create_leaves(conn)
        _create_overtimes(conn)
        conn.commit()
    finally:
        conn.close()
