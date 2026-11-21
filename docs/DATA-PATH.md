# Мобильные данные: диагностика IPA v2.6L на SDM660

Актуальное состояние на 2026-11-21. Это разбор цены ошибки между «модем зарегистрирован»
и «есть интернет». Ядро — community-порт IPA v2.6L (`setotau/qcom-sdm660-7.2.y-ipa2-wip2`),
не `ipa2-lite`: последний компилируется, но вызывает hard LOCKUP CPU6 и не должен
ставиться на это устройство.

## Цепочка симптомов

1. Стоковое ядро: SIM, регистрация, сигнал и SMS через raw QMI работают; сетевого
   порта модема нет, ModemManager modem не создаёт.
2. С ядром wip2: `IPA driver initialized`, `setup completed`, BAM DMA активен,
   `rmnet_ipa0` создаётся, модем регистрируется в LTE — но IPv4-настроек,
   DHCP и трафика нет; MM создаёт modem и перезапрашивает его в цикле.
3. После часов проб все QMI-сервисы модема (WDS, WMS, IPA INIT_DRIVER) начали
   отвечать `FAILURE, error 2 = NoMemory`. Полный power-off/холодный ребут
   перезапустил MSS и снял это состояние.

## Что реально помогло

- **Холодный ребут** (действие пользователя) —решающий фактор против `NoMemory`.
- **Патчи бинарника ModemManager** (на устройстве нет компилятора; aarch64-код
  правлен напрямую и проверен `llvm-objdump-19`):
  - `mm_shared_qmi_setup_sim_hot_swap()` → `mov w1,#1; b g_task_return_boolean@plt`
    (не регистрируем UIM slot/refresh-индикации);
  - `mm_iface_modem_process_sim_event()` (смещение `0xb5170` в сборке
    `1.25.95_git20261005`) → `ret`: прошивка сообщает изменившийся ICCID при
    обычной загрузке SIM, что вызывало бесконечный override Disable → reprobe.
    Сама загрузка SIM не тронута.
- **Временный udev-заместитель** `dummy0` с тегами `ID_MM_QCOM_SOC=1`,
  `ID_MM_PHYSDEV_UID=qcom-soc`, `ID_MM_CANDIDATE=1`, `ID_MM_PORT_TYPE_QMI=1`:
  MM требует хотя бы один `net`-порт в устройстве qcom-soc. Удалить правило и
  `dummy0`, когда `rmnet_ipa0` снова появится.
- **dyndbg до события**: `echo 'module ipa +pflt' > /sys/kernel/debug/dynamic_debug/control`
  после загрузки бесполезен — сообщения хендшейка уже прошли. Включать через
  modprobe/udev до хендшейка; `qmap_mux_id=1` должен совпадать с mux_id MM.

## Коррекция более раннего вывода

Полный хендшейк **есть**, если ловить его с самого старта:
`received IPA config request`, `install filter rule request (24 specs)`,
`installed WAN DL filters`, `DPM port mapping installed (tx 5 rx 4)`.
То есть QMI, DPM и mux в порядке; разрыв — в user plane.

## Разрыв user plane и его устранение

`qmapmux0.0@rmnet_ipa0` поднимался и получал IP из PDP-контекста APN, MM
показывал `connected`/LTE/attached, но счётчик `RX` оставался 0 при растущем
`TX`, а `ping -I qmapmux0.0 ...` давал 100% loss. QMI-хендшейк при этом был
полным — значит дело было не в модеме, а в обработке нисходящих пакетов.

В `dmesg` повторялось:

```
ipa 147c0000.ipa: unexpected tagged packet from endpoint 6
```

Endpoint 6 в `ipa_data-v2.5.c` — `IPA_ENDPOINT_MODEM_LAN_TX`: пакеты от модема
реально приходили. `ipa_endpoint_status_tag_valid()` считал ошибкой любой
тег, тогда как cookie-тег — это только маркер синхронизации конвейера, а
прошивка v2.6L помечает обычные нисходящие данные не-cookie тегом. Пакеты
отбрасывались драйвером; отсюда «IP есть, TX идёт, RX ноль».

Исправление — `patches/rxfix-tagged-downlink.patch`: cookie-тег по-прежнему
отбрасывается как sync marker, пакеты с другим тегом отдаются как данные.
После установки пересобранного `ipa.ko` и холодного ребута пользователь
подтвердил, что мобильный интернет работает. Полный рабочий набор правок
ядра — DPM OPEN_PORT с AP-стороними endpoint-ами, отключение AP-side WAN
DL-фильтров и доставка пакетов с не-cookie тегом.

## Опубликованные патчи ядра

| Патч | Статус | Суть |
| --- | --- | --- |
| `patches/dpm-endpoint-swap.patch` | собран в `7.2.15-sdm660` | DPM OPEN_PORT: `tx=4/rx=5` вместо `tx=5/rx=4` (как в вендорском QMI-логе SDM636 / IPA v2.6L) |
| `patches/wan-dl-filter-off.patch` | собран в `7.2.15-sdm660` | Не ставить AP-стороние WAN DL-фильтры по умолчанию (`wan_dl_filter=N`) — на v2.6L их ставит модем |
| `patches/rxfix-tagged-downlink.patch` | собран в `7.2.15-sdm660` | Доставлять нисходящие пакеты с не-cookie тегом вместо сброса; cookie-тег остаётся sync marker |

Все три правки собраны в одно ядро `7.2.15-sdm660`; после установки модуля
`ipa.ko.zst` и холодного перезапуска телефона пользователь подтвердил
работающий мобильный интернет. Ядро можно собрать заново по
`scripts/build-kernel.sh`, установку производить только с бэкапом
(`docs/ROLLBACK.md`).

## Инструменты

`scripts/data-path/` (копируются на устройство; `qmi_sms.py` из `tools/` должен
быть в `/usr/local/bin`):

- `vendor-call.py` — вендорская последовательность WDA/DPM/WDS с удержанием
  WDS-сокета; APN берётся из `APN`, по умолчанию публичный APN оператора;
- `mobile-up.sh` — поднимает `qmapmux0.0`, адрес/шлюз из `/tmp/vendor-call.state`,
  DNS только из состояния bearer;
- `dpm-fix.py`, `wda-set.py` — точечные QMI-запросы для проверки DPM/формата данных;
- `next-boot-setup.sh` — `qmap_mux_id=1`, dyndbg на загрузке модуля, восстановление
  D-Bus-файла ModemManager;
- `hw-state.sh`, `ipv4call.sh` — снятие состояния и IPv4-call для проверки.

## Что не помогало (не повторять)

`qmicli --dms-set-operating-mode=reset` (успех, состояние не меняется),
остановка MM/qmi-proxy, QRTR DEL_CLIENT, `rmmod ipa` на минуты, QMUX-обёртки
для WDS, WDS STOP_NETWORK, `rmmod/modprobe ipa` (netdev `rmnet_ipa0` после этого
не возвращается — только холодный ребут). `ipa2-lite` не ставить.

Ссылка на вендорский материал, который использовался как ориентир:
`miraro/postmarketos-x00td-cellular` (`vendor-init/stage_dpm_open.c`,
`POSTMARKETOS_X00TD_CELLULAR.md`).
