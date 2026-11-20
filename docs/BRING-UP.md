# Bring-up: IPA v2.6 на SDM660

Хронология и текущее состояние экспериментов. Даты — 2026-11-20.

## 1. Исходная проблема

- `CONFIG_QCOM_IPA` в ядре `qcom-sdm660-7.2.15` не поддерживает SDM660:
  `ipa.ko` не имеет alias для sdm660, DT-узла `ipa` в `sdm630.dtsi` нет.
- ModemManager (`1.25.95`) видит QMI-модем через QRTR (`qrtr0`), но после
  успешного QMI-пробы отбрасывает его: «Failed to find a net port in the QMI
  modem». Метки udev на `rmnet*` не меняют ситуацию — порты группируются под
  фиктивным родителем и считаются виртуальными.
- ofono (`qrtrsoc`) требует ≥3 `rmnet_data*` + `rmnet_ipa*` с общим iflink;
  его включение сбрасывает ONLINE → LOW_POWER и может завести модем в состояние,
  из которого помогает только полная перезагрузка.

## 2. Что сделано

1. Из набора патчей msm8953/milohr взят `0026-net-add-the-ipa2-lite-driver-for-IPA-v2.x.patch`
   (драйвер из msm8953-mainline, коммит `7213855948...`). Патч применён к чистому
   `qcom-sdm660-7.2.15` (`patch -p1`, fuzz в Kconfig/Makefile).
2. В `sdm630.dtsi` добавлен узел `ipa@14780000` (IRQ 333/432, `RPM_SMD_IPA_CLK`,
   `qcom,ipa-lite-v2.6`, `modem-remoteproc = <&remoteproc_mss>`).
3. Конфигурация: `CONFIG_QCOM_IPA` выключен, `CONFIG_QCOM_IPA2_LITE=m`;
   QRTR/RMNET/Q6V5/firmware-loader/RPMSG включены (см. `config/`).
4. Собраны и установлены два варианта:

   - **wip2** — полный IPA с QMI-хендшейком и IP-настройками. Работает инициализация
     IPA, modem-side часть оставалась проблемной. Перед переходом к следующему
     варианту состояние `/boot` и модулей сохранено на ПК для отката.
   - **ipa2-lite** — урезанный драйвер, `CONFIG_QCOM_IPA2_LITE=m`. Сборка шла через
     clang-19 (`LLVM=-19`), `-j8`; на момент публикации проверка на устройстве
     продолжалась.

## 3. Результат, который удалось подтвердить

dmesg после загрузки wip2:

```
[    1.140160] bam-dma-engine 14784000.dma-controller: IPA BAM: desc threshold 16, event threshold 16
[   21.334101] ipa 147c0000.ipa: IPA driver initialized
[   21.337175] ipa 147c0000.ipa: IPA driver setup completed successfully
[   25.207423] ipa 147c0000.ipa: received modem starting event
[   26.740560] ipa 147c0000.ipa: received modem running event
```

Сетевой интерфейс: `3: rmnet_ipa0: <...> state DOWN`, udev:
`ID_MM_CANDIDATE=1`, `ID_MM_PHYSDEV_UID=qcom-soc`, `ID_MM_QCOM_SOC=1`.
Модем: `Mode: 'online'`, `Registration state: 'registered'`, `[0]: 'lte'`.
Сигнал был очень слабым (`-125 dBm`), что тоже мешало проверке данных.

После перезапуска ModemManager (с временно убранным D-Bus `.service`-файлом,
иначе Phosh/dbus-activation вызывает crash-loop) modem появляется:

```
/org/freedesktop/ModemManager1/Modem/0 [QUALCOMM INCORPORATED] 0
```

но затем уходит `enabling → enabled → disabling → disabled` с
`couldn't build device ids: Unknown device subsystem` и
`failed checking whether autoconnect is disabled or not: QMI protocol error (70): InvalidOperation`.

## 4. Открытые вопросы

- Приclamation IP-пакетов от модема в `rmnet_ipa0` (QMI WDS `WDS_GET_RUNTIME_SETTINGS` /
  IP configuration) — на стороне модема/ userspace.
- Стабильность: вай-фай (`ath10k_snoc`) на 7.2 без патчей роняет модем при
  каждом отключении; на 7.2 нужны два патча `ath10k` из
  [mest2011/redmi-note7-nura](https://github.com/mest2011/redmi-note7-nura)
  (`docs/wifi.md` в исходном проекте).
- Слабый сигнал LTE на тестовом экземпляре: проверять с SIM вне помещения.
- Модуль `ipa2-lite` требует проверки `modinfo ... | grep alias` и
  `ip link show rmnet_ipa0` после свежей установки.

## 5. Полезные команды

```bash
dmesg | grep -iE 'ipa|bam|qmi|modem' | tail -20
ip -o link show | grep -E 'rmnet|wwan'
udevadm info /sys/class/net/rmnet_ipa0 | grep -E 'ID_MM|DRIVER|DEVTYPE'
qmicli -d qrtr://0 --dms-get-operating-mode
qmicli -d qrtr://0 --nas-get-serving-system | grep 'Registration state'
mmcli -L
logread | grep -i ModemManager | tail -20
```
