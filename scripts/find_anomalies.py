#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для поиска аномалий в текстовых файлах с произведениями русской литературы.
Ищет токены, лишние непонятные символы (не названия глав), и другие аномалии.
"""

import os
import re
import sys
from pathlib import Path

# Кириллица, цифры, основные знаки препинания, пробельные символы
RUSSIAN_CHARS = set('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя0123456789')
PUNCTUATION = set('.,;:!?-"()[]{}«»—–…')
WHITESPACE = set(' \n\r\t')
ALLOWED_CHARS = RUSSIAN_CHARS | PUNCTUATION | WHITESPACE

# Паттерны для названий глав (римские цифры, слова ГЛАВА, ЧАСТЬ и т.д.)
CHAPTER_PATTERNS = [
    r'^[IVXLCDM]+$',  # Римские цифры
    r'^ГЛАВА\s+[IVXLCDM\d]+',  # ГЛАВА I, ГЛАВА 1
    r'^ЧАСТЬ\s+[IVXLCDM\d]+',  # ЧАСТЬ I, ЧАСТЬ 1
    r'^[ГЧ]\s*[IVXLCDM\d]+',  # Г I, Ч 1
    r'^\d+$',  # Просто число (могут быть номера глав)
]

def is_likely_chapter_title(line):
    """Проверяет, является ли строка названием главы"""
    stripped = line.strip()
    if not stripped:
        return False
    
    for pattern in CHAPTER_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True
    
    # Проверка на короткие строки, состоящие только из заглавных букв
    if len(stripped) < 30 and stripped.isupper() and stripped.replace(' ', '').isalpha():
        return True
    
    return False

def is_base64_like(text):
    """Проверяет, похож ли текст на base64 строку"""
    if len(text) < 40:
        return False
    # Base64 содержит A-Z, a-z, 0-9, +, /, =
    base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    text_chars = set(text.strip())
    if text_chars.issubset(base64_chars):
        # Проверяем, что есть хотя бы один знак = или /, и достаточно много символов
        if ('=' in text or '/' in text) and len(text.strip()) > 40:
            return True
    return False

def is_normal_latin_usage(line):
    """Проверяет, является ли латиница нормальным использованием (имена собственные, римские цифры)"""
    stripped = line.strip()
    
    # Римские цифры (I, II, III, IV, V, X, L, C, D, M)
    if re.match(r'^[IVXLCDM]+$', stripped, re.IGNORECASE):
        return True
    
    # Короткие латинские слова в скобках (часто используются как пометки)
    if re.match(r'^\([a-zA-Z]{1,4}\)$', stripped):
        return True
    
    # Известные сокращения и аббревиатуры
    common_abbrevs = {'ISBN', 'ISBN:', 'http', 'https', 'www', 'com', 'ru', 'org', 'net'}
    words = re.findall(r'\b[A-Za-z]+\b', line)
    if words and all(w.upper() in common_abbrevs or len(w) <= 3 for w in words):
        return True
    
    return False

def find_anomalies_in_line(line, line_num):
    """Находит аномалии в строке"""
    anomalies = []
    
    # Пропускаем пустые строки и названия глав
    if not line.strip() or is_likely_chapter_title(line):
        return anomalies
    
    stripped = line.strip()
    
    # Проверка на base64-подобные строки (токены) - приоритетная проверка
    if is_base64_like(stripped):
        anomalies.append({
            'type': 'token_like',
            'line_num': line_num,
            'line': stripped
        })
        return anomalies  # Если это токен, другие проверки не нужны
    
    # Проверяем наличие недопустимых символов
    suspicious_chars = []
    for i, char in enumerate(line):
        if char not in ALLOWED_CHARS:
            suspicious_chars.append((i, char, ord(char)))
    
    if suspicious_chars:
        has_russian = any(c in RUSSIAN_CHARS for c in line)
        
        if has_russian:
            # Проверяем на латиницу
            latin_chars = [(i, c) for i, c, _ in suspicious_chars if c.isalpha() and ord(c) < 128]
            if latin_chars and not is_normal_latin_usage(line):
                # Только если латиницы достаточно много (не единичные символы)
                if len(latin_chars) > 3:
                    anomalies.append({
                        'type': 'latin_in_russian',
                        'line_num': line_num,
                        'chars': latin_chars[:10],  # Ограничиваем для вывода
                        'line': stripped
                    })
            
            # Другие подозрительные символы (не латиница, не кириллица)
            other_chars = [(i, c, hex(ord(c))) for i, c, code in suspicious_chars 
                          if not (c.isalpha() and ord(c) < 128)]
            # Исключаем известные нормальные символы (тире, кавычки разных видов)
            normal_symbols = set('—–…‹›‚„«»°№§')
            other_chars = [(i, c, hex_val) for i, c, hex_val in other_chars if c not in normal_symbols]
            
            if other_chars:
                anomalies.append({
                    'type': 'unusual_symbols',
                    'line_num': line_num,
                    'chars': other_chars[:10],  # Ограничиваем для вывода
                    'line': stripped
                })
    
    # Проверяем строки с множеством подряд идущих необычных символов
    # Но исключаем известные паттерны (тире, кавычки)
    unusual_pattern = re.search(r'[^\w\s\u0400-\u04FF.,;:!?\-"()\[\]{}«»—–…°№§]{3,}', line)
    if unusual_pattern:
        anomalies.append({
            'type': 'multiple_unusual_chars',
            'line_num': line_num,
            'line': stripped
        })
    
    return anomalies

def analyze_file(filepath):
    """Анализирует файл на наличие аномалий"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='cp1251') as f:
                lines = f.readlines()
        except Exception as e:
            return {'error': f'Не удалось прочитать файл: {e}'}
    except Exception as e:
        return {'error': f'Ошибка при чтении файла: {e}'}
    
    all_anomalies = []
    seen_lines = set()  # Для удаления дубликатов
    
    for line_num, line in enumerate(lines, 1):
        anomalies = find_anomalies_in_line(line, line_num)
        
        # Убираем дубликаты - если для этой строки уже есть аномалия, берем только первую
        for anomaly in anomalies:
            line_key = (line_num, anomaly['type'])
            if line_key not in seen_lines:
                seen_lines.add(line_key)
                all_anomalies.append(anomaly)
    
    return {
        'total_lines': len(lines),
        'anomalies': all_anomalies
    }

def main():
    script_dir = Path(__file__).parent
    # Файлы с текстами находятся в папке texts/ на уровень выше
    texts_dir = script_dir.parent / 'texts'
    txt_files = list(texts_dir.glob('*.txt'))
    
    if not txt_files:
        print("Не найдено .txt файлов в директории")
        return
    
    print(f"Найдено {len(txt_files)} .txt файлов\n")
    print("=" * 80)
    
    files_with_anomalies = []
    
    for txt_file in sorted(txt_files):
        result = analyze_file(txt_file)
        
        if 'error' in result:
            print(f"\n❌ {txt_file.name}")
            print(f"   Ошибка: {result['error']}")
            continue
        
        anomalies = result['anomalies']
        
        if anomalies:
            files_with_anomalies.append((txt_file.name, anomalies))
            print(f"\n🔍 {txt_file.name} ({result['total_lines']} строк)")
            
            # Группируем аномалии по типам
            by_type = {}
            for anomaly in anomalies:
                a_type = anomaly['type']
                if a_type not in by_type:
                    by_type[a_type] = []
                by_type[a_type].append(anomaly)
            
            for a_type, type_anomalies in sorted(by_type.items()):
                print(f"\n   Тип аномалии: {a_type} ({len(type_anomalies)} случаев)")
                
                # Показываем первые 3 примера каждого типа с полным текстом
                for anomaly in type_anomalies[:3]:
                    line_text = anomaly['line']
                    # Ограничиваем вывод до 500 символов, но показываем больше
                    if len(line_text) > 500:
                        print(f"      Строка {anomaly['line_num']}: {line_text[:500]}...")
                    else:
                        print(f"      Строка {anomaly['line_num']}: {line_text}")
                
                if len(type_anomalies) > 3:
                    print(f"      ... и еще {len(type_anomalies) - 3} случаев")
        
        # Показываем прогресс для файлов без аномалий
        # (раскомментируйте, если хотите видеть все файлы)
        # else:
        #     print(f"✓ {txt_file.name} - аномалий не найдено")
    
    print("\n" + "=" * 80)
    print(f"\nИтого: найдено {len(files_with_anomalies)} файлов с аномалиями из {len(txt_files)} проверенных")
    
    # Сохраняем детальный отчет в файл (в папку scripts/)
    report_file = script_dir / 'anomalies_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ОТЧЕТ ОБ АНОМАЛИЯХ В ТЕКСТОВЫХ ФАЙЛАХ\n")
        f.write("=" * 80 + "\n\n")
        
        for filename, anomalies in files_with_anomalies:
            f.write(f"\n{'='*80}\n")
            f.write(f"Файл: {filename}\n")
            f.write(f"Всего аномалий: {len(anomalies)}\n")
            f.write(f"{'='*80}\n\n")
            
            by_type = {}
            for anomaly in anomalies:
                a_type = anomaly['type']
                if a_type not in by_type:
                    by_type[a_type] = []
                by_type[a_type].append(anomaly)
            
            for a_type, type_anomalies in sorted(by_type.items()):
                f.write(f"\nТип: {a_type} ({len(type_anomalies)} случаев)\n")
                f.write("-" * 80 + "\n")
                
                for anomaly in type_anomalies:
                    f.write(f"\nСтрока {anomaly['line_num']}:\n")
                    f.write(f"{anomaly['line']}\n")
                    
                    if 'chars' in anomaly:
                        f.write(f"Подозрительные символы: {anomaly['chars']}\n")
    
    print(f"\nДетальный отчет сохранен в: {report_file}")

if __name__ == '__main__':
    main()
