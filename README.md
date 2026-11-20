# Модем SDM660 на mainline Linux

SIM, SMS и экспериментальный мобильный интернет на Redmi Note 7 без
ModemManager/ofono.

**Статус (2026-11-20):** SIM, регистрация в LTE и SMS работают. Вариант с
`ipa2-lite` собран и установлен, но при загрузке вызвал hard LOCKUP CPU и RCU
stall — признан неудачным, выполняется откат на предыдущее рабочее ядро
(IPA wip2). Патч оставляется только как experimentный материал с предупреждением.

| Путь | Назначение |
| --- | --- |
| `docs/MODEM.md` | SIM/SMS через raw QMI по QRTR, проверки модема |
| `docs/BRING-UP.md` | IPA v2.6: что проверено и почему вариант провалился |
| `docs/ROLLBACK.md` | как вернуть рабочее ядро после неудачной сборки |
| `tools/` | SMS-клиент и GTK-GUI, сервис включения модема, сброс модема |
| `etc/net-gui.desktop` | запуск сетевого GUI в Phosh |
| `patches/` | патч `ipa2-lite` (НЕ для ежедневного использования) |
| `config/` | опции ядра QRTR/RMNET/IPA/Q6V5 |
| `scripts/` | сборка и установка ядра с IPA |
| `COPYING-kernel` | GPL-2.0 для кода ядра |

Драйвер `ipa2-lite` — из msm8953-mainline; код ядра GPL-2.0.
Оригинальные инструменты — MIT (`LICENSE`).
