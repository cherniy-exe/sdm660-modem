# QRTR / QMI: выжимка для SDM660

Кратко о том, как общаться с модемом без ModemManager и почему это работает
именно так.

## Адресация и поиск сервисов

- `AF_QIPCRTR = 42`, `SOCK_DGRAM`. Адрес — кортеж `(node, port)`.
- `bind((0,0))` возвращает EINVAL; первого `sendto` достаточно для авто-привязки.
  Локальный node: `getsockname()`.
- Новый lookup: `struct.pack('<IIIII', 10, service, 0, 0, 0)` → `(local_node,
  0xfffffffe)`. Ответ: `NEW_SERVER` (cmd=4) с `(service, instance, node, port)`.
- Отправлять на node 0 или broadcast `0xffffffff` опасно — вызов может
  заблокироваться. Всегда используйте локальный node.
- Идентификаторы сервисов: `ctl=0`, `wds=1`, `dms=2`, `nas=3`, `wms=5`, `uim=10`.
- Порты меняются после перезапуска модема — делайте lookup заново при каждом
  подключении.

## Кадры QMI

На QRTR нет QMUX-заголовка (`qmi-endpoint-qrtr.c` в libqmi отправляет
"raw QRTR message without QMUX/QRTR header"). Формат запроса:

```
struct.pack('<BBHH', 0, txn, msg, len(tlvs)) + tlvs
TLV: type:u8 + len:u16le + value
```

Ответы сопоставляются по `(txn, msg)`; TLV `0x02` — ошибка: `err:u16le`,
`status:u16le` (0 = успех). CTL `Get Client ID` на QRTR не нужен: модем
идентифицирует клиента по исходному QRTR-порту, а CID в libqmi — локальный
счётчик.

## WMS (SMS)

| Операция | Msg ID | TLV |
| --- | --- | --- |
| List Messages | 0x0035 | in: storage u8 (0=UIM, 1=NV); out: массив `(index u32, tag u8)` |
| Raw Read | 0x0022 | in: storage + index u32; out: PDU bytes |
| Raw Send | 0x0020 | in: SMS-SUBMIT PDU; out: message id u16 |
| Delete | 0x0034 | in: storage + index |

PDU SMS-SUBMIT: `[0x00 (SMSC по умолчанию), 0x11, MR 0x00, digit-count +
0x91 (international) + BCD, PID 0x00, DCS, VP 0xA7, UDL, UD]`.
`DCS 0x08` = UCS2 (кириллица; UDL — число байт), `0x00` = GSM7 (UDL — число
септетов, 7-битная упаковка). BCD: младший младший полубайт, `0xa='*'`,
`0xb='#'`, нечётное число цифр дополняется `0xf`.

## Интеграция с ModemManager

- QRTR-модему нужен netdev-порт (`ipa`/`bam-dmux`), иначе MM отбрасывает
  устройство после успешной QMI-пробы. Отсюда и порт `ipa2-lite`.
- DBus-активация MM из Phosh/NM борется с openrc за имя
  `org.freedesktop.ModemManager1`. Для отладки: убрать `.service`-файл,
  `rc-service modemmanager stop; zap; start`, вернуть файл, добавить сервис
  в default runlevel.
- Отладочный лог: `/etc/conf.d/modemmanager` →
  `modemmanager_opts="--log-level=DEBUG --log-file=/tmp/mm.log --log-timestamps"`;
  перезапустить, прочитать файл (root-owned, `chmod 644`).
- `supervise-daemon` после лимита респавнов требует `rc-service <svc> zap`.

## Восстановление modem wedge

Если режим застрял в `offline`, любая смена режима даёт `InvalidTransition(60)`,
а stop/start remoteproc — таймаут: помогает только полная перезагрузка телефона.
Профилактика — не запускать ofono/MM с циклической сменой режима на этой
прошивке; держать модем в `online` через отдельный openrc-сервис после
`msm-firmware-loader` и `rmtfs`.
