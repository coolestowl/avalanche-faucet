import time
import datetime
import requests
import threading

from lxml import etree

import config
import faucet
import proxy


def get_last_transfer(from_addr, to_addr):
    try:
        resp = requests.get('https://testnet.snowtrace.io/address/%s?fromaddress=%s' %
                            (to_addr, from_addr), headers={'User-Agent': config.USER_AGENT}, proxies=config.SNOWTRACE_PROXY)
        faucet.debug_print(resp.status_code, len(resp.text))
        if len(resp.text) < 10000:
            time.sleep(30)
            return get_last_transfer(from_addr, to_addr)

        tx_tag = etree.HTML(resp.text).xpath(
            '/html/body/div[1]/main/div[4]/div[2]/div[2]/div/div[1]/div[2]/table/tbody/tr[1]/td[2]/a')
        time_tag = etree.HTML(resp.text).xpath(
            '/html/body/div[1]/main/div[4]/div[2]/div[2]/div/div[1]/div[2]/table/tbody/tr[1]/td[6]/span')
        return tx_tag[0].text, time_tag[0].attrib['title']
    except Exception as _:
        return '', ''


queue = []


def append_addr(addr, offset_mins=0):
    obj = {
        'addr': addr,
        'last': None,
        'tx': 'error',
        'wait': offset_mins,
    }

    (tx_hash, timestr) = get_last_transfer(config.FAUCET_ADDR, addr)
    if len(timestr) > 0:
        obj['last'] = datetime.datetime.strptime(
            timestr, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(hours=8) + datetime.timedelta(minutes=offset_mins)
        obj['tx'] = tx_hash
    else:
        obj['last'] = datetime.datetime.now() - datetime.timedelta(hours=24)

    queue.append(obj)
    pass


def next_event():
    until = queue[0]['last'] + \
        datetime.timedelta(hours=config.FAUCET_CD) - datetime.datetime.now()
    if until < datetime.timedelta(0):
        return 0
    return until.total_seconds()


def pop():
    # get and delete the first one of queue
    obj = queue[0]
    queue.remove(obj)
    return obj


def print_queue():
    faucet.debug_print('queue size: %d' % len(queue))
    for obj in queue:
        faucet.debug_print(obj['addr'], obj['last'], obj['tx'])
    faucet.debug_print()


def queue_to_slack():
    msg = ''
    for obj in queue:
        msg += '%s => %s ( %s\n' % (obj['addr']
                                    [:20], obj['tx'][:20], obj['last'])

    data = {
        'blocks': [{
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': 'addresses:'
            }
        }, {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '```%s```' % (msg)
            }
        }]
    }
    resp = requests.post(config.SLACK_WEBHOOK, json=data)
    faucet.debug_print('[slack]', resp.status_code, resp.text)


def slack_routine():
    while True:
        queue_to_slack()
        time.sleep(3600 * 4)


def main():
    for addr in config.ADDRS:
        append_addr(addr)
    queue.sort(key=lambda x: x['last'])

    x = threading.Thread(target=slack_routine)
    x.start()

    while True:
        print_queue()

        wait_secs = next_event()
        if wait_secs > 0:
            faucet.debug_print('last event at %s' % queue[0]['last'])
            faucet.debug_print('cd %d hours' % config.FAUCET_CD)
            faucet.debug_print('sleep %d seconds' % wait_secs)
            time.sleep(wait_secs)
            pass

        obj = pop()
        faucet.debug_print('task %s' % obj['addr'])

        wait_mins = task(obj)
        if obj['wait'] > 0:
            wait_mins += obj['wait']

        time.sleep(16 * 2)  # 2 secs / block, 16 blocks for confirmation
        append_addr(obj['addr'], offset_mins=wait_mins)
        queue.sort(key=lambda x: x['last'])


def task(obj):
    wait_mins = 0
    msg = proxy.single_addr_task(obj['addr'], headless=False)
    if msg.__contains__('Please try again after 1440 minutes'):
        wait_mins = 60*12
    return wait_mins


if __name__ == '__main__':
    main()
    pass
