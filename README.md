# SDM660: порт ipa2-lite для модемного	data-пути (IPA v2.6)

Экспериментальный репозиторий: адаптация драйвера `ipa2-lite` (из
msm8953-mainline) для mainline-ядра `qcom-sdm660-7.2.y` на Redmi Note 7
(lavender, SDM660, панель Tianma).

**Статус на момент публикации (2026-11-20): work in progress.** Модуль
собирается и загружается, IPA инициализируется, `rmnet_ipa0` создаётся, модем
регистрируется в LTE; устойчивой подачи мобильных данных ещё нет. Работа
продолжается в параллельной сессии — снимок — снимок текущего состояния,
а не финальный релиз.

## Зачем

Стоковый mainline `drivers/net/ipa` не поддерживает SDM660: в `modinfo ipa`
нет совместимого alias, DT-узла `ipa` в `sdm630.dtsi` нет. Из-за отсутствия
сетевого порта ModemManager отбрасывает QMI-модем («Failed to find a net port»).
`ipa2-lite` — компактный драйвер IPA v2.x, который поднимает `rmnet_ipa0` и даёт
MM нужный сетевой порт.

## Содержимое

| Путь | Назначение |
| --- | --- |
| `patches/0001-sdm660-ipa2-lite-modem-data-path.patch` | DT-узел `ipa@14780000`, хуки Kconfig/Makefile, драйвер `drivers/net/ipa2-lite/*` |
| `config/lavender-ipa2.fragment` | Опции ядра для QRTR/RMNET/IPA/Q6V5/firmware loader |
| `scripts/build-kernel.sh` | Воспроизводимая команда сборки (clang-19, LLVM=19, toolchain) |
| `scripts/install-kernel.sh` | Установка собранного ядра на устройство + mkinitfs |
| `docs/BRING-UP.md` | Что проверено, логи, открытые вопросы |
| `docs/PROTOCOL.md` | Выжимка по QRTR/QMI и интеграции с ModemManager |
| `COPYING-kernel` | GPL-2.0 — лицензия кода ядра |

## Применение

База — чистый клон ветки `qcom-sdm660-7.2.15` репозитория
[sdm660-mainline/linux](https://github.com/sdm660-mainline/linux):

```bash
git clone --depth 1 --branch qcom-sdm660-7.2.15 \
  https://github.com/sdm660-mainline/linux.git kernel
cd kernel
git apply ../0001-sdm660-ipa2-lite-modem-data-path.patch
cp /path/to/device-config .config
../scripts/build-kernel.sh
```

Патч добавляет:

- `arch/arm64/boot/dts/qcom/sdm630.dtsi`: узел `ipa: ipa@14780000` с
  `compatible = "qcom,ipa-lite-v2.6"`, регистром `0x14780000..0x4effc`,
  `RPM_SMD_IPA_CLK`, IRQ 333 (ipa) и 432 (dma), `modem-remoteproc =
  <&remoteproc_mss>`;
- `drivers/net/Kconfig` / `Makefile`: `CONFIG_QCOM_IPA2_LITE`;
- `drivers/net/ipa2-lite/`: Kconfig, Makefile, `ipa.c`, `ipa.h`, `ipa-hw.h`,
  `ipa-qmi.c` (код из msm8953-mainline).

Важно: `CONFIG_QCOM_IPA` нужно **выключить** (`./scripts/config --disable
QCOM_IPA --module QCOM_IPA2_LITE`), иначе в дереве останутся два драйвера.

## Что проверено

Собрано ядро `7.2.15-sdm660` с `CONFIG_QCOM_IPA2_LITE=m`. Логи с устройства
после установки варианта с QMI-хендшейком:

```
bam-dma-engine 14784000.dma-controller: IPA BAM: desc threshold 16, event threshold 16
ipa 147c0000.ipa: IPA driver initialized
ipa 147c0000.ipa: IPA driver setup completed successfully
ipa 147c0000.ipa: received modem starting event
ipa 147c0000.ipa: received modem running event
```

`rmnet_ipa0` создан; udev-атрибуты `ID_MM_CANDIDATE=1`, `ID_MM_PHYSDEV_UID=qcom-soc`,
`ID_MM_QCOM_SOC=1` присутствуют; после перезапуска ModemManager modem
появляется в `mmcli -L`. Модем: `Mode: 'online'`, `registered`, `lte`.

Детали и открытые вопросы — `docs/BRING-UP.md`.

## Происхождение и лицензии

`ipa2-lite` взят из [msm8953-mainline/linux](https://github.com/msm8953-mainline/linux)
(commit `7213855948c70fd165356526f1de1c3b6bf4d554`) через набор патчей проекта
milohr;адаптация для SDM660 (DT-узел, конфигурация, сборка, диагностика)
сделана здесь. Код ядра — GPL-2.0 (см. `COPYING-kernel`). Модуль `ipa2-lite`
оригинально написан contributor'ами порта Xiaomi Mi MIX Linux.
