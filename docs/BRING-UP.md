# Bring-up: IPA v2.6 на SDM660

## Что удалось проверить

Вариант **IPA wip2** (community-порт v2.6L): IPA инициализируется, BAM DMA
активен, `rmnet_ipa0` создаётся. В `dmesg`:

```
bam-dma-engine 14784000.dma-controller: IPA BAM: desc threshold 16, event threshold 16
ipa 147c0000.ipa: IPA driver initialized
ipa 147c0000.ipa: IPA driver setup completed successfully
ipa 147c0000.ipa: received modem starting/running event
```

Позднее, с dyndbg, включённым **до** загрузки модуля, подтверждён полный
хендшейк: `received IPA config request`, `DPM port mapping installed`,
`installed WAN DL filters` — то есть QMI/DPM/mux работают. Модем после
холодного ребута и патчей ModemManager уходит в `connected`/LTE,
`qmapmux0.0` получает IP из PDP-контекста. Но `RX` остаётся 0; свежая
диагностика и инструменты — `docs/DATA-PATH.md`.

## Провал варианта ipa2-lite

Сборка прошла успешно (`LITEBUILD-EXIT=0`, `CONFIG_QCOM_IPA2_LITE=m`); после
исправления vermagic через tag ядра сборка дала `7.2.15-sdm660`, модуль
`ipa2-lite.ko.zst` и DTB с узлом `qcom,ipa-lite-v2.6` (alias модуля
`of:N*T*Cqcom,ipa-lite-v2.6`). Ядро и `boot.img` были установлены на устройство
через `mkinitfs`/`boot-deploy`.

**При загрузке это ядро вызвало hard LOCKUP:**

```
watchdog: CPU5: Watchdog detected hard LOCKUP on CPU 6
RCU stall — затронуты CPU 0-3
BUG: soft lockup
```

Телефон перестал отвечать по SSH и ICMP. Вариант признан нерабочим; причина
lockup не установлена (нужен разбор DT-узла, IRQ/BAM и взаимодействия с
remoteproc). Патч оставлен в `patches/` с предупреждением, но **не рекомендуется
к установке**.

## Известные проблемы

- Нисходящие пакеты приходят на endpoint 6 (`MODEM_LAN_TX`), но отбрасываются
  как tagged (`unexpected tagged packet from endpoint 6`).
- `ath10k_snoc` на 7.2 без патчей роняет модем при отключении Wi-Fi; нужны
  патчи из [mest2011/redmi-note7-nura](https://github.com/mest2011/redmi-note7-nura).
- Слабый сигнал LTE на тестовом экземпляре проверять вне помещения.

## Проверки и откат

```bash
dmesg | grep -iE 'ipa|bam|lockup|watchdog|tagged' | tail -20
ip -o link show | grep -E 'rmnet|qmap'
ip -s link show qmapmux0.0 | grep -A2 'RX:'
qmicli -d qrtr://0 --nas-get-serving-system | grep 'Registration state'
mmcli -L
```

Порядок возврата к рабочему ядру — `docs/ROLLBACK.md`.
