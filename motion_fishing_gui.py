"""Motion Fishing 1.2 — bilingual portable, single IMU method; local-origin motion + rotation.

No third-party runtime dependencies. iPhone phyphox HTTP Remote Access
on the user's local Wi-Fi network. No Bluetooth configuration required.
Does not automate bites or timers.
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError

from engine import FishingSession, MotionSegmenter, cast_reversal, hook_direction_gate, magnitude
from phyphox_client import Phyphox, normalize_url, relative_motion
from settings_store import load, save, settings_path, publish_preset
from imu_recognizer import make_example, classify, separation, angular_rate_dps
from windows_input import KEYS, foreground_title, tap
from i18n import tr, set_language


class LocalizedStringVar(tk.StringVar):
    """Preserve the original message so the UI can switch live in both directions."""
    def __init__(self, *args, **kwargs):
        initial = kwargs.pop('value', '')
        self.raw_value = initial
        super().__init__(*args, value=tr(initial), **kwargs)

    def set(self, value):
        self.raw_value = str(value)
        super().set(tr(self.raw_value))

    def refresh(self):
        super().set(tr(self.raw_value))


class TranslatedDialogs:
    """Translate messagebox title/body while preserving its normal return values."""
    def __getattr__(self, attr):
        callback = getattr(messagebox, attr)
        def wrapper(*args, **kwargs):
            return callback(*(tr(arg) if isinstance(arg, str) else arg for arg in args), **kwargs)
        return wrapper


dialogs = TranslatedDialogs()


BG = '#0B111A'              # stone
PANEL = '#172330'           # deep steel-blue
PANEL_ALT = '#111B27'
GOLD = '#CDA15B'
BRIGHT_GOLD = '#F3D59C'
BORDER = '#75542E'
INK = '#071018'
TEXT = '#F1E7D1'
MUTED = '#A9B5BB'
TEAL = '#80CDD1'
RED = '#EB9785'
BUTTON = '#293748'


def txt(parent, value: str = '', *, size: int = 10, color: str = TEXT,
        bold: bool = False, family: str = 'Segoe UI', **kwargs):
    return tk.Label(parent, text=tr(value), bg=parent.cget('bg'), fg=color,
                    font=(family, size, 'bold' if bold else 'normal'),
                    justify='left', anchor='w', **kwargs)


def btn(parent, title: str, command, *, primary=False, danger=False, compact=False):
    background = GOLD if primary else ('#473031' if danger else BUTTON)
    foreground = INK if primary else (RED if danger else TEXT)
    return tk.Button(parent, text=tr(title), command=command, relief='flat', bd=0,
                     bg=background, fg=foreground,
                     activebackground=BRIGHT_GOLD if primary else '#41536B',
                     activeforeground=INK if primary else TEXT,
                     cursor='hand2', font=('Segoe UI', 10, 'bold' if primary else 'normal'),
                     padx=10 if compact else 15, pady=6 if compact else 9)


def panel(parent, title: str, subtitle: str = ''):
    outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    outer.pack(fill='x', padx=18, pady=(0, 13))
    inner = tk.Frame(outer, bg=PANEL, padx=18, pady=16)
    inner.pack(fill='both', expand=True)
    txt(inner, tr(title), size=14, bold=True, color=BRIGHT_GOLD, family='Georgia').pack(anchor='w')
    if subtitle:
        txt(inner, tr(subtitle), size=9, color=MUTED, wraplength=790).pack(anchor='w', pady=(5, 12))
    return inner


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Motion Fishing')
        self.root.geometry('1020x800')
        self.root.minsize(780, 620)
        self.root.configure(bg=BG)
        self._set_icon()

        self.settings = load()
        self.language = self.settings.get('language', 'en')
        set_language(self.language)
        self.root.title(tr('Motion Fishing • Мастерская рыболова'))
        self._log_entries = []  # original-language text for live translation
        self.templates = self.settings['imu_templates']  # Only new IMU samples, no legacy fallbacks
        self.segmenter = MotionSegmenter(threshold=self.settings['cast_threshold'],
                                         quiet_seconds=self.settings['quiet_seconds'])
        self.session = FishingSession(cooldown=self.settings['cooldown'],
                                      hook_guard=self.settings['hook_guard'])
        self.events: queue.Queue = queue.Queue()
        self.stop_event: threading.Event | None = None
        self.worker: threading.Thread | None = None
        self.connected = False
        self.live = False
        self.training: str | None = None
        self.training_after = 0.
        self.save_after = None
        self.last_no_templates = -1e5
        self.last_reject = -1e5
        self.measuring = None
        self.attitudes_by_time = {}  # Only a short rolling sensor history
        self.last_attitude_sample = None

        self.url = tk.StringVar(value=self.settings['url'])
        self.key = tk.StringVar(value=self.settings['key'])
        self.only_wow = tk.BooleanVar(value=self.settings['only_wow'])
        self.keyboard_on = tk.BooleanVar(value=True)  # Key sending is enabled by default on launch
        self.values = {k: tk.DoubleVar(value=self.settings[k]) for k in (
            'cast_threshold', 'hook_threshold',
            'cast_match_tolerance', 'hook_match_tolerance', 'negative_match_tolerance',
            'min_reversal_speed', 'hook_direction_min_cosine', 'hook_max_rotation_degrees',
            'rotation_trigger_dps',
            'ambiguity_margin', 'cooldown', 'hook_guard', 'quiet_seconds')}
        self.status = LocalizedStringVar(value='ОТКЛЮЧЕНО')
        self.acc = LocalizedStringVar(value='0.0 м/с²')
        self.expected = LocalizedStringVar(value='ГОТОВ К ЗАБРОСУ')
        self.last = LocalizedStringVar(value='Совершите движение после подключения')
        self.training_hint = LocalizedStringVar(value='')
        self.separation_hint = LocalizedStringVar(value='')
        self.params_labels: dict[str, tk.Label] = {}
        self._build()
        self._update_counts()
        self._update_params()
        self._wire_traces()
        self._update_expected()
        self._log('Запуск. Подключение: локальная Wi-Fi сеть → phyphox → Play → Remote Access.')
        self._log('Единый IMU: CAST двухфазный; HOOK к себе без вращения; NEGATIVE отклоняет похожие движения.')
        self._log(f'Портативный профиль: {settings_path()}')
        self.root.after(90, self._drain)
        self.root.protocol('WM_DELETE_WINDOW', self._close)

    def _change_language(self, code: str):
        if code == self.language:
            return
        self.language = code
        set_language(code)
        self.settings['language'] = code
        self.root.title(tr('Motion Fishing • Мастерская рыболова'))
        self._save()
        # Preserve connected sensor worker, trained profiles, widgets' backing variables,
        # and event history. Recreate only the presentation controls.
        for child in tuple(self.root.winfo_children()):
            child.destroy()
        self.params_labels = {}
        self._build()
        self._update_counts()
        self._update_params()
        self._update_expected()
        for variable in (self.status, self.acc, self.expected, self.last,
                         self.training_hint, self.separation_hint):
            variable.refresh()
        self._render_log_entries()

    def _render_log_entries(self):
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        for stamp, raw in self._log_entries[-320:]:
            self.log.insert('end', stamp + '   ' + tr(raw) + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _set_icon(self):
        p = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets' / 'motion_fishing.ico'
        if p.exists():
            try:
                self.root.iconbitmap(str(p))
            except tk.TclError:
                pass

    def _scroll_tab(self, notebook, name):
        frame = tk.Frame(notebook, bg=BG)
        notebook.add(frame, text='   ' + tr(name) + '   ')
        canvas = tk.Canvas(frame, bg=BG, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(frame, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = tk.Frame(canvas, bg=BG)
        item = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(item, width=e.width))

        def scroll(e):
            # Scrolling only when the pointer is over this tab. Avoids global bindings.
            canvas.yview_scroll(-int(e.delta / 120), 'units')
        def bind_wheel(widget):
            widget.bind('<MouseWheel>', scroll)
            for child in widget.winfo_children():
                bind_wheel(child)
        # Recursively binding after controls are created handled in _build().
        self._scrollers.append((inner, scroll, bind_wheel))
        return inner

    def _build(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TNotebook', background=BG, borderwidth=0, tabmargins=[13, 0, 0, 0])
        style.configure('TNotebook.Tab', background=PANEL_ALT, foreground=MUTED,
                        padding=[21, 12], font=('Segoe UI', 10, 'bold'), borderwidth=1)
        style.map('TNotebook.Tab', background=[('selected', BORDER)],
                  foreground=[('selected', BRIGHT_GOLD)])
        style.configure('Vertical.TScrollbar', background=BUTTON, troughcolor=BG,
                        bordercolor=BG, arrowcolor=GOLD)
        style.configure('Fishing.TCombobox', fieldbackground=PANEL_ALT,
                        background=PANEL_ALT, foreground=TEXT, arrowcolor=GOLD)

        masthead = tk.Frame(self.root, bg=PANEL_ALT, pady=12, padx=23)
        masthead.pack(fill='x')
        crest = tk.Canvas(masthead, width=67, height=69, bg=PANEL_ALT, highlightthickness=0)
        crest.pack(side='left', padx=(0, 16))
        crest.create_oval(3, 3, 63, 63, outline=GOLD, width=3)
        crest.create_oval(9, 9, 57, 57, outline=BORDER, width=1)
        crest.create_arc(16, 12, 51, 53, start=190, extent=205, outline=BRIGHT_GOLD, width=3, style='arc')
        crest.create_line(41, 17, 41, 41, fill=BRIGHT_GOLD, width=2)
        crest.create_oval(35, 38, 47, 49, fill=RED, outline=BRIGHT_GOLD, width=1)
        crest.create_arc(13, 44, 57, 62, start=18, extent=135, outline=TEAL, width=2, style='arc')
        heading = tk.Frame(masthead, bg=PANEL_ALT)
        heading.pack(side='left', fill='x', expand=True)
        txt(heading, 'MOTION FISHING', size=27, family='Georgia', bold=True, color=BRIGHT_GOLD).pack(anchor='w')
        txt(heading, 'МАСТЕРСКАЯ РЫБОЛОВА    •    iPHONE   /   WI-FI   /   WoW FOREVER',
            size=9, color=TEAL, bold=True).pack(anchor='w', pady=(4, 0))
        status_box = tk.Frame(masthead, bg=PANEL_ALT)
        status_box.pack(side='right', padx=(12, 0))
        txt(status_box, 'СОЕДИНЕНИЕ', size=8, color=MUTED).pack(anchor='e')
        txt(status_box, '', textvariable=self.status, size=11, color=TEAL, bold=True).pack(anchor='e')
        # Always visible in the header, never buried in Settings.
        lang_box = tk.Frame(masthead, bg=PANEL_ALT)
        lang_box.pack(side='right', padx=(6, 20))
        txt(lang_box, 'LANGUAGE / ЯЗЫК', size=8, color=MUTED, bold=True).pack(anchor='center', pady=(0, 4))
        switch_row = tk.Frame(lang_box, bg=PANEL_ALT)
        switch_row.pack(anchor='center')
        for code, label in (('ru', 'RU'), ('en', 'EN')):
            selected = self.language == code
            tk.Button(switch_row, text=label, command=lambda c=code: self._change_language(c),
                      relief='solid', bd=1, cursor='hand2', width=5,
                      bg=GOLD if selected else PANEL, fg=INK if selected else TEXT,
                      activebackground=BRIGHT_GOLD, activeforeground=INK,
                      highlightthickness=0, font=('Segoe UI', 10, 'bold'),
                      padx=3, pady=5).pack(side='left', padx=3)
        tk.Frame(self.root, height=2, bg=GOLD).pack(fill='x')

        self._scrollers = []
        tabs = ttk.Notebook(self.root)
        tabs.pack(fill='both', expand=True)
        self.home = self._scroll_tab(tabs, 'ПРИЧАЛ')
        self.training_page = self._scroll_tab(tabs, 'ШКОЛА ЖЕСТОВ')
        self.settings_page = self._scroll_tab(tabs, 'НАСТРОЙКИ')
        self.log_page = self._scroll_tab(tabs, 'ЖУРНАЛ')

        self._build_home()
        self._build_training()
        self._build_settings()
        self._build_log()
        for _inner, _scroll, bind_wheel in self._scrollers:
            bind_wheel(_inner)

        footer = tk.Frame(self.root, bg=PANEL_ALT, padx=23, pady=7)
        footer.pack(fill='x')
        txt(footer, 'MOTION FISHING  •  v1.2  /  BILINGUAL PORTABLE', size=8, color=MUTED).pack(side='left')
        txt(footer, 'ДЕЙСТВИЯ — ТОЛЬКО ПО ЖЕСТУ', size=8, color=GOLD).pack(side='right')

    def _build_home(self):
        intro = tk.Frame(self.home, bg=BG, padx=22, pady=17)
        intro.pack(fill='x')
        txt(intro, 'Забрасывай удочку. Почувствуй подсечку.', size=17,
            color=TEXT, family='Georgia', bold=True).pack(anchor='w')
        txt(intro, 'Физический контроллер на основе iPhone. Без автоловли и распознавания поклёвок.',
            size=10, color=MUTED).pack(anchor='w', pady=(4, 0))

        c = panel(self.home, '01  •  СВЯЗЬ С УДОЧКОЙ',
                  'Подключи iPhone и ПК к одной локальной сети (Wi-Fi; ПК может быть по кабелю). Вставь адрес Remote Access из phyphox.')
        row = tk.Frame(c, bg=PANEL)
        row.pack(fill='x')
        txt(row, 'АДРЕС PHYphox', size=9, color=MUTED).pack(side='left', padx=(0, 11))
        tk.Entry(row, textvariable=self.url, font=('Consolas', 11),
                 bg=PANEL_ALT, fg=TEXT, insertbackground=TEXT, relief='flat',
                 highlightthickness=1, highlightbackground=BORDER).pack(side='left', fill='x', expand=True,
                                                                        ipady=9, padx=(0, 9))
        btn(row, 'ПОДКЛЮЧИТЬ', self._connect, primary=True).pack(side='left', padx=(0, 6))
        btn(row, 'Отключить', self._disconnect).pack(side='left')
        btn(c, 'КАК ПОДКЛЮЧИТЬ ПО WI-FI?', self._wifi_help, compact=True).pack(anchor='w', pady=(10, 0))
        row2 = tk.Frame(c, bg=PANEL)
        row2.pack(fill='x', pady=(13, 0))
        txt(row2, 'Датчик:  ', color=MUTED).pack(side='left')
        txt(row2, '', textvariable=self.acc, color=TEAL, bold=True).pack(side='left')
        txt(row2, '    •    Данные сохраняются в папке profiles рядом с программой', color=MUTED, size=9).pack(side='left')

        c = panel(self.home, '02  •  УПРАВЛЕНИЕ ЗАБРОСОМ',
                  'Для WoW используй ту же клавишу, которую назначил в аддоне рыбалки (например, F8).')
        row = tk.Frame(c, bg=PANEL)
        row.pack(fill='x')
        txt(row, 'Клавиша', color=MUTED).pack(side='left', padx=(0, 9))
        ttk.Combobox(row, textvariable=self.key, values=list(KEYS), state='readonly',
                     style='Fishing.TCombobox', width=9).pack(side='left', padx=(0, 18))
        self._check(row, 'Отправлять только в активное окно WoW', self.only_wow).pack(side='left')
        btn(row, 'СБРОС К ЗАБРОСУ', self._reset_state, compact=True).pack(side='right')
        row2 = tk.Frame(c, bg=PANEL)
        row2.pack(fill='x', pady=(16, 0))
        self._check(row2, 'ОТПРАВКА КЛАВИШ В ИГРУ', self.keyboard_on, bold=True).pack(side='left')
        txt(row2, '', textvariable=self.expected, color=BRIGHT_GOLD,
            family='Georgia', size=12, bold=True).pack(side='right')
        txt(c, 'Отправка клавиш включена при запуске. Для тренировки выключи её вручную.',
            size=9, color=MUTED, wraplength=790).pack(anchor='w', pady=(13, 0))

        c = panel(self.home, '03  •  ПОСЛЕДНЕЕ ДВИЖЕНИЕ')
        txt(c, '', textvariable=self.last, color=TEAL, size=11, bold=True,
            wraplength=790).pack(anchor='w')
        txt(c, 'CAST → F8 → ожидание поклёвки → HOOK → F8 → CAST',
            color=MUTED, family='Consolas', size=10).pack(anchor='w', pady=(8, 0))
        tk.Frame(self.home, bg=BG, height=9).pack()

    def _check(self, parent, text, var, bold=False):
        return tk.Checkbutton(parent, text=tr(text), variable=var, bg=parent.cget('bg'),
                              fg=BRIGHT_GOLD if bold else TEXT, selectcolor=BUTTON,
                              activebackground=parent.cget('bg'), activeforeground=TEXT,
                              font=('Segoe UI', 10, 'bold' if bold else 'normal'))

    def _build_training(self):
        intro = tk.Frame(self.training_page, bg=BG, padx=22, pady=16)
        intro.pack(fill='x')
        txt(intro, 'Твои движения — твои правила', size=18,
            family='Georgia', bold=True, color=TEXT).pack(anchor='w')
        txt(intro, 'Запиши 5–8 естественных повторов каждого жеста. CAST: назад → вперёд; HOOK: рывок к себе без поворота кисти. '
                   'Для записи одного движения нажми кнопку, выжди секунду и взмахни.', color=MUTED,
            wraplength=840).pack(anchor='w', pady=(5, 0))

        for kind, title, desc in (
            ('CAST', 'ЗАБРОС', 'Обязательно: движение назад → разворот → движение вперёд. Один взмах не будет сохранён.'),
            ('HOOK', 'ПОДСЕЧКА', 'Рывок К СЕБЕ без пронации/супинации. Поворот кисти не должен вызывать HOOK.'),
            ('NEGATIVE', 'НЕ ДЕЙСТВИЕ', 'Запиши 5–8 движений, которые должны игнорироваться: пронация, супинация, поправить телефон в руке.'),
        ):
            p = panel(self.training_page, '•  ' + title, desc)
            buttons = tk.Frame(p, bg=PANEL)
            buttons.pack(fill='x')
            btn(buttons, 'ЗАПИСАТЬ ПРИМЕР', lambda kind=kind: self._train(kind),
                primary=True).pack(side='left', padx=(0, 7))
            btn(buttons, 'Удалить последний', lambda kind=kind: self._delete_last(kind),
                compact=True).pack(side='left', padx=(0, 7))
            btn(buttons, 'Очистить ' + title.lower(), lambda kind=kind: self._clear_kind(kind),
                danger=True, compact=True).pack(side='left')
            count = txt(p, '', color=TEAL, size=10, bold=True)
            count.pack(anchor='w', pady=(11, 0))
            setattr(self, 'count_' + kind, count)

        c = panel(self.training_page, '•  ОЦЕНКА ОБУЧЕНИЯ',
                  'Один алгоритм: ускорение и вращение в координатах начала жеста. '
                  'Старые версии жестов не загружаются: переобучи CAST/HOOK, затем добавь отрицательные движения.')
        txt(c, '', textvariable=self.separation_hint, color=TEAL, wraplength=780).pack(anchor='w')
        txt(c, '', textvariable=self.training_hint, color=BRIGHT_GOLD,
            wraplength=780).pack(anchor='w', pady=(8, 0))
        btn(c, 'ОЧИСТИТЬ ВСЕ ПРИМЕРЫ', self._clear_all, danger=True).pack(anchor='w', pady=(14, 0))

        c = panel(self.training_page, '•  ПРЕСЕТ ДЛЯ GITHUB',
                  'Настройки и примеры жестов хранятся в папке profiles рядом с приложением. '
                  'Создай общий пресет для новых игроков после обучения. Адрес phyphox не публикуется.')
        btn(c, 'СОХРАНИТЬ МОИ ЖЕСТЫ В ОБЩИЙ ПРЕСЕТ', self._publish_preset,
            primary=True).pack(anchor='w')
        txt(c, 'Файл profiles/default.json можно загрузить в GitHub. '
               'Личные изменения сохраняются отдельно в profiles/settings.json.',
            color=MUTED, size=9, wraplength=790).pack(anchor='w', pady=(9, 0))

    def _build_settings(self):
        intro = tk.Frame(self.settings_page, bg=BG, padx=22, pady=15)
        intro.pack(fill='x')
        txt(intro, 'Точная настройка снасти', size=18,
            color=TEXT, family='Georgia', bold=True).pack(anchor='w')
        txt(intro, 'Изменения сразу применяются и сохраняются. Проверяй результат на вкладке «Журнал».',
            color=MUTED).pack(anchor='w', pady=(5, 0))

        c = panel(self.settings_page, '•  ЕДИНЫЙ МЕТОД: IMU / ЛОКАЛЬНЫЙ НОЛЬ',
                  'Ускорение пересчитывается относительно начальной ориентации телефона. '
                  'Attitude используется также для измерения вращения. Нет режимов фиксированного хвата, '
                  'глобальных осей и сравнения только модуля ускорения.')
        txt(c, 'Нельзя независимо определить направление «к телу» при произвольном хвате. '
               'Обучай HOOK в привычном хвате; во время обучения порог ускорения снижен вдвое. Если пример записан с предупреждением, проверь настройки фильтра.',
            color=MUTED, size=9, wraplength=790).pack(anchor='w')

        c = panel(self.settings_page, '•  ЧУВСТВИТЕЛЬНОСТЬ И РАЗЛИЧИМОСТЬ')
        self._slider(c, 'cast_threshold', 'Порог заброса', 1., 8., .10, 'м/с²',
                     'Базовый порог обнаружения. При обязательном замахе запись CAST начинается '
                     'уже с 60% порога, чтобы не терять слабую подготовительную фазу.')
        self._slider(c, 'hook_threshold', 'Порог подсечки', .75, 8., .10, 'м/с²',
                     'Отдельный порог для ПОДСЕЧКИ. Обычно ниже заброса: короткий рывок может '
                     'быть мягче. Если подсечки пропадают — уменьши его первым.')
        txt(c, 'CAST ВСЕГДА требует замах назад → вперёд.', color=BRIGHT_GOLD, bold=True).pack(anchor='w', pady=(10, 5))
        txt(c, 'CAST принимается, только если по интегралу ускорения подтверждается возвратное '
               'движение назад → вперёд. Один разгон с торможением не должен срабатывать. '
               'При обучении неполный CAST тоже отклоняется.',
            color=MUTED, size=9, wraplength=790).pack(anchor='w', pady=(0, 6))
        self._slider(c, 'min_reversal_speed', 'Минимальная скорость замаха', .06, .60, .01, 'м/с',
                     'Оценка скорости по датчику за короткий жест, а не скорость по GPS. '
                     'ВЫШЕ = строже к движению назад, но больше пропусков CAST.')
        self._slider(c, 'cast_match_tolerance', 'Допуск сходства CAST', .10, 1.50, .01, '',
                     'Независимый порог для заброса. Дистанция CAST должна быть НИЖЕ порога, '
                     'и двухфазность должна подтверждаться. ВЫШЕ = мягче.')
        self._slider(c, 'hook_match_tolerance', 'Допуск сходства HOOK', .10, 1.50, .01, '',
                     'Независимый порог для подсечки. Если HOOK не дотягивает до собственного '
                     'порога, результат UNKNOWN. ВЫШЕ = мягче.')
        txt(c, 'HOOK ВСЕГДА требует направление к себе и ограничение вращения.',
            color=BRIGHT_GOLD, bold=True).pack(anchor='w', pady=(8, 4))
        txt(c, 'Сравнивается направление ПЕРВОГО ускорения подсечки с записанными примерами. '
               'Обучай только рывок к себе. Если в образцах смешаны противоположные движения, '
               'программа попросит переобучить HOOK. Начальный угол телефона относительно Земли не нужен.',
            color=MUTED, size=9, wraplength=790).pack(anchor='w', pady=(0, 5))
        self._slider(c, 'hook_direction_min_cosine', 'Строгость направления HOOK', .10, .95, .05, '',
                     'Косинус сходства первых ускорений: 0.50 = до 60° отклонения. ВЫШЕ = строже.')
        self._slider(c, 'rotation_trigger_dps', 'Порог обнаружения вращения', 50., 360., 10., '°/с',
                     'Если двигаешь телефон почти без ускорения, этот порог всё равно позволит записать NEGATIVE. '
                     'МЕНЬШЕ = легче фиксируются повороты кисти.')
        self._slider(c, 'hook_max_rotation_degrees', 'Максимальное вращение для HOOK', 10., 180., 5., '°',
                     'Максимальный угол отклонения телефона от начальной ориентации в течение подсечки. Если кисть вращается сильнее, '
                     'жест будет UNKNOWN. МЕНЬШЕ = лучше подавляет пронацию/супинацию.')
        self._slider(c, 'negative_match_tolerance', 'Порог запрещённых движений', .10, 1.50, .02, '',
                     'Если движение похоже на NEGATIVE, оно отвергается даже при сходстве с HOOK/CAST. '
                     'ВЫШЕ = сильнее блокировка, но возможны пропуски настоящих жестов.')
        self._slider(c, 'ambiguity_margin', 'Отстройка от другого жеста', 0., .30, .005, '',
                     'Если оба класса прошли свои пороги, различие их дистанций должно превышать этот отрыв. '
                     'ВЫШЕ = больше результатов UNKNOWN вместо спорных классификаций. '
                     'При слишком похожих жестах понадобится переобучение.')

        c = panel(self.settings_page, '•  ТАЙМИНГ И ЗАЩИТА ОТ ПОВТОРОВ')
        self._slider(c, 'quiet_seconds', 'Завершение движения', .10, .50, .02, 'с',
                     'Сколько времени ждать после затихания движения. Для CAST с замахом '
                     'используется минимум 0.42 с, чтобы не потерять вторую фазу.')
        self._slider(c, 'cooldown', 'Пауза между командами', .35, 3., .05, 'с',
                     'Минимальное время между двумя принятыми командами. Защищает '
                     'от случайной повторной отправки F8.')
        self._slider(c, 'hook_guard', 'Ожидание после заброса', .50, 4., .10, 'с',
                     'Минимальное время от заброса до допустимой подсечки. '
                     'Защищает от повторного взмаха при забросе. Не распознаёт поклёвку.')

    def _slider(self, parent, key, heading, lo, hi, step, unit, description):
        outer = tk.Frame(parent, bg=PANEL)
        outer.pack(fill='x', pady=(7, 12))
        top = tk.Frame(outer, bg=PANEL)
        top.pack(fill='x')
        txt(top, heading, size=11, bold=True).pack(side='left')
        val = txt(top, '', size=11, bold=True, color=BRIGHT_GOLD)
        val.pack(side='right')
        self.params_labels[key] = (val, unit)
        scale = tk.Scale(outer, variable=self.values[key], from_=lo, to=hi,
                         resolution=step, orient='horizontal', showvalue=False,
                         bg=PANEL, troughcolor=BUTTON, activebackground=GOLD,
                         highlightthickness=0, bd=0, sliderlength=17,
                         fg=TEXT, length=600)
        scale.pack(fill='x', anchor='w')
        txt(outer, description, color=MUTED, size=9,
            wraplength=790).pack(anchor='w')
        tk.Frame(parent, height=1, bg='#354454').pack(fill='x')

    def _build_log(self):
        intro = tk.Frame(self.log_page, bg=BG, padx=22, pady=16)
        intro.pack(fill='x')
        txt(intro, 'Бортовой журнал', size=18, family='Georgia', bold=True).pack(anchor='w')
        txt(intro, 'В журнале: оценки CAST/HOOK/NEGATIVE, поворот телефона, причина UNKNOWN.',
            color=MUTED).pack(anchor='w', pady=(5, 0))
        c = panel(self.log_page, '•  СОБЫТИЯ')
        self.log = tk.Text(c, bg=PANEL_ALT, fg=TEXT, insertbackground=TEAL,
                           font=('Consolas', 10), height=21, relief='flat',
                           padx=12, pady=12, wrap='word', state='disabled')
        self.log.pack(fill='both', expand=True)
        btn(c, 'Очистить журнал', self._clear_log, compact=True).pack(anchor='e', pady=(10, 0))

    def _wire_traces(self):
        self.keyboard_on.trace_add('write', lambda *_: self._toggle_keyboard())
        for var in (self.url, self.key, self.only_wow, *self.values.values()):
            var.trace_add('write', lambda *_: self._changed())

    def _changed(self):
        self._update_params()
        self._update_counts()
        if self.save_after is not None:
            self.root.after_cancel(self.save_after)
        self.save_after = self.root.after(650, self._save)

    def _update_params(self):
        for key, (lab, unit) in self.params_labels.items():
            number = self.values[key].get()
            lab.configure(text=tr(f'{number:.3f} {unit}'.strip() if key == 'ambiguity_margin'
                          else f'{number:.2f} {unit}'.strip()))
        self.segmenter.quiet_seconds = self.values['quiet_seconds'].get()
        self.session.cooldown = self.values['cooldown'].get()
        self.session.hook_guard = self.values['hook_guard'].get()

    def _save(self):
        self.save_after = None
        self.settings.update({
            'url': self.url.get().strip(), 'key': self.key.get(),
            'only_wow': self.only_wow.get(),
            **{k: v.get() for k, v in self.values.items()},
            'imu_templates': self.templates,
            'language': self.language,
        })
        try:
            save(self.settings)
        except OSError as err:
            self._log(f'Не получилось сохранить настройки: {err}')

    def _publish_preset(self):
        total = sum(len(self.templates[k]) for k in ('CAST', 'HOOK', 'NEGATIVE'))
        if not total:
            dialogs.showwarning('Пресет пуст', 'Сначала запиши обучающие жесты.')
            return
        if not dialogs.askyesno(
                'Общий пресет для GitHub',
                'Скопировать текущие обучающие жесты и настройки в profiles/default.json?\n'
                'Адрес phyphox будет очищен, потому что у каждого игрока он свой.\n'
                'Личный профиль останется без изменений.'):
            return
        self._save()
        try:
            destination = publish_preset(self.settings)
        except OSError as exc:
            dialogs.showerror('Не удалось сохранить', str(exc))
            self._log(f'Ошибка публикации пресета: {exc}')
            return
        self._log(f'Общий пресет записан: {destination}')
        dialogs.showinfo('Пресет готов',
                            f'Создан файл:\n{destination}\n\n'
                            'Добавь profiles/default.json в GitHub. '
                            'Профиль текущего пользователя не изменился.')

    def _update_counts(self):
        for kind in ('CAST', 'HOOK', 'NEGATIVE'):
            n = len(self.templates[kind])
            getattr(self, 'count_' + kind).configure(
                text=tr(f'Записано: {n} из 12 возможных   •   Рекомендуется 5–8'))
        gap = separation(self.templates)
        if gap is None:
            self.separation_hint.set('Нужны примеры CAST и HOOK. NEGATIVE необязателен, но полезен.')
        elif gap < .06:
            self.separation_hint.set(f'ВНИМАНИЕ: CAST и HOOK слишком похожи ({gap:.3f}). Переобучи.')
        else:
            self.separation_hint.set(f'Разделение CAST и HOOK: {gap:.3f}. Это диагностика, не гарантия точности.')

    def _toggle_keyboard(self):
        if self.keyboard_on.get():
            self.session.reset()
            self.segmenter.reset()
            self._update_expected()
            self._log('Ввод включён. Состояние сброшено; первый жест — заброс.')
        else:
            self._update_expected()

    def _update_expected(self):
        if not self.keyboard_on.get():
            self.expected.set('РЕЖИМ ТРЕНИРОВКИ')
        elif self.session.line_out:
            self.expected.set('ОЖИДАЕТСЯ ПОДСЕЧКА')
        else:
            self.expected.set('ОЖИДАЕТСЯ ЗАБРОС')

    def _log(self, message):
        self._log_entries.append((time.strftime('%H:%M:%S'), str(message)))
        if len(self._log_entries) > 320:
            self._log_entries = self._log_entries[-300:]
        if hasattr(self, 'log') and self.log.winfo_exists():
            self.log.configure(state='normal')
            self.log.insert('end', self._log_entries[-1][0] + '   ' + tr(message) + '\n')
            lines = int(self.log.index('end-1c').split('.')[0])
            if lines > 360:
                self.log.delete('1.0', '90.0')
            self.log.see('end')
            self.log.configure(state='disabled')

    def _clear_log(self):
        self._log_entries.clear()
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

    def _wifi_help(self):
        dialogs.showinfo(
            'Motion Fishing • Подключение по Wi-Fi',
            '1. Подключи iPhone и Windows к одной домашней сети.\n'
            '   Компьютер может быть подключён к роутеру кабелем.\n'
            '2. На iPhone открой phyphox → Acceleration and Attitude.\n'
            '3. Нажми Play и включи Allow Remote Access.\n'
            '4. Перепиши показанный адрес целиком, включая порт (:8080),\n'
            '   в поле «Адрес phyphox» и нажми «ПОДКЛЮЧИТЬ».\n'
            '5. Если не работает, сначала открой этот адрес в браузере Windows.\n\n'
            'Bluetooth не требуется. На гостевой Wi-Fi сети устройства\n'
            'могут быть изолированы друг от друга.'
        )

    def _connect(self):
        if self.worker and self.worker.is_alive():
            self._log('Соединение уже активно. Сначала отключись.')
            return
        try:
            address = normalize_url(self.url.get())
        except ValueError as err:
            dialogs.showerror('Адрес phyphox', str(err))
            return
        self.url.set(address)
        self._save()
        self.segmenter.reset()
        self.attitudes_by_time.clear()
        self.last_attitude_sample = None
        self.measuring = None
        self.stop_event = threading.Event()
        self.worker = threading.Thread(target=self._poll, args=(address, self.stop_event), daemon=True)
        self.worker.start()
        self.status.set('СОЕДИНЯЮСЬ…')

    def _poll(self, address, stop):
        try:
            api = Phyphox(address)
            title = api.check()
            self.events.put(('connected', title))
            last_error = -1e10
            failed = False
            while not stop.is_set():
                try:
                    samples, measuring, changed = api.samples()
                    self.events.put(('samples', samples, measuring, changed))
                    if failed:
                        self.events.put(('recovered',))
                    failed = False
                except (URLError, HTTPError, OSError, TimeoutError, ValueError) as err:
                    failed = True
                    if time.monotonic() - last_error > 4:
                        self.events.put(('network_error', str(err)))
                        last_error = time.monotonic()
                    if stop.wait(.5):
                        break
                    continue
                stop.wait(.10)
        except (URLError, HTTPError, OSError, TimeoutError, ValueError, RuntimeError) as err:
            self.events.put(('fatal', str(err)))
        finally:
            self.events.put(('stopped',))

    def _disconnect(self):
        if self.stop_event:
            self.stop_event.set()
        self.connected = False
        self.live = False
        self.keyboard_on.set(False)
        self.training = None
        self.training_hint.set('')
        self.segmenter.reset()
        self.last_attitude_sample = None
        self.status.set('ОТКЛЮЧЕНО')
        self._log('Отключено. Управление клавишами остановлено.')

    def _drain(self):
        try:
            for _ in range(65):
                event = self.events.get_nowait()
                kind = event[0]
                if kind == 'connected' and self.stop_event and not self.stop_event.is_set():
                    self.connected = True
                    self.status.set('СОЕДИНЕНО')
                    self._log('На связи: ' + str(event[1]))
                elif kind == 'samples' and self.connected:
                    _, values, measuring, changed = event
                    if changed:
                        self.segmenter.reset()
                        self.attitudes_by_time.clear()
                        self.last_attitude_sample = None
                        self.session.reset()
                        self.training = None
                        self.training_hint.set('')
                        self._update_expected()
                        self._log('phyphox перезапущен — состояние сброшено.')
                    if measuring != self.measuring:
                        self.measuring = measuring
                        self._log('Датчик ' + ('запущен.' if measuring else 'остановлен. Нажми Play.'))
                        if not measuring:
                            self.segmenter.reset()
                    self.live = bool(measuring)
                    if not measuring:
                        continue
                    if values:
                        latest = values[-1][0]
                        self.acc.set(f'{magnitude(latest):.1f} м/с²')
                    for pair in values:
                        self.attitudes_by_time[pair[0][0]] = pair[2]
                    if values:
                        cutoff = values[-1][0][0] - 4.0
                        for timestamp in tuple(self.attitudes_by_time):
                            if timestamp < cutoff:
                                del self.attitudes_by_time[timestamp]
                    for pair in values:
                        sample = pair[0]
                        rate = 0.
                        if self.last_attitude_sample is not None:
                            previous_t, previous_q = self.last_attitude_sample
                            rate = angular_rate_dps(previous_q, pair[2], sample[0] - previous_t)
                        self.last_attitude_sample = (sample[0], pair[2])
                        goal = self.training or (self.session.expected if self.keyboard_on.get() else 'PRACTICE')
                        if goal == 'PRACTICE':
                            self.segmenter.threshold = min(self.values['cast_threshold'].get(),
                                                           self.values['hook_threshold'].get())
                        else:
                            self.segmenter.threshold = self.values[
                                'hook_threshold' if goal == 'HOOK' else 'cast_threshold'].get()
                        if goal in ('CAST', 'PRACTICE'):
                            self.segmenter.threshold = max(.70, self.segmenter.threshold * .60)
                        elif self.training == 'HOOK':
                            # Training is acquisition, not classification: capture gentle
                            # single-phase pulls without relaxing the in-game threshold.
                            self.segmenter.threshold = max(.50, self.segmenter.threshold * .50)
                        # The backward and forward phase belong to one CAST,
                        # including a short transition pause.
                        if goal in ('CAST', 'PRACTICE'):
                            self.segmenter.quiet_seconds = max(self.values['quiet_seconds'].get(), .42)
                            self.segmenter.max_seconds = 2.1
                            self.segmenter.pre_seconds = .18
                        else:
                            self.segmenter.quiet_seconds = self.values['quiet_seconds'].get()
                            self.segmenter.max_seconds = 1.5
                            self.segmenter.pre_seconds = .12
                        movement = self.segmenter.feed(sample, rate,
                                 self.values['rotation_trigger_dps'].get())
                        if movement is not None:
                            try:
                                local = relative_motion(movement, self.attitudes_by_time)
                                self._handle_motion(local, {t: self.attitudes_by_time[t] for t, *_ in movement})
                            except (ValueError, KeyError) as err:
                                self._log('Жест пропущен: ' + str(err))
                                continue
                elif kind == 'network_error':
                    self.live = False
                    self.segmenter.reset()
                    self.keyboard_on.set(False)  # Requires re-enabling after disconnect
                    self.status.set('ПОТЕРЯНА СВЯЗЬ')
                    self._log('Нет ответа от телефона: ' + event[1])
                elif kind == 'recovered':
                    self.session.reset()
                    self.segmenter.reset()
                    self.status.set('СОЕДИНЕНО')
                    self._update_expected()
                    self._log('Связь восстановлена. Управление нужно включить снова.')
                elif kind == 'fatal':
                    self._disconnect()
                    dialogs.showerror('Подключение не удалось', event[1] + '\n\nПроверь одну сеть Wi-Fi/роутер, Play, Remote Access и адрес с портом.')
                elif kind == 'stopped':
                    pass
        except queue.Empty:
            pass
        self.root.after(75, self._drain)

    def _train(self, kind):
        if not self.connected or not self.live:
            dialogs.showinfo('Нет датчика', 'Нужен активный phyphox с нажатой Play.')
            return
        self.keyboard_on.set(False)
        self.segmenter.reset()
        self.training = kind
        self.training_after = time.monotonic() + 1.0
        text = {'HOOK': 'ПОДСЕЧКУ', 'CAST': 'ЗАБРОС', 'NEGATIVE': 'НЕЖЕЛАТЕЛЬНОЕ ДВИЖЕНИЕ'}[kind]
        self.training_hint.set('Через секунду сделай одно движение: ' + text + '.')
        self._log('Запись ' + kind + ': через 1 секунду выполни одно движение.')

    def _delete_last(self, kind):
        if not self.templates[kind]:
            self._log('Нечего удалять: ' + kind)
            return
        self.templates[kind].pop()
        self.training = None
        self.keyboard_on.set(False)
        self._save()
        self._update_counts()
        self.training_hint.set('Последний пример ' + kind + ' удалён.')
        self._log('Последний пример ' + kind + ' удалён.')

    def _clear_kind(self, kind):
        name = {'HOOK': 'подсечки', 'CAST': 'заброса', 'NEGATIVE': 'нежелательных движений'}[kind]
        if not dialogs.askyesno('Удалить примеры', 'Удалить ВСЕ примеры ' + name + '?\n'
                                              'Примеры другого жеста сохранятся.'):
            return
        self.templates[kind] = []
        self.training = None
        self.keyboard_on.set(False)
        self._save()
        self._update_counts()
        self.training_hint.set('Примеры ' + name + ' удалены.')
        self._log('Примеры ' + kind + ' очищены отдельно.')

    def _clear_all(self):
        if not dialogs.askyesno('Удалить все примеры', 'Удалить ВСЕ образцы CAST, HOOK и NEGATIVE?'):
            return
        self.templates = {'CAST': [], 'HOOK': [], 'NEGATIVE': []}
        self.training = None
        self.keyboard_on.set(False)
        self._save()
        self._update_counts()
        self.training_hint.set('Все образцы удалены.')
        self._log('Все обучающие примеры удалены.')

    def _reset_state(self):
        self.session.reset()
        self.segmenter.reset()
        self._update_expected()
        self._log('Состояние сброшено — ожидается заброс.')

    def _handle_motion(self, motion, attitudes):
        now = time.monotonic()
        try:
            example, stats = make_example(motion, attitudes)
        except (ValueError, KeyError) as err:
            self._log('Не удалось собрать IMU-жест: ' + str(err))
            return
        rotation_path = stats['rotation_path_degrees']
        rotation = stats['rotation_peak_degrees']  # maximum angular excursion, not accumulated sensor jitter
        confirmed, phase_reason, phase_stats = cast_reversal(
            motion, self.values['min_reversal_speed'].get())
        max_rotation = self.values['hook_max_rotation_degrees'].get()
        if self.training is not None:
            if now < self.training_after:
                return
            name = self.training
            if name == 'CAST' and not confirmed:
                self.last.set('CAST НЕ СОХРАНЁН: ' + phase_reason)
                self.training_hint.set('Не записано: ' + phase_reason)
                self._log('Обучение CAST: отклонён — ' + phase_reason)
                return
            warnings = []
            if name == 'HOOK':
                # Save training examples even if one fails an in-game classification
                # gate. A real one-phase pull should never require a reversal.
                # Report potential problems rather than silently blocking learning.
                if rotation > max_rotation:
                    warnings.append(f'поворот {rotation:.0f}° выше лимита {max_rotation:.0f}°; жест может отклоняться в игре')
                if self.templates['HOOK']:
                    ok, why, _ = hook_direction_gate(example['acc'],
                        [e['acc'] for e in self.templates['HOOK']],
                        self.values['hook_direction_min_cosine'].get())
                    if not ok:
                        warnings.append(why + '; проверь хват или удали неподходящий пример')
            self.templates[name].append(example)
            self.templates[name] = self.templates[name][-12:]
            self.training = None
            self._save()
            self._update_counts()
            number = len(self.templates[name])
            note = (' ВНИМАНИЕ: ' + '; '.join(warnings)) if warnings else ''
            self.training_hint.set(f'Записан {name} #{number}. Желательно 5–8 примеров.' + note)
            self.last.set(f'ОБРАЗЕЦ {name} #{number} СОХРАНЁН' + (' ⚠' if warnings else ''))
            self._log(f'Обучение: {name} #{number}; макс. поворот {rotation:.0f}°, суммарный {rotation_path:.0f}°' + note)
            return
        if not self.templates['CAST'] or not self.templates['HOOK']:
            if now - self.last_no_templates > 6:
                self.last_no_templates = now
                self._log('Для распознавания нужны новые IMU-примеры CAST и HOOK.')
            return
        gesture, scores, cause = classify(
            example, self.templates, confirmed, rotation,
            cast_limit=self.values['cast_match_tolerance'].get(),
            hook_limit=self.values['hook_match_tolerance'].get(),
            negative_limit=self.values['negative_match_tolerance'].get(),
            direction_cosine=self.values['hook_direction_min_cosine'].get(),
            hook_rotation_limit=max_rotation,
            ambiguity=self.values['ambiguity_margin'].get())
        details = ' | '.join(f'{k}={v:.3f}' for k,v in scores.items())
        details += f' | вращение={rotation:.0f}°'
        if not confirmed:
            details += ' | CAST: ' + phase_reason
        if gesture is None:
            self.last.set(cause + '   |   ' + details)
            if now - self.last_reject > 1.4:
                self._log(cause + '   (' + details + ')')
                self.last_reject = now
            return
        self.last.set(f'{gesture}  •  {details}')
        if not self.keyboard_on.get():
            self._log('Тренировка: ' + gesture + ' (' + details + '); клавиша не отправлена.')
            return
        title = foreground_title()
        if not self.connected or not self.live:
            self._log('Не отправлено: телефон не передаёт данные.')
            return
        if 'motion fishing' in title.lower():
            self._log('Не отправлено: активно окно Motion Fishing.')
            return
        if self.only_wow.get() and 'world of warcraft' not in title.lower():
            self._log('Не отправлено: активно не окно WoW (' + title + ').')
            return
        ok, reason = self.session.validate(gesture, now)
        if not ok:
            self.last.set(f'{gesture}  •  ПРОПУЩЕНО: {reason}')
            self._log('Не отправлено: ' + reason + ' (' + details + ')')
            return
        try:
            tap(self.key.get())
        except Exception as err:
            self.keyboard_on.set(False)
            self.session.reset()
            self._update_expected()
            self._log('Ошибка клавиатуры: ' + str(err))
            return
        self.session.consume(gesture, now)
        self._update_expected()
        self._log(f'{gesture} → {self.key.get()}  •  {details}')

    def _close(self):
        if self.stop_event:
            self.stop_event.set()
        if self.save_after is not None:
            self.root.after_cancel(self.save_after)
        self._save()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
