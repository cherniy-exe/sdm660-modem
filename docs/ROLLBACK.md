# Откат после неудачного ядра

Перед каждым экспериментом с IPA сохраняйте рабочее состояние: `boot.img`,
`vmlinuz`, DTB и каталог `/lib/modules/<version>`. В рассматриваемом случае
бэкап рабочего варианта (IPA wip2) лежал в
`~/redmi-note7-linux/kernel-backup/wip2/`:

- `boot.img` — md5 `84186fe4de037bba41dd7b0c484a5d71`;
- `vmlinuz`, `dtbs-tianma.dtb`, `modules.tar.gz`.

## Быстрый путь — fastboot

1. Принудительно выключить телефон (Power 15–20 с), если он висит в панике.
2. Войти в fastboot: **Vol− + Power**.
3. Проверить `fastboot devices`, затем:
   ```bash
   fastboot flash boot /path/to/backup/boot.img
   fastboot reboot
   ```
4. После загрузки восстановить модули:
   ```bash
   tar -xzf modules.tar.gz -C /lib/modules
   depmod <version>
   mkinitfs
   ```

## Через TWRP

`adb push` + `dd` в `boot` может оборваться, а `adb sideload` — прерваться на
нескольких процентах, если TWRP отваливается на нестабильном USB. Если
используете sideload, соберите zip с `META-INF/com/google/android/update-binary`
и `boot.img` внутри и проверьте, что устройство остаётся в режиме sideload до
конца передачи. Надёжнее всего — fastboot.

## Проверка после отката

```bash
uname -r
ip -o link show | grep rmnet
qmicli -d qrtr://0 --dms-get-operating-mode
qmicli -d qrtr://0 --nas-get-serving-system | grep 'Registration state'
```

Ожидаемое состояние: SIM/SMS/VPN работают, модем зарегистрирован в LTE;
мобильные данные — по-прежнему открытый вопрос.
