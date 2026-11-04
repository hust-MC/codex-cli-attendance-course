# 打卡数据模型
# 负责单条打卡记录的序列化
from dataclasses import dataclass


@dataclass
class Checkin:
    """打卡记录实体"""

    id: int
    employee_id: int
    check_type: str
    check_time: str
    location: str
    remark: str

    @classmethod
    def from_row(cls, row):
        """从数据库查询结果构造打卡对象"""
        return cls(
            id=row['id'],
            employee_id=row['employee_id'],
            check_type=row['check_type'],
            check_time=row['check_time'],
            location=row['location'] if 'location' in row.keys() else None,
            remark=row['remark'] if 'remark' in row.keys() else None,
        )

    def to_dict(self):
        """转换为接口响应数据"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'check_type': self.check_type,
            'check_time': self.check_time,
            'location': self.location,
            'remark': self.remark,
        }
