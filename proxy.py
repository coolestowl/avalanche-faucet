import time
import json
import requests

import config
import faucet


def get_51_proxy():
    for api in [config.PROXY_API]:
        try:
            resp = requests.get(api, headers={
                'User-Agent': config.USER_AGENT,
            }, timeout=(5, 5))
            obj = json.loads(resp.text)
            if len(obj['data']) > 0:
                item = obj['data'][0]
                return 'http://%s' % (item['ip'])
            else:
                faucet.debug_print('no proxy ip found, response:')
                faucet.debug_print(resp.text)

            time.sleep(1)
        except Exception as e:
            faucet.debug_print('get_51_proxy() ->', e)
            pass

    return ''


def proxy_is_ok(addr):
    if len(addr) == 0:
        return False
    try:
        faucet.debug_print('[INFO]', 'proxy test:', addr)

        urls = [
            # 'https://www.recaptcha.net/recaptcha/api.js',
            # 'https://www.gstatic.cn/recaptcha/releases/6MY32oPwFCn9SUKWt8czDsDw/recaptcha__en.js',
            'https://www.zhihu.com'
        ]
        for url in urls:
            resp = requests.get(url, proxies={'http': addr, 'https': addr}, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            }, timeout=(5, 5))
            if resp.status_code != 200:
                faucet.debug_print(
                    '[WARN]', 'status via proxy:', resp.status_code)
                return False
            faucet.debug_print('[pass]', url)
        return True
    except Exception as e:
        faucet.debug_print('[WARN]', 'proxy exception:', e)
        return False


proxy_provider = get_51_proxy  # get_zmhttp_proxy


def find_available_proxy():
    proxy_addr = proxy_provider()
    while not proxy_is_ok(proxy_addr):
        faucet.debug_print('[WARN]', 'bad proxy:', proxy_addr)
        proxy_addr = proxy_provider()
    return proxy_addr


def single_addr_task(addr, headless=False):
    proxy_addr = find_available_proxy()
    faucet.debug_print('[INFO]', 'addr:', addr, 'proxy:', proxy_addr)

    typ, msg = faucet.main(proxy=proxy_addr, addr=addr, headless=headless)
    while typ == 'err' or msg.__contains__('Captcha verification failed') or msg.__contains__('Network Error'):
        faucet.debug_print('[WARN]', 'bad proxy:', proxy_addr, msg)
        proxy_addr = find_available_proxy()
        typ, msg = faucet.main(proxy=proxy_addr, addr=addr, headless=headless)

    faucet.debug_print('[INFO]', msg, end='\n\n')
    return msg
