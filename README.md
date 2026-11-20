# ipa2-lite для SDM660 (IPA v2.6)

Патч и заметки по порту драйвера `ipa2-lite` на mainline-ядро
`qcom-sdm660-7.2.y` (Redmi Note 7, SDM660).

**Статус:** модуль собирается, IPA инициализируется, `rmnet_ipa0` создаётся;
устойчивой передачи мобильных данных пока нет.

Стоковый `drivers/net/ipa` не поддерживает SDM660, поэтому ModemManager не
находит сетевой порт модема. `ipa2-lite` (из msm8953-mainline) закрывает IPA
v2.x и даёт MM интерфейс `rmnet_ipa0`.

## Файлы

| Путь | Назначение |
| --- | --- |
| `patches/0001-sdm660-ipa2-lite-modem-data-path.patch` | DT-узел `ipa@14780000`, Kconfig/Makefile, драйвер |
| `config/lavender-ipa2.fragment` | опции QRTR/RMNET/IPA/Q6V5 |
| `scripts/build-kernel.sh`, `scripts/install-kernel.sh` | сборка и установка ядра |
| `docs/BRING-UP.md` | проверки и известные проблемы |
| `COPYING-kernel` | GPL-2.0 |

## Применение

```bash
git clone --depth 1 --branch qcom-sdm660-7.2.15 \
  https://github.com/sdm660-mainline/linux.git kernel
cd kernel
git apply ../0001-sdm660-ipa2-lite-modem-data-path.patch
cp /path/to/device-config .config
../scripts/build-kernel.sh
```

Важно: `CONFIG_QCOM_IPA` выключить, `CONFIG_QCOM_IPA2_LITE=m` включить —
иначе в дереве останутся два драйвера.

Подтверждённый результат: `IPA driver initialized`, `setup completed
successfully`, события modem starting/running в `dmesg`; `rmnet_ipa0`
существует, modem регистрируется в LTE. Детали — `docs/BRING-UP.md`.

Драйвер `ipa2-lite` происходит из [msm8953-mainline/linux](https://github.com/msm8953-mainline/linux)
(commit `7213855948c70fd165356526f1de1c3b6bf4d554`); порт на SDM660 сделан
здесь. Код ядра — GPL-2.0 (`COPYING-kernel`).
