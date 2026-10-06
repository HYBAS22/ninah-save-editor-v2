# NINAH Save Tool v2 — “No, I'm not a Human” save editor

Decrypt, view and edit (`.sav`) saves of
**[No, I'm not a Human](https://store.steampowered.com/app/3180070/No_Im_not_a_Human/)**

- **CLI** (`ninah_tool.py`): `find / dec / info / get / set / enc / verify / publish / backup / backups / restore`
- **Local web UI** (`ninah_gui.py`):
  Simple mode (resources, day & energy, people, house, story) +
  expert tree with *every* field of *every* controller, one-click snapshots
  and rollback

> Close the game before saving, or Steam Cloud will overwrite your edit

## How to run

1. Download `NINAHSaveEditor.exe` from [Releases](../../releases)
2. Double-click it, the editor opens in your browser by itself
3. Pick a save (found automatically), edit, press **Save**
4. Before risky experiments press **Backup**; rollback via snapshot list
   and the **Restore** button

## Install (from source)

```powershell
pip install -r requirements.txt
python ninah_tool.py find
```

## Build the .exe yourself

```powershell
pip install pyinstaller
build_exe.bat        # -> dist\NINAHSaveEditor.exe
```

## CLI

```powershell
python ninah_tool.py find # find saves
python ninah_tool.py info GameSaveData.sav # 16 controllers + fields
python ninah_tool.py get GameSaveData.sav ConsumablesController Storage.Bobeer
python ninah_tool.py set GameSaveData.sav ConsumablesController Storage.Bobeer 42
python ninah_tool.py publish GameSaveData.sav # push: file+registry+cloud
python ninah_tool.py backup --label before-experiments # full snapshot
python ninah_tool.py backups # list snapshots
python ninah_tool.py restore snap-20261006-000000 # roll back
python ninah_tool.py dec   GameSaveData.sav -o save.json # decrypt to JSON
python ninah_tool.py enc   save.json out.sav # encrypt back
python ninah_tool.py verify [GameSaveData.sav] # 3 independent checks
```

`set` takes JSON values (`true`, `5`, `"str"`, `[1,2]`) and paths like
`Storage.Bobeer`, `CharactersInside[0]`, `YarnBoolVariables.$teethCheck`.
`set` stages the edit into the file; `publish` pushes the result to file +
registry + cloud with per-target checks. Snapshots cover all stores at once.

## GUI

```powershell
python ninah_gui.py # opens http://127.0.0.1:PORT/
python ninah_gui.py GameSaveData.sav
```

## Key rotation

If the devs change the key, decryption fails with
`no key matched — Game key may have rotated`.
Add the new key to `keys.json` (`{"keys": ["<old>", "<new>"]}`) and pass
`--keys keys.json`

If you use the GUI build, just download the new version, I usually update the keys myself

## Credits

Based on: [juliangrtz/NINAHSaveEditor](https://github.com/juliangrtz/NINAHSaveEditor)
(C#, WinForms). I went with Python instead of C# to keep development simple

---

# NINAH Save Tool v2 — редактор сейвов «No, I'm not a Human»

Расшифровка, просмотр и правка сохранений (`.sav`) игры
**[No, I'm not a Human](https://store.steampowered.com/app/3180070/No_Im_not_a_Human/)**

- **CLI** (`ninah_tool.py`): `find / dec / info / get / set / enc / verify / publish / backup / backups / restore`
- **Локальный веб-интерфейс** (`ninah_gui.py`):
  Простой режим (ресурсы, день и энергия, люди, дом, сюжет) +
  Экспертное дерево со *всеми* полями *всех* контроллеров, снапшоты в один клик
  и откат

> Перед сохранением закрой игру, иначе Steam Cloud перезапишет правку

## Как запустить

1. Скачайте `NINAHSaveEditor.exe` из [Releases](../../releases)
2. Запустите двойным кликом и редактор откроется сам в браузере
3. Выберите сейв (найдётся сам), правь, жми **Save**
4. Перед рискованными экспериментами жмите **Backup**; доступен откат с выбором снапшота
   и кнопкой **Restore**

## Установка (из исходников)

```powershell
pip install -r requirements.txt
python ninah_tool.py find
```

## Собрать .exe самому

```powershell
pip install pyinstaller
build_exe.bat        # -> dist\NINAHSaveEditor.exe
```

## CLI

```powershell
python ninah_tool.py find # найти сейвы
python ninah_tool.py info GameSaveData.sav # 16 контроллеров + поля
python ninah_tool.py get GameSaveData.sav ConsumablesController Storage.Bobeer
python ninah_tool.py set GameSaveData.sav ConsumablesController Storage.Bobeer 42
python ninah_tool.py publish GameSaveData.sav # разослать: файл+реестр+облако
python ninah_tool.py backup --label до-экспериментов # полный снапшот
python ninah_tool.py backups # список снапшотов
python ninah_tool.py restore snap-20261006-000000 # откатить
python ninah_tool.py dec   GameSaveData.sav -o save.json # расшифровать в JSON
python ninah_tool.py enc   save.json out.sav # зашифровать обратно
python ninah_tool.py verify [GameSaveData.sav] # 3 независимые проверки
```

`set` принимает JSON-значения (`true`, `5`, `"str"`, `[1,2]`) и пути вида
`Storage.Bobeer`, `CharactersInside[0]`, `YarnBoolVariables.$teethCheck`.
`set` кладёт правку в файл; `publish` рассылает результат в файл + реестр +
облако с проверкой каждой цели. Снапшоты покрывают все хранилища сразу

## GUI

```powershell
python ninah_gui.py # откроется http://127.0.0.1:PORT/
python ninah_gui.py GameSaveData.sav
```

## Ротация ключей

Если разработчики сменят ключ, расшифровка упадёт с
`no key matched — Game key may have rotated`.
Добавьте новый ключ в `keys.json` (`{"keys": ["<old>", "<new>"]}`) и передайте
`--keys keys.json`

Если вы используете GUI версию, то просто скачайте свежую версию, скорее всего я уже успел обновить ключи

## Благодарности

За основу был взят проект: [juliangrtz/NINAHSaveEditor](https://github.com/juliangrtz/NINAHSaveEditor)
(C#, WinForms). Для более простой разработки был взят Python вместо C#
