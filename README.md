# Модем SDM660 на mainline Linux

SIM, SMS и экспериментальный мобильный интернет на Redmi Note 7 без
ModemManager/ofono.

**Статус (2026-11-21):** SIM, LTE и SMS работают. После холодного ребута и
патчей ModemManager модем переходит в `connected`, появляется `qmapmux0.0`
с IP из PDP-контекста, но `RX` остаётся 0: нисходящие пакеты приходят на
endpoint 6 и отбрасываются драйвером как tagged. Последняя находка и порядок
проверок — `docs/DATA-PATH.md`. Вариант `ipa2-lite` признан нерабочим
(hard LOCKUP CPU6) и не должен устанавливаться.

| Путь | Назначение |
| --- | --- |
| `docs/MODEM.md` | SIM/SMS через raw QMI по QRTR, проверки модема |
| `docs/DATA-PATH.md` | IPA v2.6L: хендшейк, ModemManager, RX=0, инструменты |
| `docs/BRING-UP.md` | что проверено и почему `ipa2-lite` провалился |
| `docs/ROLLBACK.md` | возврат к рабочему ядру после неудачной сборки |
| `tools/` | SMS-клиент и GTK-GUI, сервис включения модема, сброс модема |
| `scripts/data-path/` | вендорский data-call, QMI-пробы, подготовка к ребуту |
| `etc/net-gui.desktop` | запуск сетевого GUI в Phosh |
| `patches/` | патчи IPA v2.6L и предупреждение про `ipa2-lite` |
| `config/` | опции ядра QRTR/RMNET/IPA/Q6V5 |
| `COPYING-kernel` | GPL-2.0 для кода ядра |

Код ядра GPL-2.0; оригинальные инструменты — MIT (`LICENSE`).
