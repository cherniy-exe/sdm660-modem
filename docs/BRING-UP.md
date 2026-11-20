# Bring-up: IPA v2.6 на SDM660

## Подтверждённое

Ядро `7.2.15-sdm660` с `CONFIG_QCOM_IPA2_LITE=m` собирается и грузится.
В `dmesg`:

```
bam-dma-engine 14784000.dma-controller: IPA BAM: desc threshold 16, event threshold 16
ipa 147c0000.ipa: IPA driver initialized
ipa 147c0000.ipa: IPA driver setup completed successfully
ipa 147c0000.ipa: received modem starting/running event
```

`rmnet_ipa0` создаётся; udev: `ID_MM_CANDIDATE=1`, `ID_MM_QCOM_SOC=1`.
Модем: `online`, `registered`, LTE. ModemManager может увидеть модем после
перезапуска, но пока сбрасывает его `enabled → disabling → disabled`.

## Известные проблемы

- Передача IP-пакетов от модема в `rmnet_ipa0` (QMI WDS / IP-конфигурация).
- `ath10k_snoc` на 7.2 без патчей роняет модем при отключении Wi-Fi; нужны
  патчи из [mest2011/redmi-note7-nura](https://github.com/mest2011/redmi-note7-nura).
- Слабый сигнал LTE на тестовом устройстве проверять вне помещения.

## Проверки

```bash
dmesg | grep -iE 'ipa|bam' | tail -12
ip -o link show | grep rmnet
udevadm info /sys/class/net/rmnet_ipa0 | grep ID_MM
qmicli -d qrtr://0 --nas-get-serving-system | grep 'Registration state'
mmcli -L
```
