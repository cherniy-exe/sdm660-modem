# Патчи ядра

| Файл | Статус | Что делает |
| --- | --- | --- |
| `0001-sdm660-ipa2-lite-modem-data-path.patch` | **НЕ ИСПОЛЬЗОВАТЬ** | Порт `ipa2-lite` на sdm660: собирается, но при загрузке вызывает hard LOCKUP CPU6 и RCU stall |
| `dpm-endpoint-swap.patch` |экспериментальный, собран в `7.2.15-sdm660` | DPM OPEN_PORT `tx=4/rx=5` вместо `tx=5/rx=4` |
| `wan-dl-filter-off.patch` |экспериментальный, установлен как `wanfix` | AP-side WAN DL-фильтры выключены по умолчанию (`wan_dl_filter=N`) |

Патчи применяются к дереву `qcom-sdm660-7.2.y` / ветке wip2 с уже
существующим портом IPA v2.6L; это **не** патчи для `ipa2-lite`.
Перед установкой любого варианта сохраните рабочие `/boot` и модули
(`docs/ROLLBACK.md`). Подробности диагностики — `docs/DATA-PATH.md`.
