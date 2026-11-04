# 加班数据模型
# 负责加班申请记录的序列化
from dataclasses import dataclass


@dataclass
class Overtime:
    """加班申请实体"""

    id: int
    employee_id: int
    work_date: str
    hours: float
    reason: str
    status: str
    approver: str
    approve_comment: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row):
        """从数据库查询结果构造加班对象"""
        return cls(
            id=row['id'],
            employee_id=row['employee_id'],
            work_date=row['work_date'],
            hours=row['hours'],
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
            'work_date': self.work_date,
            'hours': self.hours,
            'reason': self.reason,
            'status': self.status,
            'approver': self.approver,
            'approve_comment': self.approve_comment,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
