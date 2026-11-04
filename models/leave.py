# 请假数据模型
# 负责请假申请记录的序列化
from dataclasses import dataclass


@dataclass
class Leave:
    """请假申请实体"""

    id: int
    employee_id: int
    leave_type: str
    start_date: str
    end_date: str
    days: int
    reason: str
    status: str
    approver: str
    approve_comment: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row):
        """从数据库查询结果构造请假对象"""
        return cls(
            id=row['id'],
            employee_id=row['employee_id'],
            leave_type=row['leave_type'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            days=row['days'],
            reason=row['reason'],
            status=row['status'],
            approver=row['approver'],
            approve_comment=row['approve_comment'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def to_dict(self):
        """转换为接口响应数据"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'leave_type': self.leave_type,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'days': self.days,
            'reason': self.reason,
            'status': self.status,
            'approver': self.approver,
            'approve_comment': self.approve_comment,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
