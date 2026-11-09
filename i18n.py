"""English/Russian UI translation layer. Russian strings are the legacy source keys.

Language is a presentation preference only; IMU templates and recognition are unchanged.
"""
from __future__ import annotations
import re

LANGUAGE = 'en'


def set_language(language: str) -> None:
    global LANGUAGE
    if language not in ('ru', 'en'):
        raise ValueError('Unsupported language')
    LANGUAGE = language


# Full/static UI phrases. Keep these readable so contributors can maintain both languages.
EN = {
    'Motion Fishing • Мастерская рыболова': "Motion Fishing • Fisher's Workshop",
    'МАСТЕРСКАЯ РЫБОЛОВА    •    iPHONE   /   WI-FI   /   WoW FOREVER': 'FISHER\'S WORKSHOP    •    iPHONE   /   WI-FI   /   WoW FOREVER',
    'СОЕДИНЕНИЕ': 'CONNECTION',
    'ПРИЧАЛ': 'DOCK', 'ШКОЛА ЖЕСТОВ': 'GESTURE TRAINING', 'НАСТРОЙКИ': 'SETTINGS', 'ЖУРНАЛ': 'EVENT LOG',
    'ДЕЙСТВИЯ — ТОЛЬКО ПО ЖЕСТУ': 'ONE ACTION PER GESTURE',
    'Забрасывай удочку. Почувствуй подсечку.': 'Cast your line. Feel the strike.',
    'Физический контроллер на основе iPhone. Без автоловли и распознавания поклёвок.': 'Use your iPhone as a motion controller. No automatic fishing or bite detection.',
    '01  •  СВЯЗЬ С УДОЧКОЙ': '01  •  CONNECT YOUR ROD',
    'Подключи iPhone и ПК к одной локальной сети (Wi-Fi; ПК может быть по кабелю). Вставь адрес Remote Access из phyphox.': 'Connect your iPhone and PC to the same local network (the PC can use Ethernet). Enter the Remote Access address shown in phyphox.',
    'АДРЕС PHYphox': 'PHYPHOX ADDRESS',
    'ПОДКЛЮЧИТЬ': 'CONNECT', 'Отключить': 'Disconnect',
    'КАК ПОДКЛЮЧИТЬ ПО WI-FI?': 'HOW TO CONNECT OVER WI-FI?',
    'Датчик:  ': 'Sensor:  ',
    '    •    Данные сохраняются в папке profiles рядом с программой': '    •    Settings are stored in the profiles folder next to the app',
    '02  •  УПРАВЛЕНИЕ ЗАБРОСОМ': '02  •  FISHING CONTROLS',
    'Для WoW используй ту же клавишу, которую назначил в аддоне рыбалки (например, F8).': 'Select the same key you assigned in your WoW fishing addon (for example, F8).',
    'Клавиша': 'Key', 'Отправлять только в активное окно WoW': 'Send keys only when WoW is active',
    'СБРОС К ЗАБРОСУ': 'RESET TO CAST', 'ОТПРАВКА КЛАВИШ В ИГРУ': 'SEND KEYS TO GAME',
    'Отправка клавиш включена при запуске. Для тренировки выключи её вручную.': 'Key sending is enabled at launch. Turn it off when testing or training gestures.',
    '03  •  ПОСЛЕДНЕЕ ДВИЖЕНИЕ': '03  •  LAST MOTION',
    'CAST → F8 → ожидание поклёвки → HOOK → F8 → CAST': 'CAST → F8 → wait for a bite → HOOK → F8 → CAST',
    'Твои движения — твои правила': 'Your movements. Your rules.',
    'Запиши 5–8 естественных повторов каждого жеста. CAST: назад → вперёд; HOOK: рывок к себе без поворота кисти. Для записи одного движения нажми кнопку, выжди секунду и взмахни.': 'Record 5–8 natural repetitions of each gesture. CAST: back → forward; HOOK: pull toward yourself without twisting the wrist. Click Record, wait one second, and make one movement.',
    'ЗАБРОС': 'CAST', 'ПОДСЕЧКА': 'HOOK', 'НЕ ДЕЙСТВИЕ': 'IGNORE / NEGATIVE',
    'ПОДСЕЧКУ': 'HOOK', 'НЕЖЕЛАТЕЛЬНОЕ ДВИЖЕНИЕ': 'NEGATIVE',
    'Обязательно: движение назад → разворот → движение вперёд. Один взмах не будет сохранён.': 'Required: move backward, reverse, then move forward. A single forward swing is not saved.',
    'Рывок К СЕБЕ без пронации/супинации. Поворот кисти не должен вызывать HOOK.': 'A pull TOWARD YOU without pronating or supinating the wrist. Wrist rotation must not trigger HOOK.',
    'Запиши 5–8 движений, которые должны игнорироваться: пронация, супинация, поправить телефон в руке.': 'Record 5–8 movements to ignore: pronation, supination, readjusting your phone, etc.',
    'ЗАПИСАТЬ ПРИМЕР': 'RECORD EXAMPLE', 'Удалить последний': 'Remove last',
    'Очистить заброс': 'Clear CAST', 'Очистить подсечка': 'Clear HOOK', 'Очистить не действие': 'Clear NEGATIVE',
    '•  ОЦЕНКА ОБУЧЕНИЯ': '•  TRAINING QUALITY',
    'Один алгоритм: ускорение и вращение в координатах начала жеста. Старые версии жестов не загружаются: переобучи CAST/HOOK, затем добавь отрицательные движения.': 'One IMU method: acceleration and rotation relative to the gesture start. Legacy gesture formats are not used; retrain CAST/HOOK and add negative examples.',
    'ОЧИСТИТЬ ВСЕ ПРИМЕРЫ': 'CLEAR ALL EXAMPLES',
    '•  ПРЕСЕТ ДЛЯ GITHUB': '•  SHARE A GITHUB PRESET',
    'Настройки и примеры жестов хранятся в папке profiles рядом с приложением. Создай общий пресет для новых игроков после обучения. Адрес phyphox не публикуется.': 'Settings and gesture examples live in the profiles folder beside the app. Create a shared preset after training. Your phyphox address is never included.',
    'СОХРАНИТЬ МОИ ЖЕСТЫ В ОБЩИЙ ПРЕСЕТ': 'PUBLISH MY GESTURES AS A DEFAULT PRESET',
    'Файл profiles/default.json можно загрузить в GitHub. Личные изменения сохраняются отдельно в profiles/settings.json.': 'Commit profiles/default.json to GitHub. Personal changes are saved separately in profiles/settings.json.',
    'Точная настройка снасти': 'Fine-tune your fishing rod',
    'Изменения сразу применяются и сохраняются. Проверяй результат на вкладке «Журнал».': 'Changes take effect immediately and are saved automatically. Check results in the Event Log.',
    '•  ЕДИНЫЙ МЕТОД: IMU / ЛОКАЛЬНЫЙ НОЛЬ': '•  ONE METHOD: IMU / LOCAL ZERO',
    'Ускорение пересчитывается относительно начальной ориентации телефона. Attitude используется также для измерения вращения. Нет режимов фиксированного хвата, глобальных осей и сравнения только модуля ускорения.': 'Acceleration is transformed relative to the phone orientation at the start of each gesture. Attitude also measures rotation. No fixed-grip, world-axis, or acceleration-magnitude-only modes.',
    'Нельзя независимо определить направление «к телу» при произвольном хвате. Обучай HOOK в привычном хвате; во время обучения порог ускорения снижен вдвое. Если пример записан с предупреждением, проверь настройки фильтра.': 'The sensor cannot infer where your body is for an arbitrary phone grip. Train HOOK using your normal grip. The detection threshold is halved while training; review any warnings.',
    '•  ЧУВСТВИТЕЛЬНОСТЬ И РАЗЛИЧИМОСТЬ': '•  SENSITIVITY AND CLASSIFICATION',
    'Порог заброса': 'CAST trigger threshold',
    'Базовый порог обнаружения. При обязательном замахе запись CAST начинается уже с 60% порога, чтобы не терять слабую подготовительную фазу.': 'Acceleration threshold for detecting a motion. CAST capture starts at 60% of this value to include a softer backswing.',
    'Порог подсечки': 'HOOK trigger threshold',
    'Отдельный порог для ПОДСЕЧКИ. Обычно ниже заброса: короткий рывок может быть мягче. Если подсечки пропадают — уменьши его первым.': 'Separate threshold for HOOK. A short pull can be softer than a cast. Lower this first if hooks are missed.',
    'CAST ВСЕГДА требует замах назад → вперёд.': 'CAST ALWAYS requires a back → forward motion.',
    'CAST принимается, только если по интегралу ускорения подтверждается возвратное движение назад → вперёд. Один разгон с торможением не должен срабатывать. При обучении неполный CAST тоже отклоняется.': 'CAST is accepted only when integrated acceleration supports a backward and forward motion. A single acceleration/deceleration should not count; incomplete CAST examples are rejected during training.',
    'Минимальная скорость замаха': 'Minimum backswing speed',
    'Оценка скорости по датчику за короткий жест, а не скорость по GPS. ВЫШЕ = строже к движению назад, но больше пропусков CAST.': 'Estimated short-gesture velocity from acceleration, not GPS speed. HIGHER = stricter backswing detection, but potentially more missed CASTs.',
    'Допуск сходства CAST': 'CAST similarity tolerance',
    'Независимый порог для заброса. Дистанция CAST должна быть НИЖЕ порога, и двухфазность должна подтверждаться. ВЫШЕ = мягче.': 'Separate acceptance distance for CAST. The score must be BELOW this threshold and the two phases must be confirmed. HIGHER = more lenient.',
    'Допуск сходства HOOK': 'HOOK similarity tolerance',
    'Независимый порог для подсечки. Если HOOK не дотягивает до собственного порога, результат UNKNOWN. ВЫШЕ = мягче.': 'Separate acceptance distance for HOOK. An out-of-range motion returns UNKNOWN. HIGHER = more lenient.',
    'HOOK ВСЕГДА требует направление к себе и ограничение вращения.': 'HOOK ALWAYS requires the trained pull direction and limited rotation.',
    'Сравнивается направление ПЕРВОГО ускорения подсечки с записанными примерами. Обучай только рывок к себе. Если в образцах смешаны противоположные движения, программа попросит переобучить HOOK. Начальный угол телефона относительно Земли не нужен.': 'The FIRST acceleration pulse is compared with trained HOOK examples. Record only pulls toward yourself. Conflicting example directions will require retraining. No fixed angle relative to Earth is needed.',
    'Строгость направления HOOK': 'HOOK direction strictness',
    'Косинус сходства первых ускорений: 0.50 = до 60° отклонения. ВЫШЕ = строже.': 'Cosine similarity of initial acceleration: 0.50 allows up to 60° deviation. HIGHER = stricter.',
    'Порог обнаружения вращения': 'Rotation detection threshold',
    'Если двигаешь телефон почти без ускорения, этот порог всё равно позволит записать NEGATIVE. МЕНЬШЕ = легче фиксируются повороты кисти.': 'Allows recording NEGATIVE examples even when rotation creates little linear acceleration. LOWER = easier to detect wrist twists.',
    'Максимальное вращение для HOOK': 'Maximum rotation for HOOK',
    'Максимальный угол отклонения телефона от начальной ориентации в течение подсечки. Если кисть вращается сильнее, жест будет UNKNOWN. МЕНЬШЕ = лучше подавляет пронацию/супинацию.': 'Maximum phone orientation change relative to the beginning of HOOK. A larger twist returns UNKNOWN. LOWER = better suppression of wrist rotation.',
    'Порог запрещённых движений': 'NEGATIVE matching threshold',
    'Если движение похоже на NEGATIVE, оно отвергается даже при сходстве с HOOK/CAST. ВЫШЕ = сильнее блокировка, но возможны пропуски настоящих жестов.': 'If a motion resembles a NEGATIVE example, it is rejected even when similar to CAST/HOOK. HIGHER = stronger blocking but more false negatives.',
    'Отстройка от другого жеста': 'Ambiguity margin',
    'Если оба класса прошли свои пороги, различие их дистанций должно превышать этот отрыв. ВЫШЕ = больше результатов UNKNOWN вместо спорных классификаций. При слишком похожих жестах понадобится переобучение.': 'If both positive classes pass, their score difference must exceed this margin. HIGHER = more UNKNOWN results for ambiguous motions. Retrain if the gestures are too similar.',
    '•  ТАЙМИНГ И ЗАЩИТА ОТ ПОВТОРОВ': '•  TIMING AND DUPLICATE PROTECTION',
    'Завершение движения': 'Motion end delay',
    'Сколько времени ждать после затихания движения. Для CAST с замахом используется минимум 0.42 с, чтобы не потерять вторую фазу.': 'How long to wait after the movement quiets. CAST waits at least 0.42 s to capture both phases.',
    'Пауза между командами': 'Command cooldown',
    'Минимальное время между двумя принятыми командами. Защищает от случайной повторной отправки F8.': 'Minimum time between accepted commands. Prevents accidental repeated F8 presses.',
    'Ожидание после заброса': 'Post-cast guard',
    'Минимальное время от заброса до допустимой подсечки. Защищает от повторного взмаха при забросе. Не распознаёт поклёвку.': 'Minimum delay after casting before HOOK is allowed. Prevents a cast follow-through from triggering a hook. Does not detect bites.',
    'Бортовой журнал': 'Captain’s Log',
    'В журнале: оценки CAST/HOOK/NEGATIVE, поворот телефона, причина UNKNOWN.': 'The log shows CAST/HOOK/NEGATIVE scores, phone rotation, and reasons for UNKNOWN.',
    '•  СОБЫТИЯ': '•  EVENTS', 'Очистить журнал': 'Clear log',
    'м/с²': 'm/s²', 'м/с': 'm/s', '°/с': '°/s', 'с': 's',
    # Dialogs and frequently used status messages.
    'ОТКЛЮЧЕНО': 'DISCONNECTED', 'СОЕДИНЯЮСЬ…': 'CONNECTING…', 'СОЕДИНЕНО': 'CONNECTED',
    'ПОТЕРЯНА СВЯЗЬ': 'CONNECTION LOST', 'ГОТОВ К ЗАБРОСУ': 'READY TO CAST',
    'Совершите движение после подключения': 'Connect the phone, then make a gesture',
    'РЕЖИМ ТРЕНИРОВКИ': 'PRACTICE MODE', 'ОЖИДАЕТСЯ ПОДСЕЧКА': 'AWAITING HOOK',
    'ОЖИДАЕТСЯ ЗАБРОС': 'AWAITING CAST',
    'Пресет пуст': 'Preset is empty', 'Сначала запиши обучающие жесты.': 'Record some training gestures first.',
    'Общий пресет для GitHub': 'Shared GitHub preset', 'Не удалось сохранить': 'Could not save',
    'Пресет готов': 'Preset ready', 'Адрес phyphox': 'phyphox address',
    'Подключение не удалось': 'Could not connect', 'Нет датчика': 'No sensor data',
    'Нужен активный phyphox с нажатой Play.': 'phyphox must be connected with Play enabled.',
    'Удалить примеры': 'Delete examples', 'Удалить все примеры': 'Delete all examples',
    'Удалить ВСЕ образцы CAST, HOOK и NEGATIVE?': 'Delete ALL CAST, HOOK, and NEGATIVE examples?',
    'Motion Fishing • Подключение по Wi-Fi': 'Motion Fishing • Wi-Fi setup',
    '1. Подключи iPhone и Windows к одной домашней сети.\n   Компьютер может быть подключён к роутеру кабелем.\n2. На iPhone открой phyphox → Acceleration and Attitude.\n3. Нажми Play и включи Allow Remote Access.\n4. Перепиши показанный адрес целиком, включая порт (:8080),\n   в поле «Адрес phyphox» и нажми «ПОДКЛЮЧИТЬ».\n5. Если не работает, сначала открой этот адрес в браузере Windows.\n\nBluetooth не требуется. На гостевой Wi-Fi сети устройства\nмогут быть изолированы друг от друга.': '1. Connect your iPhone and Windows PC to the same local network.\n   The PC may connect to the router via Ethernet.\n2. On iPhone, open phyphox → Acceleration and Attitude.\n3. Press Play and enable Allow Remote Access.\n4. Enter the complete address (including the port, such as :8080)\n   into the phyphox address field and press CONNECT.\n5. If it fails, first open the same address in a Windows browser.\n\nBluetooth is not required. Some guest Wi-Fi networks isolate devices.',
    'Скопировать текущие обучающие жесты и настройки в profiles/default.json?\nАдрес phyphox будет очищен, потому что у каждого игрока он свой.\nЛичный профиль останется без изменений.': 'Copy your current gesture examples and settings to profiles/default.json?\nYour personal phyphox address will be removed.\nYour personal profile will remain unchanged.',
    'Проверь одну сеть Wi-Fi/роутер, Play, Remote Access и адрес с портом.': 'Check that devices share a local network, Play and Remote Access are on, and the address includes the port.',
    'Нужны примеры CAST и HOOK. NEGATIVE необязателен, но полезен.': 'Record CAST and HOOK samples first. NEGATIVE examples are optional but useful.',
    'Ввод включён. Состояние сброшено; первый жест — заброс.': 'Key sending enabled. State reset; the next gesture should be CAST.',
    'Нечего удалять: ': 'Nothing to remove: ',
    'Состояние сброшено — ожидается заброс.': 'State reset — awaiting CAST.',
    'Все образцы удалены.': 'All examples deleted.', 'Все обучающие примеры удалены.': 'All training examples deleted.',
    'Нет синхронизированных данных ориентации': 'No synchronized orientation readings',
    'Введите адрес phyphox': 'Enter the phyphox address',
    'Нужен корневой адрес HTTP, например http://172.20.10.1': 'Use the base HTTP address, for example http://172.20.10.1',
    'Неверный кватернион': 'Invalid quaternion', 'Неверная ориентация': 'Invalid orientation',
    'Некорректный кватернион': 'Invalid quaternion', 'Мало точек для ориентации': 'Not enough orientation samples',
    'Неверная длительность': 'Invalid duration',
    'Недостаточно обучающих примеров CAST и HOOK': 'Not enough CAST and HOOK training samples',
    'UNKNOWN: движение похоже на запрещённый пример': 'UNKNOWN: resembles a NEGATIVE example',
    'CAST: нет двухфазного замаха': 'CAST: missing two-phase backswing',
    'CAST: не похож на обучение': 'CAST: does not match training',
    'HOOK: не похож на обучение': 'HOOK: does not match training',
    'UNKNOWN: обе модели подходят': 'UNKNOWN: both gestures match',
    'нет обучающих примеров HOOK': 'No HOOK training examples',
    'нечёткие старые примеры HOOK — переобучи подсечку': 'Legacy HOOK samples are ambiguous — retrain HOOK',
    'образцы HOOK противоречат по направлению — очисти и переобучи только рывок к себе': 'HOOK samples conflict in direction — clear HOOK and retrain pulls toward you',
    'не удалось определить начало рывка': 'Could not determine pull onset',
    'нет единого направления в обучении HOOK': 'HOOK training examples have no consistent direction',
    'слишком мало данных для двух фаз': 'Not enough data for two phases',
    'движение короче 0.26 с': 'Motion shorter than 0.26 s',
    'слишком длинное движение': 'Motion too long',
    'пропущены измерения во время движения': 'Sensor samples missing during motion',
    'нет выраженной оси движения': 'No dominant motion axis',
    'одна фаза значительно слабее другой': 'One phase much weaker than the other',
    'не хватает длительности одной из фаз': 'One phase is too short',
    'обратный и прямой ход подтверждены': 'Back-and-forward phases confirmed',
    'пауза после предыдущего жеста': 'Cooldown after previous gesture',
    'слишком рано после заброса': 'Too soon after CAST',
}

# A few algorithm reasons and logs contain numerical readings or variable names.
PATTERNS = [
    (r'^Записано: (\d+) из 12 возможных   •   Рекомендуется 5–8$', r'Recorded: \1 of 12 possible   •   Recommended: 5–8'),
    (r'^ВНИМАНИЕ: CAST и HOOK слишком похожи \((.+)\)\. Переобучи\.$', r'WARNING: CAST and HOOK are too similar (\1). Retrain.'),
    (r'^Разделение CAST и HOOK: (.+)\. Это диагностика, не гарантия точности\.$', r'CAST/HOOK separation: \1. Diagnostic only; accuracy is not guaranteed.'),
    (r'^Запись (CAST|HOOK|NEGATIVE): через 1 секунду выполни одно движение\.$', r'Recording \1: make one gesture after one second.'),
    (r'^Через секунду сделай одно движение: (.+)\.$', r'Make one \1 gesture after one second.'),
    (r'^Последний пример (CAST|HOOK|NEGATIVE) удалён\.$', r'Last \1 example removed.'),
    (r'^Примеры (.+) удалены\.$', r'Examples removed: \1.'),
    (r'^Примеры (CAST|HOOK|NEGATIVE) очищены отдельно\.$', r'Only \1 samples cleared.'),
    (r'^ОБРАЗЕЦ (CAST|HOOK|NEGATIVE) #(\d+) СОХРАНЁН', r'SAVED \1 EXAMPLE #\2'),
    (r'^Записан (CAST|HOOK|NEGATIVE) #(\d+)\. Желательно 5–8 примеров\.', r'Recorded \1 #\2. Recommended: 5–8 examples.'),
    (r'^Обучение: (CAST|HOOK|NEGATIVE) #(\d+); макс\. поворот (.+)°, суммарный (.+)°', r'Training: \1 #\2; peak rotation \3°, total rotation \4°'),
    (r'^неверное направление рывка: угол (.+)° \(порог (.+)°\)$', r'Incorrect pull direction: angle \1° (limit \2°)'),
    (r'^направление HOOK совпадает: угол (.+)°$', r'HOOK direction matches: angle \1°'),
    (r'^нет отчётливого возвратного движения: (.+) < (.+) м/с$', r'No distinct reversal: \1 < \2 m/s'),
    (r'^HOOK: вращение (.+)° > (.+)°$', r'HOOK: rotation \1° > \2°'),
    (r'^ожидается (CAST|HOOK)$', r'Expected \1'),
]

# Substrings used in real-time messages containing numeric fields or error details.
FRAGMENTS = [
    ('Портативный профиль:', 'Portable profile:'),
    ('Запуск. Подключение: локальная Wi-Fi сеть → phyphox → Play → Remote Access.', 'Started. Connect over local Wi-Fi → phyphox → Play → Remote Access.'),
    ('Единый IMU: CAST двухфазный; HOOK к себе без вращения; NEGATIVE отклоняет похожие движения.', 'One IMU method: two-phase CAST, pull-toward-you HOOK, NEGATIVE blocks lookalike motions.'),
    ('Не получилось сохранить настройки:', 'Could not save settings:'),
    ('Ошибка публикации пресета:', 'Could not publish preset:'),
    ('Общий пресет записан:', 'Shared preset saved:'),
    ('Создан файл:', 'Created file:'),
    ('Добавь profiles/default.json в GitHub. Профиль текущего пользователя не изменился.', 'Commit profiles/default.json to GitHub. Your personal profile was not changed.'),
    ('Соединение уже активно. Сначала отключись.', 'Already connected. Disconnect first.'),
    ('Отключено. Управление клавишами остановлено.', 'Disconnected. Key sending stopped.'),
    ('На связи:', 'Connected to:'),
    ('phyphox перезапущен — состояние сброшено.', 'phyphox restarted; state reset.'),
    ('Датчик запущен.', 'Sensor started.'),
    ('Датчик остановлен. Нажми Play.', 'Sensor stopped. Press Play.'),
    ('Жест пропущен:', 'Gesture skipped:'),
    ('Нет ответа от телефона:', 'No response from phone:'),
    ('Связь восстановлена. Управление нужно включить снова.', 'Connection restored. Re-enable key sending.'),
    ('Нечего удалять:', 'Nothing to delete:'),
    ('нет отчётливого возвратного движения:', 'no clear reverse motion:'),
    ('Откройте в phyphox импортированный эксперимент «Acceleration and Attitude»', 'Open the imported experiment “Acceleration and Attitude” in phyphox'),
    ('(НЕ «Ускорение без g»). Не найдены:', '(NOT “Acceleration without g”). Missing:'),
    ('Разная длина буферов', 'Buffers have different lengths'),
    (' с добавленными примерами', ' with additional samples'),
    ('ВНИМАНИЕ: ', 'WARNING: '),
    ('Обучение CAST: ', 'CAST training: '),
    ('нет двухфазного замаха', 'no two-phase backswing'),
    ('недостаточно обучающих примеров', 'not enough training examples'),
    (' м/с²', ' m/s²'),
    (' не похож на обучение', ' does not match training'),
    ('Для распознавания нужны новые IMU-примеры CAST и HOOK.', 'New IMU examples for CAST and HOOK are required.'),
    ('Не удалось собрать IMU-жест:', 'Failed to construct IMU gesture:'),
    ('CAST НЕ СОХРАНЁН:', 'CAST NOT SAVED:'),
    ('Не записано:', 'Not recorded:'),
    ('Обучение CAST: отклонён —', 'CAST training rejected —'),
    ('Удалить ВСЕ примеры ', 'Delete ALL examples of '),
    ('Примеры другого жеста сохранятся.', 'Other gesture samples will be kept.'),
    ('подсечки?', 'HOOK?'), ('заброса?', 'CAST?'), ('нежелательных движений?', 'NEGATIVE?'),
    ('поворот', 'rotation'), ('выше лимита', 'exceeds limit'),
    ('жест может отклоняться в игре', 'the game may reject this gesture'),
    ('проверь хват или удали неподходящий пример', 'check your grip or remove the conflicting sample'),
    (' ВНИМАНИЕ:', ' WARNING:'),
    (' | вращение=', ' | rotation='),
    ('Тренировка:', 'Practice:'),
    ('клавиша не отправлена.', 'key not sent.'),
    ('Не отправлено: телефон не передаёт данные.', 'Not sent: phone is not sending sensor data.'),
    ('Не отправлено: активно окно Motion Fishing.', 'Not sent: Motion Fishing window is focused.'),
    ('Не отправлено: активно не окно WoW', 'Not sent: WoW is not the active window'),
    ('ПРОПУЩЕНО:', 'SKIPPED:'),
    ('Не отправлено:', 'Not sent:'),
    ('Ошибка клавиатуры:', 'Keyboard error:'),
    ('Последний пример', 'Last example'),
    ('Примеры', 'Examples'),
    ('удалён.', 'removed.'),
    ('удалены.', 'removed.'),
    ('подсечки', 'HOOK'), ('заброса', 'CAST'), ('нежелательных движений', 'NEGATIVE'),
    ('Нажми Play.', 'Press Play.'),
]


def tr(value: object) -> str:
    s = str(value)
    if LANGUAGE == 'ru' or not s:
        return s
    if s in EN:
        return EN[s]
    # Numerical sensor readings and slider labels (without rewriting ordinary words).
    match = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)\s*(м/с²|м/с|°/с|с)', s)
    if match:
        return match.group(1) + ' ' + {'м/с²': 'm/s²', 'м/с': 'm/s', '°/с': '°/s', 'с': 's'}[match.group(2)]
    if s.startswith('•  '):
        return '•  ' + tr(s[3:])
    for pattern, replacement in PATTERNS:
        changed, count = re.subn(pattern, replacement, s)
        if count:
            return (changed.replace('ПОДСЕЧКУ', 'HOOK')
                    .replace('ЗАБРОС', 'CAST')
                    .replace('НЕЖЕЛАТЕЛЬНОЕ ДВИЖЕНИЕ', 'NEGATIVE'))
    for source, target in FRAGMENTS:
        s = s.replace(source, target)
    return s
