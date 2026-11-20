#!/usr/bin/env python3
"""Мобильная сеть: статус SIM/сети + SMS через raw QMI (без ModemManager)."""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
import subprocess, threading, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qmi_sms import Qmi, QmiError, decode_pdu

def qmicli_status():
    try:
        r = subprocess.run(['qmicli', '-d', 'qrtr://0',
                            '--nas-get-operator-name', '--nas-get-serving-system',
                            '--nas-get-signal-strength', '--uim-get-card-status'],
                           capture_output=True, text=True, timeout=20)
        out = r.stdout
        st = {}
        m = re.search(r"Name\s*:\s*'([^']*)'", out)
        st['operator'] = m.group(1) if m else '—'
        m = re.search(r"Registration state:\s*'([^']*)'", out)
        st['reg'] = m.group(1) if m else '—'
        m = re.search(r"Radio interfaces:.*?\[0\]:\s*'([^']*)'", out, re.S)
        st['radio'] = m.group(1) if m else ''
        m = re.search(r"Network '(?:lte|gsm|umts|none)':\s*'(-?\d+) dBm'", out)
        st['dbm'] = int(m.group(1)) if m else None
        m = re.search(r"Card state:\s*'([^']*)'", out)
        st['sim'] = m.group(1) if m else '—'
        m = re.search(r"PIN1 state:\s*'([^']*)'", out)
        st['pin'] = m.group(1) if m else ''
        return st
    except Exception:
        return {}

def signal_level(dbm):
    if dbm is None or dbm <= -120:
        return 'нет сигнала'
    if dbm >= -75: return 'отличный'
    if dbm >= -85: return 'хороший'
    if dbm >= -95: return 'средний'
    if dbm >= -105: return 'слабый'
    return 'очень слабый'

REG_RU = {'registered': 'зарегистрирован', 'not-registered': 'не зарегистрирован',
          'not-registered-searching': 'поиск сети', 'registration-denied': 'отказано',
          'unknown': 'неизвестно'}
SIM_RU = {'present': 'вставлена', 'absent': 'нет SIM', 'error': 'ошибка'}

class NetApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.nura.netgui')
        self.busy = False
        self.qmi = None
        self.messages = []

    def do_activate(self):
        self.win = Adw.Window(application=self, title='Мобильная сеть',
                              default_width=390, default_height=720)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hb = Adw.HeaderBar()
        rb = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='Обновить')
        rb.connect('clicked', lambda *_: self.refresh_all())
        hb.pack_start(rb)
        cb = Gtk.Button(icon_name='mail-send-symbolic', tooltip_text='Написать SMS')
        cb.connect('clicked', lambda *_: self.compose())
        hb.pack_end(cb)
        box.append(hb)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=12, margin_start=12, margin_end=12, margin_bottom=12)

        g1 = Adw.PreferencesGroup(title='Состояние')
        self.row_op = Adw.ActionRow(title='Оператор', subtitle='…')
        self.row_reg = Adw.ActionRow(title='Сеть', subtitle='…')
        self.row_sig = Adw.ActionRow(title='Сигнал', subtitle='…')
        self.row_sim = Adw.ActionRow(title='SIM-карта', subtitle='…')
        for r in (self.row_op, self.row_reg, self.row_sig, self.row_sim):
            g1.add(r)
        inner.append(g1)

        g2 = Adw.PreferencesGroup(title='SMS')
        self.sms_status = Adw.ActionRow(title='Загрузка…', subtitle='')
        g2.add(self.sms_status)
        self.sms_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                    css_classes=['boxed-list'])
        self.sms_list.connect('row-activated', self.on_sms_open)
        g2.add(self.sms_list)
        inner.append(g2)
        scroll.set_child(inner)
        box.append(scroll)
        self.win.set_content(box)
        self.win.present()
        self.refresh_all()
        GLib.timeout_add_seconds(20, self._auto_refresh)

    def _auto_refresh(self):
        self.refresh_status()
        return True

    def refresh_all(self):
        self.refresh_status()
        self.refresh_sms()

    def refresh_status(self):
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._fetch_status, daemon=True).start()

    def _fetch_status(self):
        st = qmicli_status()
        GLib.idle_add(self._apply_status, st)

    def _apply_status(self, st):
        self.busy = False
        if not st:
            self.row_op.set_subtitle('модем недоступен')
            return
        self.row_op.set_subtitle(st.get('operator', '—'))
        reg = REG_RU.get(st.get('reg', ''), st.get('reg', '—'))
        radio = st.get('radio', '')
        self.row_reg.set_subtitle(reg + (f' ({radio.upper()})' if radio and radio != 'none' else ''))
        dbm = st.get('dbm')
        self.row_sig.set_subtitle(f'{dbm} dBm — {signal_level(dbm)}' if dbm is not None else '—')
        sim = SIM_RU.get(st.get('sim', ''), st.get('sim', '—'))
        pin = st.get('pin', '')
        if pin and pin not in ('disabled', 'enabled-not-verified'):
            sim += f', PIN: {pin}'
        self.row_sim.set_subtitle(sim)

    def refresh_sms(self):
        threading.Thread(target=self._fetch_sms, daemon=True).start()

    def _fetch_sms(self):
        msgs = []
        err = None
        try:
            if self.qmi is None:
                self.qmi = Qmi()
            for storage in (0, 1):
                try:
                    for idx, tag in self.qmi.sms_list(storage):
                        m = self.qmi.sms_read(idx, storage)
                        if m:
                            m['idx'] = idx
                            m['storage'] = storage
                            msgs.append(m)
                except QmiError:
                    pass
        except Exception as e:
            err = str(e)
        GLib.idle_add(self._apply_sms, msgs, err)

    def _apply_sms(self, msgs, err):
        self.messages = msgs
        while True:
            row = self.sms_list.get_row_at_index(0)
            if row is None:
                break
            self.sms_list.remove(row)
        if err:
            self.sms_status.set_title('SMS недоступны')
            self.sms_status.set_subtitle(err[:60])
        else:
            self.sms_status.set_title(f'Входящие: {len(msgs)}')
            self.sms_status.set_subtitle('нажмите на сообщение, чтобы прочитать')
        for m in msgs:
            r = Adw.ActionRow(title=m.get('number', '?'),
                              subtitle=(m.get('time', '') + '  ' + m.get('text', '')[:40]))
            r.msg = m
            r.set_activatable(True)
            self.sms_list.append(r)

    def on_sms_open(self, _lb, row):
        m = row.msg
        d = Adw.Window(title=m.get('number', 'SMS'), default_width=360, default_height=400,
                       modal=True, transient_for=self.win)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_start=12, margin_end=12, margin_bottom=12)
        hb = Adw.HeaderBar()
        box.append(hb)
        lbl = Gtk.Label(label=m.get('text', ''), wrap=True, xalign=0,
                        selectable=True, vexpand=True)
        box.append(lbl)
        meta = Gtk.Label(label=f"{m.get('time','')} • {m.get('number','')}",
                         css_classes=['dim-label'], xalign=0)
        box.append(meta)
        bb = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        delb = Gtk.Button(label='Удалить', css_classes=['destructive-action'])
        delb.connect('clicked', lambda *_: self._delete_sms(m, d))
        bb.append(delb)
        box.append(bb)
        d.set_content(box)
        d.present()

    def _delete_sms(self, m, dlg):
        def work():
            try:
                self.qmi.sms_delete(m['idx'], m['storage'])
            except Exception:
                pass
            GLib.idle_add(dlg.close)
            GLib.idle_add(self.refresh_sms)
        threading.Thread(target=work, daemon=True).start()

    def compose(self):
        d = Adw.Window(title='Новое SMS', default_width=360, default_height=420,
                       modal=True, transient_for=self.win)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_start=12, margin_end=12, margin_bottom=12)
        box.append(Adw.HeaderBar())
        num = Adw.EntryRow(title='Номер (+7…)')
        box.append(num)
        tv = Gtk.TextView(vexpand=True, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                          top_margin=8, bottom_margin=8, left_margin=8, right_margin=8)
        tv.get_buffer().set_text('')
        fr = Gtk.Frame()
        fr.set_child(tv)
        box.append(fr)
        st = Gtk.Label(label='', css_classes=['dim-label'], xalign=0)
        box.append(st)
        send = Gtk.Button(label='Отправить', css_classes=['suggested-action'])
        def on_send(*_):
            number = num.get_text().strip()
            text = tv.get_buffer().get_text(tv.get_buffer().get_start_iter(),
                                            tv.get_buffer().get_end_iter(), False)
            if not number or not text:
                st.set_text('Введите номер и текст')
                return
            st.set_text('Отправка…')
            send.set_sensitive(False)
            def work():
                try:
                    if self.qmi is None:
                        self.qmi = Qmi()
                    mid = self.qmi.sms_send(number, text)
                    GLib.idle_add(lambda: (st.set_text(f'Отправлено (id {mid})'),
                                           send.set_sensitive(True)))
                    GLib.timeout_add(1500, lambda: d.close() or False)
                except Exception as e:
                    GLib.idle_add(lambda: (st.set_text(f'Ошибка: {e}'),
                                           send.set_sensitive(True)))
            threading.Thread(target=work, daemon=True).start()
        send.connect('clicked', on_send)
        box.append(send)
        d.set_content(box)
        d.present()

if __name__ == '__main__':
    NetApp().run(None)