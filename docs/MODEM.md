# Модем: SIM и SMS без ModemManager

На SDM660 нет mainline-драйвера сетевого порта модема, поэтому ModemManager
отбрасывает QMI-модем, а ofono может завести его в невосстановимое состояние.
Рабочий путь — raw QMI поверх QRTR (`tools/qmi_sms.py`, `tools/net-gui.py`).

Проверено: чтение IMEI, SIM ready, регистрация в LTE, приём и отправка SMS
(UCS2 для кириллицы). Нужны сервисы `msm-firmware-loader`, `rmtfs`,
`tqftpserv` и работающий remoteproc MSS.

Кратко о протоколе: адрес QRTR — `(node, port)`; поиск сервиса — пакет
`(10, service, 0, 0, 0)` на `(local_node, 0xfffffffe)`, ответ `NEW_SERVER`.
На QRTR нет QMUX-заголовка: кадр — `<BBHH> + TLV`. Сервисы: ctl=0, wds=1,
dms=2, nas=3, wms=5, uim=10; порты меняются после перезапуска модема.
WMS: list `0x0035`, read `0x0022`, send `0x0020`, delete `0x0034`.

Проверки на устройстве:

```bash
qmicli -d qrtr://0 --dms-get-ids
qmicli -d qrtr://0 --uim-get-card-status
qmicli -d qrtr://0 --nas-get-serving-system | grep 'Registration state'
python3 qmi_sms.py
```

Мобильные данные пока нестабильны: драйвер IPA v2.6 и диагностика — в
[sdm660-ipa2-lite](https://github.com/cherniy-exe/sdm660-ipa2-lite).
Если модем застрял в `offline`, помогает только полная перезагрузка; не
запускайте MM/ofono с циклической сменой режима на этой прошивке.
