# 📤 Публикация ENPAF в PyPI

Пошаговая инструкция, как собрать пакет и выложить его в
[PyPI](https://pypi.org), чтобы его можно было ставить через `pip install enpaf`.

---

## 0. Подготовка (один раз)

### Аккаунты и токены

1. Зарегистрируйтесь на **PyPI**: https://pypi.org/account/register/
2. (Рекомендуется) Зарегистрируйтесь на **TestPyPI**: https://test.pypi.org/account/register/ — это «песочница» для проверки.
3. Включите 2FA и создайте **API-токены**:
   - PyPI → Account settings → *API tokens* → *Add API token* (scope: «Entire account» для первой загрузки).
   - То же на TestPyPI.
   - Токен выглядит как `pypi-AgEIcHl...` — скопируйте сразу, он показывается один раз.

### Проверьте, что имя свободно

Имя `enpaf` должно быть свободно на PyPI. Откройте https://pypi.org/project/enpaf/ —
если страница существует, имя занято: поменяйте `name = "..."` в `pyproject.toml`
(например, `enpaf-framework`) и `Homepage`/`Documentation` при необходимости.

### Установите инструменты сборки

```bash
pip install build twine
```

или, если вы ставили проект из исходников:

```bash
pip install -e ".[dev]"
```

---

## 1. Обновите версию

PyPI **не позволяет повторно загрузить** уже существующую версию. Перед каждой
публикацией поднимайте `version` в `pyproject.toml`:

```toml
[project]
version = "1.0.1"   # было 1.0.0
```

Версии — по [SemVer](https://semver.org): `MAJOR.MINOR.PATCH`.

---

## 2. Соберите дистрибутивы

Из корня проекта (где лежит `pyproject.toml`):

```bash
python -m build
```

В каталоге `dist/` появятся два файла:

```
dist/
├── enpaf-1.0.1-py3-none-any.whl   # wheel (бинарный дистрибутив)
└── enpaf-1.0.1.tar.gz             # sdist (исходный дистрибутив)
```

> Совет: перед сборкой очистите старое — удалите каталог `dist/` (а лучше держите
> его в `.gitignore`).

---

## 3. Проверьте пакет

```bash
twine check dist/*
```

Должно быть `PASSED` для обоих файлов. Это проверяет корректность метаданных и
описания (README рендерится как long description).

(Опционально) Загляните внутрь wheel, чтобы убедиться, что попали данные —
шаблон и `enpaf.js`:

```bash
python -c "import zipfile; print('\n'.join(zipfile.ZipFile('dist/enpaf-1.0.1-py3-none-any.whl').namelist()))"
```

Должны присутствовать `enpaf/template/...` и `enpaf_bridge/enpaf.js`.

---

## 4. Тестовая загрузка на TestPyPI

```bash
twine upload --repository testpypi dist/*
```

При запросе логина:
- **username:** `__token__`
- **password:** ваш TestPyPI-токен (`pypi-...`)

Проверьте установку из TestPyPI в чистом окружении (зависимости тянем с обычного
PyPI, т.к. на TestPyPI их может не быть):

```bash
python -m venv /tmp/enpaf-test
# Windows: py -m venv %TEMP%\enpaf-test  &  %TEMP%\enpaf-test\Scripts\activate
source /tmp/enpaf-test/bin/activate
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ enpaf
paf doctor
python -c "import enpaf; print(enpaf.__version__)"
```

---

## 5. Боевая загрузка на PyPI

Когда всё хорошо:

```bash
twine upload dist/*
```

- **username:** `__token__`
- **password:** ваш PyPI-токен

Готово — проект доступен на `https://pypi.org/project/enpaf/` и ставится через:

```bash
pip install enpaf
```

---

## Без интерактивного ввода (CI / автоматизация)

Передавайте токен через переменные окружения:

```bash
# PowerShell
$env:TWINE_USERNAME="__token__"
$env:TWINE_PASSWORD="pypi-AgEI..."
twine upload dist/*
```

```bash
# bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEI...
twine upload dist/*
```

Либо файл `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEI...   # боевой токен

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEI...   # тестовый токен
```

> ⚠️ Не коммитьте токены и `~/.pypirc` в репозиторий.

---

## Чеклист релиза

- [ ] Поднял `version` в `pyproject.toml`
- [ ] Обновил `README.md` (он становится описанием на PyPI)
- [ ] `rm -rf dist build *.egg-info`
- [ ] `python -m build`
- [ ] `twine check dist/*` → PASSED
- [ ] Проверил установку с TestPyPI
- [ ] `twine upload dist/*`
- [ ] Поставил git-тег: `git tag v1.0.1 && git push --tags`
