# Модем SDM660 на mainline Linux

SIM, SMS и мобильный интернет на Redmi Note 7 без ModemManager/ofono.

**Статус (2026-11-21):** SIM, LTE, SMS и мобильный интернет работают.
Мобильные данные поднимаются на ядре `7.2.15-sdm660` с портом IPA v2.6L
(`wip2`) после трёх правок драйвера: DPM OPEN_PORT с AP-стороними endpoint-ами,
отключения AP-side WAN DL-фильтров и доставки нисходящих пакетов с не-cookie
тегом. Дополнительно нужны патч ModemManager (устранён цикл reprobe из-за
изменившегося ICCID), `qmap_mux_id=1` и холодный ребут после установки модуля.
Детали, проверки и patched-файлы — `docs/DATA-PATH.md`. Вариант `ipa2-lite`
признан нерабочим (hard LOCKUP CPU6) и не должен устанавливаться.

| Путь | Назначение |
| --- | --- |
| `docs/MODEM.md` | SIM/SMS через raw QMI по QRTR, проверки модема |
| `docs/DATA-PATH.md` | IPA v2.6L: хендшейк, ModemManager, причины RX=0, три правки ядра, инструменты |
| `docs/BRING-UP.md` | что проверено и почему `ipa2-lite` провалился |
| `docs/ROLLBACK.md` | возврат к рабочему ядру после неудачной сборки |
| `tools/` | SMS-клиент и GTK-GUI, сервис включения модема, сброс модема |
| `scripts/data-path/` | вендорский data-call, QMI-пробы, подготовка к ребуту |
| `etc/net-gui.desktop` | запуск сетевого GUI в Phosh |
| `patches/` | патчи IPA v2.6L и предупреждение про `ipa2-lite` |
| `config/` | опции ядра QRTR/RMNET/IPA/Q6V5 |
| `COPYING-kernel` | GPL-2.0 для кода ядра |

Код ядра GPL-2.0; оригинальные инструменты — MIT (`LICENSE`).
