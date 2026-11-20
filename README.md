# Модем SDM660 на mainline Linux

SIM, SMS иэкспериментальный мобильный интернет на Redmi Note 7 без ModemManager/ofono.

| Путь | Назначение |
| --- | --- |
| `docs/MODEM.md` | SIM/SMS через raw QMI по QRTR, проверки модема |
| `docs/BRING-UP.md` | IPA v2.6: подтверждённыерезультаты и известные проблемы |
| `tools/` | SMS-клиент и GTK-GUI, сервис включения модема, сброс модема |
| `etc/net-gui.desktop` | запуск сетевого GUI в Phosh |
| `patches/` | патч `ipa2-lite` для ядра 7.2.y (DT-узел, драйвер) |
| `config/` | опции ядра QRTR/RMNET/IPA/Q6V5 |
| `scripts/` | сборка и установка ядра с IPA |
| `COPYING-kernel` | GPL-2.0 для кода ядра |

SIM, регистрация в LTE и SMS работают; передача данных через `rmnet_ipa0`
пока нестабильна. Драйвер `ipa2-lite` — из msm8953-mainline; код ядра GPL-2.0.
Оригинальные инструменты — MIT (`LICENSE`).
