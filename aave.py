import os  # noqa
import sys  # noqa
import argparse
import random
import time
import copy
import pdb  # noqa
import shutil
import math
import re  # noqa
from datetime import datetime, timedelta  # noqa
from DrissionPage._elements.none_element import NoneElement

# 添加 commonoplib 到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'commonoplib'))

from fun_utils import (
    ding_msg,
    load_file,
    save2file,
    format_ts,
)
from fun_okx import OkxUtils
from fun_dp import DpUtils
from base_conf import (
    DEF_USE_HEADLESS,
    DEF_DEBUG,
    DEF_PATH_USER_DATA,
    DEF_NUM_TRY,
    DEF_DING_TOKEN,
    DEF_PATH_DATA_STATUS,
    DEF_FILE_STATUS,
    DEF_FILE_STATUS_HISTORY,
    DEF_URL_AAVE,
    DEF_BALANCE_KEEP_GAS_ETH,
    DEF_SUPPLY_MIN_ETH,
    DEL_PROFILE_DIR,
    DEF_INSUFFICIENT_ETH,
    DEF_SUCCESS,
    DEF_FAIL,
    DEF_TX_CCY_ETH,
    DEF_TX_TYPE_SUPPLY,
    FILENAME_LOG,
    logger,
)
from status_index import StatusIndex

# gm Check-in use UTC Time
TZ_OFFSET = 0

"""
2025.05.27
"""


class ClsAave():
    def __init__(self) -> None:
        self.args = None

        self.file_status = None

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}
        self.dic_account = {}

        self.inst_okx = OkxUtils()
        self.inst_dp = DpUtils()

        self.inst_dp.plugin_yescapcha = False
        self.inst_dp.plugin_capmonster = False
        self.inst_dp.plugin_okx = True

        # 使用枚举类定义的状态索引
        self.status_index = StatusIndex
        self.DEF_HEADER_STATUS = self.status_index.get_header()
        self.FIELD_NUM = self.status_index.get_field_count()

    def set_args(self, args):
        self.args = args
        self.is_update = False

    def __del__(self):
        pass

    def get_status_file(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/{DEF_FILE_STATUS}'
        self.file_status_history = f'{DEF_PATH_DATA_STATUS}/{DEF_FILE_STATUS_HISTORY}'

    def status_load(self):
        if self.file_status is None:
            self.get_status_file()

        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=self.DEF_HEADER_STATUS
        )

    def status_save(self):
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=self.DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.browser:
                try:
                    self.browser.quit()
                except Exception as e: # noqa
                    # logger.info(f'[Close] Error: {e}')
                    pass

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def save_screenshot(self, name):
        tab = self.browser.latest_tab
        # 对整页截图并保存
        # tab.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        tab.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def is_task_complete(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        if s_profile not in self.dic_status:
            return False

        claimed_date = self.dic_status[s_profile][idx_status]
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET) # noqa
        if date_now != claimed_date:
            return False
        else:
            return True

    def update_status(self, idx_status, s_value):
        update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        def init_status():
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
            ]
            # 确保列表长度足够容纳所有索引
            for i in range(1, self.status_index.get_field_count()):
                self.dic_status[self.args.s_profile].append('')

        if self.args.s_profile not in self.dic_status:
            init_status()
        if len(self.dic_status[self.args.s_profile]) != self.status_index.get_field_count():
            init_status()
        if self.dic_status[self.args.s_profile][idx_status] == s_value:
            return

        self.dic_status[self.args.s_profile][idx_status] = s_value
        self.dic_status[self.args.s_profile][
            self.status_index.UPDATE_TIME.value
        ] = update_time

        self.status_save()
        self.is_update = True

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == self.FIELD_NUM:
            try:
                # s_val = int(lst_pre[idx_status])
                s_val = lst_pre[idx_status]
            except: # noqa
                pass

        return s_val

    def update_date(self, idx_status, update_ts=None):
        if not update_ts:
            update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        claim_date = update_time[:10]

        self.update_status(idx_status, claim_date)

    def connect_wallet(self):
        n_tab = self.browser.tabs_count
        for i in range(1, DEF_NUM_TRY+1):
            tab = self.browser.latest_tab

            ele_blk = tab.ele(
                '@@tag()=header@@class:MuiBox-root',
                timeout=2
            )
            if not isinstance(ele_blk, NoneElement):
                lst_path = [
                    '@@tag()=button@@class:MuiButtonBase-root MuiButton-root MuiButton-gradient MuiButton-gradientPrimary MuiButton-sizeMedium MuiButton-gradientSizeMedium MuiButton-colorPrimary MuiButton-disableElevation MuiButton-root MuiButton-gradient MuiButton-gradientPrimary MuiButton-sizeMedium MuiButton-gradientSizeMedium MuiButton-colorPrimary MuiButton-disableElevation css', # before login
                    '@@tag()=p@@class:MuiTypography-root MuiTypography-buttonM', # after login
                ]
                ele_btn = self.inst_dp.get_ele_btn(ele_blk, lst_path)
                if ele_btn is not NoneElement:
                    s_info = ele_btn.text
                    self.logit(None, f'Connect Wallet Button Text: {s_info}')
                    if s_info == 'Connect wallet':
                        try:
                            ele_btn.wait.enabled(timeout=5)
                            if ele_btn.wait.clickable(timeout=5):
                                ele_btn.click(by_js=True)
                                tab.wait(1)
                        except Exception as e:  # noqa
                            continue

                        ele_btn = tab.ele(
                            '@@tag()=span@@text()=OKX Wallet',
                            timeout=2
                        )
                        if not isinstance(ele_btn, NoneElement):
                            if ele_btn.wait.clickable(timeout=5):
                                ele_btn.click(by_js=True)

                        if self.inst_okx.wait_popup(n_tab+1, 10):
                            tab.wait(2)
                            self.inst_okx.okx_connect()
                            self.inst_okx.wait_popup(n_tab, 10)
                            tab.wait(2)
                    else:
                        self.logit(None, 'Log in success')
                        return True

        return False

    def select_base_market(self):
        for i in range(1, DEF_NUM_TRY+1):
            tab = self.browser.latest_tab
            lst_path = [
                '@@tag()=h1@@text():Market',
                '@@tag()=h1@@text():Instance',
            ]
            ele_btn = self.inst_dp.get_ele_btn(tab, lst_path)
            if ele_btn is not NoneElement:
                s_text = ele_btn.text
                self.logit(None, f'Market: {s_text}')
                if s_text == 'Base Market':
                    return True
                else:
                    self.logit(None, f'Market is not Base Market: {s_text}')
                    ele_btn = tab.ele(
                        '@@tag()=svg@@class=MuiSvgIcon-root '
                        'MuiSvgIcon-fontSizeMedium css-fo7h32',
                        timeout=2
                    )
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click()
                        tab.wait(1)

                        # Select item: Base Market
                        ele_btn = tab.ele(
                            '@@tag()=span@@text():Base',
                            timeout=2
                        )
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click()
                            tab.wait(1)
                            continue

            self.logit(None, f'Market is not found: {i}/{DEF_NUM_TRY}')
            self.browser.wait(1)

        return False

    def supply_ok_close(self, max_wait_sec=10):
        for i in range(1, max_wait_sec+1):
            tab = self.browser.latest_tab
            ele_btn = tab.ele('@@tag()=button@@text()=Ok, Close', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit(None, 'Click Supply OK Close Button')
                tab.wait(1)
                return True
            self.logit(None, f'Supply OK Close: {i}/{max_wait_sec}')
            self.browser.wait(1)
        return False

    def supply_base(self):
        n_tab = self.browser.tabs_count
        for i in range(1, DEF_NUM_TRY+1):
            tab = self.browser.latest_tab
            ele_blk = tab.ele(
                '@@tag()=div@@class:MuiPaper-root '
                'MuiPaper-elevation@@text():Assets to supply',
                timeout=2
            )
            if not isinstance(ele_blk, NoneElement):
                # 点击 Supply 按钮
                ele_btn = ele_blk.ele(
                    '@@tag()=button@@text()=Supply',
                    timeout=2
                )
                if not isinstance(ele_btn, NoneElement):
                    s_info = ele_btn.text
                    self.logit(None, f'Supply Button Text: {s_info}')

                    try:
                        ele_btn.wait.enabled(timeout=5)
                        if ele_btn.wait.clickable(timeout=5):
                            ele_btn.click(by_js=True)
                            tab.wait(1)
                    except Exception as e:  # noqa
                        continue

                # Supply ETH
                # Please switch to Base.
                ele_btn = tab.ele(
                    '@@tag()=p@@class:MuiTypography-root'
                    '@@text()=Switch Network',
                    timeout=2
                )
                if not isinstance(ele_btn, NoneElement):
                    s_info = ele_btn.text
                    self.logit(None, f'Please switch to Base: {s_info}')
                    ele_btn.click(by_js=True)
                    tab.wait(1)

                # Wallet balance
                ele_amount_blk = tab.ele('.MuiBox-root css-1wecvon', timeout=2)
                if not isinstance(ele_amount_blk, NoneElement):
                    ele_balance = ele_amount_blk.ele(
                        '.MuiTypography-root MuiTypography-secondary12 '
                        'MuiTypography-noWrap css-cyw6g5',
                        timeout=2
                    )
                    if not isinstance(ele_balance, NoneElement):
                        s_info = ele_balance.text
                        self.logit(None, f'Wallet balance: {s_info}')
                        try:
                            f_balance = float(s_info)
                        except:  # noqa
                            f_balance = -1
                            pass

                        # f_amount = f_balance - DEF_BALANCE_KEEP_GAS_ETH
                        # f_balance 是预留 gas 后的余额
                        # f_balance 保留 5 位小数，向下取整
                        f_amount = math.floor(f_balance * 100000) / 100000
                        if f_amount < DEF_SUPPLY_MIN_ETH:
                            self.logit(
                                None,
                                f'Insufficient ETH balance: {f_balance}'
                            )
                            self.update_status(
                                self.status_index.STATUS,
                                DEF_INSUFFICIENT_ETH
                            )
                            return DEF_INSUFFICIENT_ETH

                        # Input Amount
                        ele_input = ele_amount_blk.ele('@@tag()=input@@inputmode=numeric', timeout=2)
                        if not isinstance(ele_input, NoneElement):
                            ele_input.click.multi(times=2)
                            tab.wait(1)
                            ele_input.clear(by_js=True)
                            tab.wait(1)
                            tab.actions.move_to(ele_input).click().type(str(f_amount)) # noqa
                            tab.wait(1)
                            if ele_input.value != str(f_amount):
                                self.logit(None, f'Input amount error: {ele_input.value} != {f_amount}')
                                continue

                        # Submit: Supply ETH
                        ele_btn = tab.ele('@@tag()=button@@text()=Supply ETH', timeout=2)
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            tab.wait(1)
                            if self.inst_okx.wait_popup(n_tab+1, 10):
                                tab.wait(2)
                                self.inst_okx.okx_confirm()
                                self.inst_okx.wait_popup(n_tab, 10)
                                self.update_status(self.status_index.TX_TYPE, DEF_TX_TYPE_SUPPLY)
                                self.update_status(self.status_index.TX_AMOUNT, f_amount)
                                self.update_status(self.status_index.TX_CCY, DEF_TX_CCY_ETH)
                                self.update_status(self.status_index.TX_DATE, format_ts(time.time(), style=1, tz_offset=TZ_OFFSET))
                                self.update_status(
                                    self.status_index.STATUS,
                                    DEF_SUCCESS
                                )
                                tab.wait(3)
                                return DEF_SUCCESS

                        self.update_status(
                            self.status_index.TX_DATE,
                            format_ts(
                                time.time(),
                                style=1,
                                tz_offset=TZ_OFFSET
                            )
                        )

        return DEF_FAIL

    def get_supply_amount(self):
        f_supply_amount = 0
        tab = self.browser.latest_tab

        ele_blk = tab.ele('.MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation1 css-133srx4', timeout=2)
        if not isinstance(ele_blk, NoneElement):
            ele_info = ele_blk.ele('.MuiBox-root css-1dm56o2', timeout=2)
            if not isinstance(ele_info, NoneElement):
                # Balance $16.14 APY 1.86% Collateral $16.14
                s_info = ele_info.text.replace('\n', ' ')
                self.logit(None, f'Your supplies: {s_info}')
            ele_info = ele_blk.ele('@@tag()=p@@data-cy=nativeAmount', timeout=2)
            if not isinstance(ele_info, NoneElement):
                # eg: 0.0061176
                s_info = ele_info.text
                self.logit('get_supply_amount', f'ETH Amount: {s_info}')
                f_supply_amount = float(s_info)
        return f_supply_amount

    # collect data from browser
    def collect_data_option(self, max_wait_sec=1):
        for i in range(1, max_wait_sec+1):
            tab = self.browser.latest_tab
            ele_btn = tab.ele('@@tag()=p@@text()=Opt-out', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit('collect_data_option', 'Click Opt-out Button')
                tab.wait(1)
                return True
            if max_wait_sec > 1:
                self.browser.wait(1)
        return False

    def aave_process(self):
        # open Aave url
        # tab = self.browser.latest_tab
        # tab.get(self.args.url)
        tab = self.browser.new_tab(DEF_URL_AAVE)
        tab.wait.doc_loaded()
        # tab.wait(3)
        # tab.set.window.max()

        if self.args.set_window_size == 'max':
            # 判断窗口是否是最大化
            if tab.rect.window_state != 'maximized':
                # 设置浏览器窗口最大化
                tab.set.window.max()
                self.logit(None, 'Set browser window to maximize')

        # Connect wallet
        if self.connect_wallet() is False:
            self.logit('aave_process', 'Connect wallet failed')
            return False
        self.logit(None, 'Connect wallet success')

        if self.select_base_market() is False:
            self.logit('aave_process', 'Select base market failed')
            return False
        self.collect_data_option()

        if self.args.tx_type == 'supply':
            self.update_balance(s_pre_or_post='pre')
            if self.supply_base() == DEF_SUCCESS:
                self.update_balance(s_pre_or_post='post')
                return True
        elif self.args.tx_type == 'withdraw':
            pass
        elif self.args.tx_type == 'auto':
            f_supply_amount = self.get_supply_amount()
            if f_supply_amount > 0:
                self.logit(None, f'Your supplies [ETH]: {f_supply_amount}')
            else:
                self.update_balance(s_pre_or_post='pre')
                if self.supply_base() == DEF_SUCCESS:
                    self.supply_ok_close()
                    self.update_balance(s_pre_or_post='post')
                    return True
        else:
            self.logit(None, f'Invalid tx type: {self.args.tx_type}')
            return False

        return False

    def update_balance(self, s_pre_or_post='pre'):
        s_chain = 'Base'
        s_coin = 'BASE_ETH'
        tab = self.browser.new_tab()

        (s_bal_chain_usd, s_balance_coin, s_balance_usd) = self.inst_okx.get_balance_by_chain_coin(s_chain, s_coin)
        self.logit(None, f'Balance chain usd: {s_bal_chain_usd}')
        self.logit(None, f'Balance: {s_balance_coin} {s_balance_usd} [{s_chain}][{s_coin}]')
        if s_pre_or_post == 'pre':
            self.update_status(self.status_index.BAL_CHAIN_USD_PRE, s_bal_chain_usd)
            self.update_status(self.status_index.BAL_ETH_PRE, s_balance_coin)
            self.update_status(self.status_index.BAL_USD_PRE, s_balance_usd)
        else:
            self.update_status(self.status_index.BAL_CHAIN_USD_POST, s_bal_chain_usd)
            self.update_status(self.status_index.BAL_ETH_POST, s_balance_coin)
            self.update_status(self.status_index.BAL_USD_POST, s_balance_usd)
        tab.close()

    def aave_run(self):
        self.browser = self.inst_dp.get_browser(self.args.s_profile)

        self.inst_okx.set_browser(self.browser)

        if self.inst_okx.init_okx(is_bulk=True) is False:
            self.logit('aave_run', 'Init OKX failed')
            return False

        self.aave_process()

        if self.args.manual_exit:
            s_msg = 'Manual Exit. Press any key to exit! ⚠️' # noqa
            input(s_msg)

        self.logit('aave_run', 'Finished!')

        return True

    def save_to_history(self):
        """将当前 profile 对应的记录追加到 status_history"""
        if (hasattr(self, 'args') and hasattr(self, 'dic_status') and 
            hasattr(self, 'file_status_history') and self.is_update):
            if self.args.s_profile in self.dic_status:
                profile_status = {self.args.s_profile: self.dic_status[self.args.s_profile]}
                save2file(
                    file_ot=self.file_status_history,
                    dic_status=profile_status,
                    idx_key=0,
                    header=self.DEF_HEADER_STATUS,
                    mode='a'  # 追加模式
                )
                self.logit('save_to_history', f'Saved to history for {self.args.s_profile}')


def send_msg(inst_aave, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            lst_status = None
            if s_profile in inst_aave.dic_status:
                lst_status = inst_aave.dic_status[s_profile]

            if lst_status is None:
                lst_status = [s_profile, -1]

            s_info += '- {},{}\n'.format(
                s_profile,
                lst_status[inst_aave.status_index.TX_TYPE],
            )
        d_cont = {
            'title': 'Aave Task Finished! [Aave]',
            'text': (
                'Aave Task\n'
                '- account,task_status\n'
                '{}\n'
                .format(s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def show_msg(args):
    current_directory = os.getcwd()
    FILE_LOG = f'{current_directory}/{FILENAME_LOG}'
    FILE_STATUS = f'{current_directory}/{DEF_PATH_DATA_STATUS}/status.csv'

    print('########################################')
    print('The program is running')
    print(f'headless={args.headless}')
    print('Location of the running result file:')
    print(f'{FILE_STATUS}')
    print('The running process is in the log file:')
    print(f'{FILE_LOG}')
    print('########################################')


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    inst_aave = ClsAave()
    inst_aave.set_args(args)

    args.s_profile = 'ALL'
    inst_aave.inst_okx.set_args(args)
    inst_aave.inst_okx.purse_load(args.decrypt_pwd)

    # 检查 profile 参数冲突
    if args.profile and (args.profile_begin is not None or args.profile_end is not None):
        logger.info('参数 --profile 与 --profile_begin/--profile_end 不能同时使用！')
        sys.exit(1)

    if len(args.profile) > 0:
        items = args.profile.split(',')
    elif args.profile_begin is not None and args.profile_end is not None:
        # 生成 profile_begin 到 profile_end 的 profile 列表
        prefix = re.match(r'^[a-zA-Z]+', args.profile_begin).group()
        start_num = int(re.search(r'\d+', args.profile_begin).group())
        end_num = int(re.search(r'\d+', args.profile_end).group())
        num_width = len(re.search(r'\d+', args.profile_begin).group())
        items = [f"{prefix}{str(i).zfill(num_width)}" for i in range(start_num, end_num + 1)]
        logger.info(f'Profile list: {items}')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(inst_aave.inst_okx.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    def is_complete(lst_status):
        if args.force:
            return False

        b_ret = True
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)

        if lst_status:
            if len(lst_status) < inst_aave.FIELD_NUM:
                return False

            if args.only_gm:
                if date_now != lst_status[inst_aave.status_index.TX_DATE]:
                    b_ret = b_ret and False
            else:
                idx_status = inst_aave.status_index.TX_TYPE
                lst_status_ok = ['Activation Completed', 'Not enough ETH']
                if lst_status[idx_status] in lst_status_ok:
                    b_complete = True
                else:
                    b_complete = False
                b_ret = b_ret and b_complete

        else:
            b_ret = False

        return b_ret

    # 将已完成的剔除掉
    inst_aave.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in inst_aave.dic_status:
            lst_status = inst_aave.dic_status[s_profile]

            if is_complete(lst_status):
                n += 1
                profiles.pop(i)

        else:
            continue
    logger.info('#'*40)

    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa

        if percent > args.max_percent:
            logger.info(f'Progress is more than threshold {percent}% > {args.max_percent}% [{n}/{total}] [{s_profile}]')
            break

        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in inst_aave.inst_okx.dic_purse:
            logger.info(f'{s_profile} is not in okx account conf [ERROR]')
            sys.exit(0)

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                if j > 1:
                    logger.info(f'⚠️ 正在重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                inst_aave.set_args(args)
                inst_aave.inst_dp.set_args(args)
                inst_aave.inst_okx.set_args(args)

                if s_profile in inst_aave.dic_status:
                    lst_status = inst_aave.dic_status[s_profile]
                else:
                    lst_status = None

                if is_complete(lst_status):
                    logger.info(f'[{s_profile}] Last update at {lst_status[inst_aave.status_index.UPDATE_TIME]}') # noqa
                    break
                else:
                    b_ret = inst_aave.aave_run()
                    inst_aave.close()
                    if b_ret:
                        lst_success.append(s_profile)
                        break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                inst_aave.close()
                if j < max_try_except:
                    time.sleep(5)

        # 处理完当前 profile 后，保存到历史记录
        inst_aave.save_to_history()

        if inst_aave.is_update is False:
            continue

        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile} Finish]')
        if percent > args.max_percent:
            continue

        if len(profiles) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))

            # 输出下次执行时间，格式为 YYYY-MM-DD HH:MM:SS
            next_exec_time = datetime.now() + timedelta(seconds=sleep_time)
            logger.info(f'next_exec_time: {next_exec_time.strftime("%Y-%m-%d %H:%M:%S")}')
            time.sleep(sleep_time)

    send_msg(inst_aave, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    parser.add_argument(
        '--profile_begin', required=False, default=None,
        help='按指定的 profile 开始后缀(包含) eg: g01'
    )
    parser.add_argument(
        '--profile_end', required=False, default=None,
        help='按指定的 profile 结束后缀(包含) eg: g05'
    )

    parser.add_argument(
        '--decrypt_pwd', required=False, default='',
        help='decrypt password'
    )
    # 不使用 X
    parser.add_argument(
        '--no_x', required=False, action='store_true',
        help='Not use X account'
    )
    parser.add_argument(
        '--auto_like', required=False, action='store_true',
        help='Like a post after login automatically'
    )
    parser.add_argument(
        '--auto_appeal', required=False, action='store_true',
        help='Auto appeal when account is suspended'
    )
    parser.add_argument(
        '--force', required=False, action='store_true',
        help='Run ignore status'
    )
    parser.add_argument(
        '--manual_exit', required=False, action='store_true',
        help='Close chrome manual'
    )
    # 添加 --headless 参数
    parser.add_argument(
        '--headless',
        action='store_true',   # 默认为 False，传入时为 True
        default=False,         # 设置默认值
        help='Enable headless mode'
    )
    # 添加 --no-headless 参数
    parser.add_argument(
        '--no-headless',
        action='store_false',
        dest='headless',  # 指定与 --headless 参数共享同一个变量
        help='Disable headless mode'
    )
    parser.add_argument(
        '--get_task_status', required=False, action='store_true',
        help='Check task result'
    )
    # 添加 --max_percent 参数
    parser.add_argument(
        '--max_percent', required=False, default=100, type=int,
        help='[默认为 100] 执行的百分比'
    )
    parser.add_argument(
        '--only_gm', required=False, action='store_true',
        help='Only do gm checkin'
    )
    parser.add_argument(
        '--set_window_size', required=False, default='normal',
        help='[默认为 normal] 窗口大小，normal 为正常，max 为最大化'
    )
    parser.add_argument(
        '--tx_type', required=False, default='auto',
        help='tx type: auto, supply, withdraw'
    )

    args = parser.parse_args()
    show_msg(args)

    if args.only_gm:
        args.no_x = True
        logger.info('-'*40)
        logger.info('Only do gm checkin, set no_x=True')

    if args.loop_interval <= 0:
        main(args)
    elif len(args.profile) > 0:
        main(args)
    else:
        while True:
            main(args)

            if args.get_task_status:
                break

            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
# noqa
python aave.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python aave.py --profile=g95
"""
