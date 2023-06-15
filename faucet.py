import time
import json

# python3.10 -m pip install selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import config


def default_option():
    opt = webdriver.ChromeOptions()
    opt.add_experimental_option('excludeSwitches', ['enable-automation'])
    opt.add_argument('--disable-blink-features=AutomationControlled')
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    opt.add_argument('--user-data-dir=/tmp/data')
    return opt


def new_option(proxy='', headless=False, user_agent=''):
    opt = default_option()
    if len(proxy) > 0:
        opt.add_argument('--proxy-server=%s' % proxy)
    if headless:
        opt.add_argument('--headless')
        opt.add_argument('--disable-gpu')
    if len(user_agent) > 0:
        opt.add_argument('--user-agent=%s' % user_agent)
    return opt


def open_target_page(hins):
    hins.get('https://core.app/tools/testnet-faucet/?token=C')


def debug_print(*msg, **kw):
    if config.DEBUG:
        print(*msg, **kw)


def debug_screenshot(inst, filename):
    if config.DEBUG:
        inst.save_screenshot(filename)


def try_find_xpath_text(inst, path):
    try:
        elem = inst.find_element(By.XPATH, path)
        if len(elem.text) > 0:
            return elem.text
        return elem.get_attribute('title')
    except Exception as e:
        return 'Xpath Exception'


def wait_requests(inst, urls):
    try:
        all_items = []
        logs = inst.get_log('performance')
        for log in logs:
            obj = json.loads(log['message'])
            if obj['message']['method'] != 'Network.responseReceived':
                continue

            resp = obj['message']['params']['response']
            if resp['url'].startswith('chrome://'):
                continue

            all_items.append({'status': resp['status'], 'url': resp['url']})

        for expected in urls:
            found = False
            for each in all_items:
                if each['status'] == 200 and each['url'].startswith(expected):
                    found = True
            if not found:
                debug_print('not loaded: ' + expected)
                return False
        return True
    except Exception as _:
        return False


def main(proxy='', addr='', headless=False):
    debug_print('init')

    opt = new_option(proxy=proxy, headless=headless,
                     user_agent=config.USER_AGENT)
    desire_opt = webdriver.DesiredCapabilities.CHROME.copy()
    desire_opt['goog:loggingPrefs'] = {'performance': 'ALL'}
    if config.REMOTE_DRIVER:
        chrome = webdriver.Remote(
            command_executor=config.REMOTE_DRIVER_URL, options=opt, desired_capabilities=desire_opt)
    else:
        chrome = webdriver.Chrome(
            options=opt, desired_capabilities=desire_opt)

    chrome.set_window_size(1296, 810)

    wait_urls = [
        'https://www.recaptcha.net/recaptcha/api.js',
        'https://www.gstatic.cn/recaptcha/releases/',
        'https://www.recaptcha.net/recaptcha/api2/anchor',
    ]

    while True:
        try:
            debug_print('open site')
            open_target_page(chrome)
            time.sleep(6)

            page_loaded, retry = False, config.LOAD_PAGE_RETRY
            while not page_loaded and retry > 0:
                if wait_requests(chrome, wait_urls):
                    page_loaded = True
                else:
                    debug_print('resources load failed, refresh')
                    chrome.refresh()
                    retry -= 1
                    time.sleep(6)

            debug_print('screenshot aa.png')
            debug_screenshot(chrome, 'aa.png')

            recaptcha_frame = try_find_xpath_text(
                chrome, '/html/body/div[3]/div/div[1]/iframe')
            debug_print('captcha text: ' + recaptcha_frame)

            debug_print('find input tag')
            input_tag = chrome.find_element(
                By.XPATH, '/html/body/div[1]/div[5]/div/div[3]/div/div/div[1]/div/div[1]/div/div[3]/div/div/div/div[1]/div/input')

            debug_print('click input tag')
            ActionChains(chrome).click(input_tag)
            time.sleep(0.5)

            debug_print('input address')
            input_tag.send_keys(addr)
            time.sleep(1)

            debug_print('press send button')
            send_button = chrome.find_element(
                By.XPATH, '/html/body/div[1]/div[5]/div/div[3]/div/div/div[1]/div/div[1]/div/div[3]/div/div/div/button')
            send_button.click()
            time.sleep(6)

            debug_print('screenshot bb.png')
            debug_screenshot(chrome, 'bb.png')

            debug_print('find result')

            ret = ()
            success_text = try_find_xpath_text(
                chrome, '/html/body/div[1]/div[5]/div/div[3]/div/div/div[1]/div/div[1]/div/div[4]/div/div/div/div/div[2]/div[2]/a')
            if len(success_text) > 0:
                ret = ('success', success_text)
            else:
                failed_text = try_find_xpath_text(
                    chrome, '/html/body/div[1]/div[5]/div/div[3]/div/div/div[1]/div/div[1]/div/div[3]/div/div/div/span')
                ret = ('fail', failed_text)

            chrome.quit()
            return ret
        except Exception as e:
            chrome.quit()
            return ('err', e)
    # loop


if __name__ == '__main__':
    main('', addr='', headless=False)
