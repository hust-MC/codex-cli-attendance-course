# 员工数据模型
# 只负责数据结构和接口序列化
from dataclasses import dataclass


@dataclass
class Employee:
    """员工实体"""

    id: int
    name: str
    department: str
    employee_no: str
    phone: str
    status: str
    created_at: str

    @classmethod
    def from_row(cls, row):
        """从数据库查询结果构造员工对象"""
        return cls(
            id=row['id'],
            name=row['name'],
            department=row['department'],
            employee_no=row['employee_no'],
            phone=row['phone'] if 'phone' in row.keys() else None,
            status=row['status'] if 'status' in row.keys() else 'active',
            created_at=row['created_at'],
        )

    def to_dict(self):
        """转换为接口响应数据"""
        return {
            'id': self.id,
            'name': self.name,
            'department': self.department,
            'employee_no': self.employee_no,
            'phone': self.phone,
            'status': self.status,
            'created_at': self.created_at,
        }
