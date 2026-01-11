#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создает краткий итоговый отчет об аномалиях
"""

import re
from collections import defaultdict
from pathlib import Path

def parse_anomalies_report():
    """Парсит файл отчета об аномалиях"""
    report_file = Path('anomalies_report.txt')
    
    if not report_file.exists():
        return None
    
    files_data = {}
    current_file = None
    current_type = None
    
    with open(report_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Начало нового файла
            if line.startswith('Файл:'):
                filename = line.replace('Файл:', '').strip()
                current_file = filename
                files_data[filename] = {
                    'token_like': [],
                    'unusual_symbols': [],
                    'latin_in_russian': [],
                    'multiple_unusual_chars': []
                }
            
            # Тип аномалии
            elif line.startswith('Тип:'):
                match = re.match(r'Тип: (\w+) \(\d+ случаев\)', line)
                if match:
                    current_type = match.group(1)
            
            # Номер строки
            elif line.startswith('Строка '):
                match = re.match(r'Строка (\d+):', line)
                if match and current_file and current_type:
                    line_num = int(match.group(1))
                    files_data[current_file][current_type].append(line_num)
    
    return files_data

def create_summary():
    """Создает краткий итоговый отчет"""
    data = parse_anomalies_report()
    
    if not data:
        print("Файл anomalies_report.txt не найден. Сначала запустите find_anomalies.py")
        return
    
    # Группируем файлы по типам критичных аномалий
    files_with_tokens = []
    files_with_multiple_unusual = []
    files_with_unusual_symbols = []
    files_with_latin = []
    
    for filename, anomalies in data.items():
        if anomalies['token_like']:
            files_with_tokens.append((filename, len(anomalies['token_like'])))
        if anomalies['multiple_unusual_chars']:
            files_with_multiple_unusual.append((filename, len(anomalies['multiple_unusual_chars'])))
        if len(anomalies['unusual_symbols']) > 100:  # Много необычных символов
            files_with_unusual_symbols.append((filename, len(anomalies['unusual_symbols'])))
        if len(anomalies['latin_in_russian']) > 50:  # Много латиницы
            files_with_latin.append((filename, len(anomalies['latin_in_russian'])))
    
    # Сортируем по количеству аномалий
    files_with_tokens.sort(key=lambda x: x[1], reverse=True)
    files_with_multiple_unusual.sort(key=lambda x: x[1], reverse=True)
    files_with_unusual_symbols.sort(key=lambda x: x[1], reverse=True)
    files_with_latin.sort(key=lambda x: x[1], reverse=True)
    
    # Создаем отчет
    summary = []
    summary.append("=" * 80)
    summary.append("ИТОГОВЫЙ ОТЧЕТ ОБ АНОМАЛИЯХ В ТЕКСТОВЫХ ФАЙЛАХ")
    summary.append("=" * 80)
    summary.append("")
    
    # 1. Токены (самые критичные)
    summary.append("1. КРИТИЧНЫЕ АНОМАЛИИ: ТОКЕНЫ (base64/непонятные строки)")
    summary.append("-" * 80)
    if files_with_tokens:
        summary.append(f"Найдено файлов с токенами: {len(files_with_tokens)}")
        summary.append("")
        for filename, count in files_with_tokens:
            summary.append(f"  • {filename}: {count} токенов")
    else:
        summary.append("  Токены не найдены")
    summary.append("")
    
    # 2. Множественные необычные символы
    summary.append("2. МНОЖЕСТВЕННЫЕ НЕОБЫЧНЫЕ СИМВОЛЫ")
    summary.append("-" * 80)
    if files_with_multiple_unusual:
        summary.append(f"Найдено файлов: {len(files_with_multiple_unusual)}")
        summary.append("")
        for filename, count in files_with_multiple_unusual:
            summary.append(f"  • {filename}: {count} случаев")
    else:
        summary.append("  Аномалии не найдены")
    summary.append("")
    
    # 3. Много необычных символов
    summary.append("3. ФАЙЛЫ С БОЛЬШИМ КОЛИЧЕСТВОМ НЕОБЫЧНЫХ СИМВОЛОВ (>100)")
    summary.append("-" * 80)
    if files_with_unusual_symbols:
        summary.append(f"Найдено файлов: {len(files_with_unusual_symbols)}")
        summary.append("")
        for filename, count in files_with_unusual_symbols[:20]:  # Топ 20
            summary.append(f"  • {filename}: {count} случаев")
        if len(files_with_unusual_symbols) > 20:
            summary.append(f"  ... и еще {len(files_with_unusual_symbols) - 20} файлов")
    else:
        summary.append("  Аномалии не найдены")
    summary.append("")
    
    # 4. Много латиницы
    summary.append("4. ФАЙЛЫ С БОЛЬШИМ КОЛИЧЕСТВОМ ЛАТИНИЦЫ (>50)")
    summary.append("-" * 80)
    if files_with_latin:
        summary.append(f"Найдено файлов: {len(files_with_latin)}")
        summary.append("")
        for filename, count in files_with_latin[:20]:  # Топ 20
            summary.append(f"  • {filename}: {count} случаев")
        if len(files_with_latin) > 20:
            summary.append(f"  ... и еще {len(files_with_latin) - 20} файлов")
    else:
        summary.append("  Аномалии не найдены")
    summary.append("")
    
    # Общая статистика
    summary.append("=" * 80)
    summary.append("ОБЩАЯ СТАТИСТИКА")
    summary.append("=" * 80)
    summary.append(f"Всего файлов с аномалиями: {len(data)}")
    summary.append(f"Файлов с токенами: {len(files_with_tokens)}")
    summary.append(f"Файлов с множественными необычными символами: {len(files_with_multiple_unusual)}")
    summary.append(f"Файлов с большим количеством необычных символов: {len(files_with_unusual_symbols)}")
    summary.append(f"Файлов с большим количеством латиницы: {len(files_with_latin)}")
    summary.append("")
    summary.append("ПРИМЕЧАНИЕ:")
    summary.append("- Токены - это критичные аномалии (base64-строки, непонятные данные)")
    summary.append("- Латиница в тексте может быть нормальной (имена собственные, цитаты)")
    summary.append("- Необычные символы могут включать специальные пробелы, тире и т.д.")
    summary.append("=" * 80)
    
    # Сохраняем отчет
    summary_text = "\n".join(summary)
    print(summary_text)
    
    with open('summary_report.txt', 'w', encoding='utf-8') as f:
        f.write(summary_text)
    
    print(f"\nКраткий отчет сохранен в: summary_report.txt")
    print(f"Детальный отчет: anomalies_report.txt")

if __name__ == '__main__':
    create_summary()

