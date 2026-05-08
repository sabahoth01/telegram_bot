# Лекция — Apache Spark, Docker, HDFS, Hive

---

## Общая архитектура BigData-стека

```
Источник данных
      ↓
   HDFS (хранение)
      ↓
  Spark (обработка)
      ↓
  Hive (SQL-операции)
      ↓
Grafana / Superset (визуализация)
```

---

## HDFS (Hadoop Distributed File System)

**HDFS** — распределённая файловая система из экосистемы Hadoop.

### Ключевые особенности
- Данные хранятся **распределённо** по нескольким машинам (нодам)
- Файлы разбиваются на **блоки** (обычно 128 МБ или 256 МБ)
- Каждый блок **реплицируется** (по умолчанию — 3 копии) для отказоустойчивости
- Архитектура: **NameNode** (мастер, хранит метаданные) + **DataNode** (хранят данные)

### Когда использовать
- Данные не помещаются на одну машину
- Нужна отказоустойчивость
- Планируется обработка через Spark или MapReduce

### Типичный пайплайн
```
Сырые данные → HDFS → Spark (обработка) → Hive (SQL) → Визуализация
```

---

## Apache Spark

**Spark** — движок для распределённой обработки больших данных.

### Основные особенности
- Работает в памяти (in-memory) — быстрее Hadoop MapReduce
- Поддерживает: batch processing, streaming, ML (MLlib), SQL (Spark SQL)
- Написан на **Java/Scala**, есть API для Python (PySpark), R

### Режимы запуска

| Режим | Флаг | Описание |
|-------|------|----------|
| Локальный | `--master local[*]` | Все ядра одной машины |
| YARN кластер | `--master yarn` | Распределённый кластер |
| Standalone | `--master spark://host:7077` | Собственный кластер Spark |

```bash
# Локально
spark-submit --master local[*] script.py

# На кластере YARN
spark-submit --master yarn --deploy-mode cluster script.py
```

### Проблемы в больших командах
- Spark обычно развёрнут на кластере с **общими ресурсами**
- Лучший подход: вычитать данные в ClickHouse → обрабатывать и визуализировать там

### conda-pack для кластера
При запуске на YARN нужно упаковать зависимости для передачи на воркер-ноды:

```bash
conda pack -n myenv -o myenv.tar.gz
spark-submit --archives myenv.tar.gz#myenv ...
```

---

## Apache Hive

**Hive** — SQL-слой поверх HDFS/Spark, позволяет делать SQL-запросы к распределённым данным.

### Особенности
- Трансформирует HiveQL (SQL-подобный язык) в MapReduce / Spark jobs
- Хранит метаданные таблиц в **Metastore**
- Поддерживает партиционирование и бакетирование таблиц

### Пример запроса
```sql
SELECT user_id, COUNT(*) as events
FROM logs
WHERE dt = '2024-01-01'
GROUP BY user_id;
```

---

## Apache Zeppelin

**Zeppelin** — web-based notebook-интерфейс для работы со Spark, SQL, Python.

### Особенности
- Встроенная интеграция со Spark
- Интерактивные параграфы с разными интерпретаторами
- Визуализация результатов прямо в notebook

---

## Docker для BigData

### Зачем Docker
- Настройка Spark на реальном кластере — сложна и трудоёмка
- **Docker Compose** позволяет симулировать многоузловой кластер на одной машине
- Все компоненты (HDFS, Spark, Hive, Zeppelin) запускаются как контейнеры
- Воспроизводимость: одна и та же среда на разных машинах

### Типичный docker-compose для BigData стека

```yaml
services:
  namenode:
    image: apache/hadoop:3
    # HDFS NameNode

  datanode:
    image: apache/hadoop:3
    # HDFS DataNode

  spark-master:
    image: bitnami/spark:3
    # Spark Master

  spark-worker:
    image: bitnami/spark:3
    # Spark Worker

  hive:
    image: apache/hive:3
    # Hive

  zeppelin:
    image: apache/zeppelin:0.10.1
    ports:
      - "8080:8080"
    # Notebook интерфейс
```

### Предупреждение
> ⚠️ Развёртывание полного стека (HDFS + Spark + Hive + Zeppelin) в Docker **может занять несколько часов** при первом запуске.

---

## Визуализаторы (для BigData)

| Инструмент | Тип | Особенности |
|------------|-----|------------|
| **Grafana** | Технический | Простые графики, без багов, рекомендован для технических метрик |
| **Apache Superset** | Продуктовый | Много разных графиков, иногда капризный |
| **Datalens** | JS-based (не SQL) | Медленнее остальных |
| PowerBI | Коммерческий | Богатый функционал |
| Tableau | Коммерческий | Богатый функционал |
| Redash | Open-source | Простой, SQL-ориентированный |
| **PostHog** | Платформа | Работает на ClickHouse под капотом, красивый и с хорошей документацией, но дорогой, некастомизируемый и ограниченный по ресурсам |
