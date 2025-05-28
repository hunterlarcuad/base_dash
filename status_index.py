from enum import IntEnum, auto


class StatusIndex(IntEnum):
    """状态索引枚举类，用于跟踪账户余额和交易信息"""
    def _generate_next_value_(self, start, count, last_values):
        return count

    ACCOUNT = auto()       # 账户名
    STATUS = auto()        # 状态
    BAL_CHAIN_USD_POST = auto()  # 链总余额(后)
    BAL_CHAIN_USD_PRE = auto()  # 链总余额(前)
    BAL_ETH_POST = auto()  # Base ETH 余额(后)
    BAL_USD_POST = auto()  # Base USD 余额(后)
    BAL_ETH_PRE = auto()   # Base ETH 余额(前)
    BAL_USD_PRE = auto()   # Base USD 余额(前)
    TX_TYPE = auto()       # 交易类型
    TX_AMOUNT = auto()     # 交易金额
    TX_CCY = auto()        # 交易币种
    TX_DATE = auto()       # 交易日期
    UPDATE_TIME = auto()   # 更新时间

    @classmethod
    def get_header(cls) -> str:
        """获取状态CSV文件的表头"""
        return (
            'account,status,bal_chain_usd_post,bal_chain_usd_pre,'
            'bal_eth_post,bal_usd_post,bal_eth_pre,bal_usd_pre,'
            'tx_type,tx_amount,tx_ccy,tx_date,update_time'
        )

    @classmethod
    def get_field_count(cls) -> int:
        """获取字段总数"""
        return len(cls)
