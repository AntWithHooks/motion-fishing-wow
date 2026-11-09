"""Safe live connection test: no keyboard events or in-game actions."""
from __future__ import annotations
import time
from phyphox_client import Phyphox
from settings_store import load


def main():
    print('Motion Fishing 0.7 | Проверка Acceleration and Attitude')
    address = load().get('url', '').strip()
    if not address:
        address = input('Адрес phyphox (http://...): ').strip()
    else:
        print('Адрес из настроек:', address)
    try:
        p = Phyphox(address)
        title = p.check()
        print('Эксперимент:', title)
        print('Двигай iPhone в течение 8 секунд. Данные только читаются.')
        count = 0
        measuring = False
        end = time.monotonic() + 8
        while time.monotonic() < end:
            samples, measuring, _ = p.samples()
            count += len(samples)
            if samples:
                _, world, _ = samples[-1]
                print('Показание: t=%.2f  a_world=(%+.2f, %+.2f, %+.2f)' % world)
            time.sleep(.12)
        print('Синхронизированных показаний:', count)
        print('phyphox:', 'Play включён' if measuring else 'Play выключен')
        if count == 0:
            print('Нет синхронизированных данных. Проверь Play, Remote Access, работу обоих графиков '
                  'и подключение iPhone и Windows к одной локальной Wi-Fi сети.')
        else:
            print('OK. Можно запускать START.bat и переобучать жесты в режиме «Локальный ноль».')
    except Exception as e:
        print('Ошибка:', e)


if __name__ == '__main__':
    main()
